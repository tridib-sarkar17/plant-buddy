import random
import time
import requests

URL = "http://127.0.0.1:5000/api/readings"
soil = 500

for i in range(30):
    soil += random.randint(3, 12)
    if i == 20:
        soil -= 150  # pretend someone watered the plant

    reading = {
        "plant_id": "sim_plant",
        "temperature": round(random.uniform(26, 31), 1),
        "humidity": round(random.uniform(55, 75), 1),
        "soil_raw": soil,
        "light_raw": random.randint(300, 800),
    }
    r = requests.post(URL, json=reading)
    print(i, r.status_code)
    time.sleep(1)
