#!/usr/bin/env python3
import requests
import configparser
from pathlib import Path
import sys
import json

CONFIG_FILE = Path.home() / ".kachna.conf"


def describe():
    print(json.dumps({
        "name": "Teplota v kanceláři a venku",
        "description": "Načte aktuální teploty ze senzorů v Home Assistant",
        "questions": [
            "Kolik je venku stupňů?",
            "Jaká je teplota v kanceláři u podlahy?",
            "Jaká je momentální aktuální venkovní teplota?",
            "Kolik je v kanceláři stupňů?",
            "Kolik je v Rožnově stupňů?",
            "Jak8 je v Rožnově aktuální venkovní momentální teplota?"
        ],
        "params": {}
    }, indent=2))


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE)

    token = cfg.get("ha", "token", fallback=None)
    url = cfg.get("ha", "url", fallback="http://homeassistant.local:8123")

    if not token:
        raise ValueError("Missing [ha] token in config")

    # odstraní případné uvozovky
    token = token.strip().strip("'").strip('"')

    return url, token


def get_state(entity_id: str, url: str, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    r = requests.get(
        f"{url}/api/states/{entity_id}",
        headers=headers,
        timeout=5
    )
    r.raise_for_status()

    data = r.json()
    return float(data["state"])


def execute():
    ha_url, ha_token = load_config()

    venku = get_state("sensor.venkovni_teplota", ha_url, ha_token)
    kancelar = get_state("sensor.kancelar_u_podlahy", ha_url, ha_token)

    print(json.dumps({
        "venkovni_teplota": venku,
        "kancelar_u_podlahy": kancelar,
        "unit": "°C",
        "source": "Home Assistant",
        "prompt": "Uváděj přednostně tlak přepočtený na hladinu moře"
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--describe":
        describe()
    else:
        execute()

