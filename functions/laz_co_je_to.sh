#!/bin/bash
set -euo pipefail

describe() {
  cat <<'JSON'
{
  "name": "Co je Láz",
  "description": "Základní popis lokality Láz a jejího účelu",
  "questions": [
    "Co je Láz?",
    "Co je na Lázu?",
    "Co znamená Láz?",
    "K čemu slouží Láz?",
    "Jaký je Láz?"
  ],
  "params": {}
}
JSON
}

execute() {
  cat <<'JSON'
{
  "name": "Láz",
  "type": "lokalita",
  "description": "Láz je kopec 549m s instalovaným meshtastic environmentálním senzorem používaným pro experimentální měření a monitoring.",
  "purpose": [
    "sběr environmentálních dat",
    "testování meshtastic sítě",
    "monitoring provozu senzorů"
  ],
  "technology": [
    "meshtastic",
    "senzory teploty a tlaku",
    "fotovoltaické panely",
    "akumulátor",
    "GPS"
  ]
}
JSON
}

case "${1:-}" in
  --describe)
    describe
    ;;
  *)
    execute
    ;;
esac

