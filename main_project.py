from machine import Pin, I2C, ADC
import dht
import time
import network
import ujson

try:
    import urequests
except ImportError:
    import requests as urequests

# ---------- Which plant is connected RIGHT NOW ----------
PLANT_ID = "tulsi"      # change to "dupati" when you move the probe

PLANT_PROFILES = {
    # soil_dry / soil_wet: A0 reading in dry air vs. in water (calibrate per plant)
    "tulsi":  {"soil_dry": 0, "soil_wet": 600, "soil_low": 30},
    "dupati": {"soil_dry": 0, "soil_wet": 600, "soil_low": 30},
}

_profile = PLANT_PROFILES[PLANT_ID]
SOIL_DRY = _profile["soil_dry"]
SOIL_WET = _profile["soil_wet"]
SOIL_LOW = _profile["soil_low"]

# ---------- Calibration (adjust after testing) ----------
LIGHT_DARK = 0       # A0 reading with the LDR covered
LIGHT_BRIGHT = 1023  # A0 reading in bright light

LIGHT_LOW = 15       # below this % = too dark
TEMP_MIN, TEMP_MAX = 15, 32   # comfortable range in C
INTERVAL = 5         # seconds between updates

# ---------- Network ----------
WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_URL = "http://10.188.110.109:5000/api/readings"  # teammate's laptop IPv4

# ---------- Pins ----------
LIGHT_PWR = 12       # D6
SOIL_PWR = 13        # D7
adc = ADC(0)
dht_sensor = dht.DHT11(Pin(14))   # D5

# ---------- OLED (optional: runs without it) ----------
try:
    import sh1106
    i2c = I2C(scl=Pin(5), sda=Pin(4))
    oled = sh1106.SH1106_I2C(128, 64, i2c)
except Exception as e:
    print("OLED not found:", e)
    oled = None

# ---------- Sensor reading ----------


def read_analog(pin_num, samples=10):
    # switch both sensors off (floating), then power only one
    Pin(LIGHT_PWR, Pin.IN)
    Pin(SOIL_PWR, Pin.IN)
    time.sleep_ms(50)
    p = Pin(pin_num, Pin.OUT)
    p.value(1)
    time.sleep_ms(200)
    total = 0
    for _ in range(samples):
        total += adc.read()
        time.sleep_ms(10)
    Pin(pin_num, Pin.IN)
    return total // samples


def to_percent(raw, low, high):
    if high == low:
        return 0
    pct = (raw - low) * 100 // (high - low)
    return max(0, min(100, pct))


def read_dht():
    for _ in range(3):
        try:
            dht_sensor.measure()
            return dht_sensor.temperature(), dht_sensor.humidity()
        except OSError:
            time.sleep(1)
    return None, None

# ---------- Status ----------


def get_status(temp, soil, light):
    if soil < SOIL_LOW:
        return "Needs water"
    if light < LIGHT_LOW:
        return "Too dark"
    if temp is not None and not (TEMP_MIN <= temp <= TEMP_MAX):
        return "Check temp"
    return "OK"

# ---------- Display ----------


def show(temp, hum, light, soil, status):
    t = "--" if temp is None else str(temp)
    h = "--" if hum is None else str(hum)
    print("[{}] T:{}C H:{}% Light:{}% Soil:{}% -> {}".format(
        PLANT_ID, t, h, light, soil, status))
    if oled is None:
        return
    oled.fill(0)
    oled.text(PLANT_ID, 0, 0)
    oled.text("T:{}C H:{}%".format(t, h), 0, 16)
    oled.text("Light: {}%".format(light), 0, 28)
    oled.text("Soil:  {}%".format(soil), 0, 40)
    oled.text(status, 0, 54)
    oled.show()

# ---------- Wi-Fi + sending ----------


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(15):
        if wlan.isconnected():
            print("Wi-Fi connected, ESP IP:", wlan.ifconfig()[0])
            return True
        time.sleep(1)
    print("Wi-Fi failed; sensors continue.")
    return False


def send_reading(temp, hum, soil_raw, light_raw):
    if temp is None or hum is None:
        print("Skip send: DHT read failed")
        return
    if not connect_wifi():
        return
    try:
        payload = ujson.dumps({
            "plant_id": PLANT_ID,
            "temperature": temp,
            "humidity": hum,
            "soil_raw": soil_raw,
            "light_raw": light_raw,
        })
        r = urequests.post(SERVER_URL, data=payload,
                           headers={"Content-Type": "application/json"})
        print("Sent, server replied:", r.status_code)
        r.close()
    except Exception as e:
        print("Send failed:", e)


# ---------- Main loop ----------
time.sleep(2)   # let the DHT11 settle
connect_wifi()
while True:
    temp, hum = read_dht()
    light_raw = read_analog(LIGHT_PWR)
    soil_raw = read_analog(SOIL_PWR)
    light = to_percent(light_raw, LIGHT_DARK, LIGHT_BRIGHT)
    soil = to_percent(soil_raw, SOIL_DRY, SOIL_WET)
    show(temp, hum, light, soil, get_status(temp, soil, light))
    send_reading(temp, hum, soil_raw, light_raw)
    time.sleep(INTERVAL)
