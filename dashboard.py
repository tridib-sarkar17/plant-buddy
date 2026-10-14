import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="GreenPulse", page_icon="🌱", layout="wide")

CSV_FILE = "readings.csv"

# ---- PER-PLANT PROFILES (placeholders, calibrate each one) ----
PLANTS = {
    "tulsi": {
        "label": "Tulsi",
        "soil_dry_raw": 0, "soil_wet_raw": 600, "soil_low_pct": 30,
        "temp_range": (18, 32), "hum_range": (40, 80),
    },
    "dupati": {
        "label": "Dupati",
        "soil_dry_raw": 0, "soil_wet_raw": 600, "soil_low_pct": 30,
        "temp_range": (18, 32), "hum_range": (40, 80),
    },
}
DEFAULT_PROFILE = {   # used for sim_plant or any unknown ID
    "label": "Unknown",
    "soil_dry_raw": 0, "soil_wet_raw": 600, "soil_low_pct": 30,
    "temp_range": (18, 32), "hum_range": (40, 80),
}

st.title("🌱 GreenPulse")
st.caption("IoT Plant Monitoring & Watering Assistance")

COLUMNS = ["timestamp", "plant_id", "temperature",
           "humidity", "soil_raw", "light_raw"]

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    df = pd.DataFrame(columns=COLUMNS)

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"])
df["plant_id"] = df["plant_id"].astype(str)

# ---- Sidebar: always list Tulsi and Dupati, plus any other IDs in the data ----
plants = list(PLANTS.keys()) + sorted(
    pid for pid in df["plant_id"].unique() if pid not in PLANTS
)
plant = st.sidebar.selectbox(
    "Select plant", plants,
    format_func=lambda pid: PLANTS[pid]["label"] if pid in PLANTS else pid,
)
st.sidebar.button("🔄 Refresh readings")

if plant.startswith("sim"):
    st.warning("Showing SIMULATED data, not live hardware readings.")

p = df[df["plant_id"] == plant].sort_values("timestamp").copy()

cfg = PLANTS.get(plant, DEFAULT_PROFILE)
st.header(f"Plant: {cfg['label'] if plant in PLANTS else plant}")
if p.empty:
    st.info(f"No readings received yet for {cfg['label'] if plant in PLANTS else plant}. "
            "Connect that plant's probe and wait for the first reading.")
    st.stop()


def soil_percent(raw):
    dry, wet = cfg["soil_dry_raw"], cfg["soil_wet_raw"]
    pct = (raw - dry) / (wet - dry) * 100
    return max(0, min(100, pct))


p["soil_pct"] = p["soil_raw"].apply(soil_percent)
latest = p.iloc[-1]

# ---- Rule-based condition estimate ----
issues = []
if latest["soil_pct"] < cfg["soil_low_pct"]:
    issues.append("Soil is dry, watering may be needed")
t_lo, t_hi = cfg["temp_range"]
h_lo, h_hi = cfg["hum_range"]
if not t_lo <= latest["temperature"] <= t_hi:
    issues.append("Temperature outside demo range")
if not h_lo <= latest["humidity"] <= h_hi:
    issues.append("Humidity outside demo range")

if not issues:
    st.success("😊 Estimated condition: Favorable")
elif len(issues) == 1:
    st.warning("😐 Estimated condition: Moderate. " + issues[0])
else:
    st.error("😟 Estimated condition: Needs attention. " + "; ".join(issues))

# ---- Current readings ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Temperature", f"{latest['temperature']:.1f} °C")
c2.metric("Humidity", f"{latest['humidity']:.0f} %")
c3.metric("Soil moisture (est.)", f"{latest['soil_pct']:.0f} %")
c4.metric("Light (raw)", f"{int(latest['light_raw'])}")
st.caption(f"Last reading: {latest['timestamp']}  |  Total readings: {len(p)}")

# ---- History graphs ----
st.subheader("Soil moisture history")
st.plotly_chart(px.line(p, x="timestamp", y="soil_pct",
                        labels={"soil_pct": "Soil moisture (%)"}),
                use_container_width=True)

g1, g2 = st.columns(2)
g1.plotly_chart(px.line(p, x="timestamp", y="temperature",
                        title="Temperature (°C)"), use_container_width=True)
g2.plotly_chart(px.line(p, x="timestamp", y="humidity",
                        title="Humidity (%)"), use_container_width=True)
