#!/usr/bin/env python3

import requests
from kachna import Function
from datetime import datetime, timezone
import math

def provider():
    token = f.config.get("ha", "token")
    url   = f.config.get("ha", "url")
    item  = "sensor.atmosfericky_tlak"

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
        "confidence": confidence,
        "units": "hPa"
        }


f = Function()
f.setName           ("Atmosférický tlak v Rožnově")
f.setDescription    ("Zjistí aktuální tlak ze sensorů v Home Assistant")
f.addQuestion       ("Kolik je venku stupňů?")
f.addQuestion       ("Jaký je momentální aktuální atmosférický tlak?")
f.addQuestion       ("Jaký je tlak přepočtený na hladinu moře?")
f.addQuestion       ("Jaký je tlak vzduchu?")
f.addQuestion       ("Jaký je tlak v Rožnově?")
f.setAdvice         ("Stručně odpověz, jaký je tlak v hPa!")
f.setFormat         ("sentence")
f.setProvider       (provider)
f.exec()

