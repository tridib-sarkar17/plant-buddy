from flask import Flask, request, jsonify
from datetime import datetime
import csv
import os

app = Flask(__name__)

DATA_FILE = "readings.csv"
FIELDS = ["timestamp", "plant_id", "temperature",
          "humidity", "soil_raw", "light_raw"]


def initialise_csv():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


@app.get("/")
def home():
    return "GreenPulse sensor server is running!"


@app.post("/api/readings")
def receive_reading():
    data = request.get_json(silent=True) or {}
    required = ["plant_id", "temperature", "humidity",
                "soil_raw", "light_raw"]

    if any(key not in data for key in required):
        return jsonify({"error": "Missing sensor fields"}), 400

    try:
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "plant_id": str(data["plant_id"]),
            "temperature": float(data["temperature"]),
            "humidity": float(data["humidity"]),
            "soil_raw": int(data["soil_raw"]),
            "light_raw": int(data["light_raw"]),
        }
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid sensor values"}), 400

    with open(DATA_FILE, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow(row)

    print("Reading saved:", row)
    return jsonify({"success": True, "message": "Reading saved"}), 201


if __name__ == "__main__":
    initialise_csv()
    print("GreenPulse backend starting...")
    app.run(host="0.0.0.0", port=5000, debug=False)
