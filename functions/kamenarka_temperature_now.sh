#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="kamenarka.eu"
DB_USER="kamenarka.eu"

describe() {
  cat <<'JSON'
{
  "name": "Teplota Kamenárka",
  "description": "Zjistí poslední známou teplotu a tlak na Kamenárce",
  "questions": [
    "Jaká je poslední teplota na Kamenárce?",
    "Je v tento moment na Kamenárce zima?",
    "Je v tento moment na Kamenárce horko?",
    "Jaký je v tento moment tlak na Kamenárce?",
    "Jaký je nyní tlak na Kamenárce?",
    "Kolik je stupňů na Kamenárce?",
    "Kolik je nyní stupňů na Kamenárce?",
    "Kolik je teď stupňů na Kamenárce?"
  ],
  "params": {}
}
JSON
}

execute() {
  result="$(
    psql -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" -At -F $'\t' <<'SQL'
select
    t.date,
    round(t.temperature*10)/10 as temperature,
    round(t.pressure*10)/10 as pressure
from telemetry_view t
where t.temperature is not null
  and t.station = 'hobrasoft.cz sensor'
order by t.date desc
limit 1;
SQL
  )"

  if [[ -z "$result" ]]; then
    echo '{"error":"no_data"}'
    exit 0
  fi

  IFS=$'\t' read -r date temperature pressure <<<"$result"

  cat <<JSON
{
  "temperature": $temperature,
  "pressure": $pressure,
  "unit": {
    "temperature": "°C",
    "pressure": "hPa"
  },
  "timestamp": "$date",
  "location": "Kamenárka"
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

