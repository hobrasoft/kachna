#!/usr/bin/env python3
import requests
import configparser
from pathlib import Path
import sys
import json

CONFIG_FILE = Path.home() / ".kachna.conf"


def describe():
    print(json.dumps({
        "name": "Atmosferický tlak v Rožnově",
        "description": "Načte aktuální tlak ze senzorů v Home Assistant",
        "questions": [
            "Jaký je aktuální atmosférický tlak?",
            "Jaký je tlak přepočtený na hladinu moře?",
            "Jaký je tlak vzduchu?",
            "Jaký je tlak v Rožnově?"
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

    tlak_skutecny   = get_state("sensor.atmosfericky_tlak", ha_url, ha_token)
    tlak_prepocteny = get_state("sensor.atmosfericky_tlak_prepocteny_na_hladinu_more_2", ha_url, ha_token)

    print(json.dumps({
        "pressure": tlak_skutecny,
        "pressure_at_sea_level": tlak_prepocteny,
        "unit": "hPa",
        "source": "Home Assistant",
        "location": "Rožnov pod Radhoštěm"
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--describe":
        describe()
    else:
        execute()

