#!/bin/bash
set -euo pipefail

describe() {
  cat <<'JSON'
{
  "name": "Uzly na Kamenárce",
  "description": "Popis uzlů meshtastic umístěných na lokalitě Kamenárka",
  "questions": [
    "Co je na Kamenárce?",
    "Jaké uzly jsou na Kamenárce?",
    "Kolik senzorů je na Kamenárce?",
    "Jaké meshtastic uzly jsou na Kamenárce?"
  ],
  "params": {}
}
JSON
}

execute() {
  cat <<'JSON'
{
  "location": "Kamenárka",
  "nodes": [
    {
      "name": "www.kamenarka.eu",
      "type": "meshtastic",
      "description": "Hlavní uzel na Kamenárce"
    },
    {
      "name": "hobrasoft.cz sensor",
      "type": "meshtastic",
      "description": "Doplňkový senzorový uzel"
    }
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

