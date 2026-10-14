# Plant Health Monitor (ESP8266 + MicroPython)

## Short description

An ESP8266 reads air temperature and humidity (DHT11), light level (LDR) and soil moisture (HW-080 probe), shows them on a 1.3" OLED, and gives a simple status: **OK**, **Needs water** or **Check conditions**. The ESP8266 has only one analog pin, so the LDR and soil probe take turns on A0. Each is powered from its own GPIO only while it is being read, which also reduces probe corrosion.

## Pinout and input types

| Part | Input type | Board pin | Code pin |
|---|---|---|---|
| DHT11 DATA | **Digital** (single-wire protocol) | D5 | `Pin(14)` |
| OLED SCL | **Digital** (I2C) | D1 | `Pin(5)` |
| OLED SDA | **Digital** (I2C) | D2 | `Pin(4)` |
| LDR | **Analog** (voltage divider) | D6 powers it, A0 reads it | `Pin(12)`, `ADC(0)` |
| Soil probe | **Analog** (voltage divider) | D7 powers it, A0 reads it | `Pin(13)`, `ADC(0)` |

**Power:** DHT11 VCC and OLED VCC go to **3V3**, and all grounds go to **GND**.

**Analog part of the wiring** (the A0 node is one shared point):

```
D6 ──[ LDR ]───┐
               ├── A0 ──[ 10 kΩ ]── GND
D7 ──[ probe ]─┘
```

## Files on the board

1. `sh1106.py`: the OLED driver from earlier (don't rename it)
2. `main.py`: the code below, which runs automatically on boot

## main.py

```python
from machine import Pin, I2C, ADC
import dht
import time

# ---------- Calibration (adjust after testing) ----------
LIGHT_DARK = 0       # A0 reading with the LDR covered
LIGHT_BRIGHT = 1023  # A0 reading in bright light
SOIL_DRY = 0         # A0 reading with the probe in dry air
SOIL_WET = 600       # A0 reading with the probe in water

SOIL_LOW = 30        # below this % = needs water
LIGHT_LOW = 15       # below this % = too dark
TEMP_MIN, TEMP_MAX = 15, 32   # comfortable range in C
INTERVAL = 5         # seconds between updates

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
    print("T:{}C H:{}% Light:{}% Soil:{}% -> {}".format(t, h, light, soil, status))
    if oled is None:
        return
    oled.fill(0)
    oled.text("Plant Monitor", 0, 0)
    oled.text("T:{}C H:{}%".format(t, h), 0, 16)
    oled.text("Light: {}%".format(light), 0, 28)
    oled.text("Soil:  {}%".format(soil), 0, 40)
    oled.text(status, 0, 54)
    oled.show()

# ---------- Main loop ----------
time.sleep(2)   # let the DHT11 settle
while True:
    temp, hum = read_dht()
    light = to_percent(read_analog(LIGHT_PWR), LIGHT_DARK, LIGHT_BRIGHT)
    soil = to_percent(read_analog(SOIL_PWR), SOIL_DRY, SOIL_WET)
    show(temp, hum, light, soil, get_status(temp, soil, light))
    time.sleep(INTERVAL)
```

## What each reading means

* **Temperature and humidity:** whole numbers from the DHT11 (about ±2 °C, ±5%).
* **Light %:** relative brightness. 0 is dark and 100 is bright, based on your calibration.
* **Soil %:** 0 is dry and 100 is as wet as water, based on your calibration. This probe wiring gives **higher values when wetter**.

## Before you rely on it

1. **Get the 10 kΩ resistor.** Without it the soil reading isn't usable (on NodeMCU/Wemos boards it only gives a rough wet/dry hint).
2. **Calibrate:** run the program and note the raw A0 values in the dark and bright light, and with the probe in air and in water. Then set `LIGHT_DARK`, `LIGHT_BRIGHT`, `SOIL_DRY` and `SOIL_WET` to match. To see the raw values, add `print(read_analog(SOIL_PWR))` above the loop.
3. **Your DHT11 was still timing out** on the ESP8266. If it still fails, the screen shows `--` for temperature and humidity and everything else keeps working. Then check the wiring, try 5 V with a 1 kΩ resistor on DATA, or replace the sensor.
4. **Tune the thresholds** (`SOIL_LOW`, `LIGHT_LOW`, `TEMP_MIN` and `TEMP_MAX`) for the plant you have. Different plants want different values.

## Possible next steps

Send the readings to a server over Wi-Fi (`urequests.post`), build the web dashboard with history graphs, and add the pump later using the transistor circuit on D8 (GPIO15).
