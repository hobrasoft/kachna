#!/usr/bin/env python3

import requests
from kachna import Function
from datetime import datetime, timezone
import math

def provider():
    token = f.config.get("ha", "token")
    url   = f.config.get("ha", "url")
    item  = "sensor.kancelar_u_podlahy"

    r = requests.get(
        f"{url}/api/states/{item}",
        headers = { "Authorization": f"Bearer {token}", "Content-Type": "application/json" },
        timeout = 5
        )
    r.raise_for_status()

    data = r.json()

    ts = datetime.fromisoformat(data["last_updated"])
    now = datetime.now(timezone.utc)
    age_hours = (now - ts).total_seconds() / 3600.0
    confidence = 1.0 / (1.0 + math.log(1.0 + age_hours / 3.0))

    return {
        "temperature": float(data["state"]),
        "timestamp": data["last_updated"],
        "confidence": confidence
        }


f = Function()
f.setName           ("Teplota v Kanceláři")
f.setDescription    ("Zjistí aktuální teplotu v kanceláři ze sensorů v Home Assistant")
f.addQuestion       ("Kolik je v kanceláři stupňů?")
f.addQuestion       ("Jaká je momentální aktuální teplota v kanceláři?")
f.addQuestion       ("Kolik je v kanceláři stupňů?")
f.setAdvice         ("Stručně odpověz, kolik je stupňů a kdy byla hodnota naměřena.")
f.setFormat         ("sentence")
f.setProvider       (provider)
f.exec()




