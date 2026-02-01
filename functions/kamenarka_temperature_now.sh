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
    "Jaký je v tento moment tlak na Kamenárce?"
    "Jaký je nyní tlak na Kamenárce?"
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
    t.temperature,
    t.pressure
from telemetry_view t
where t.temperature is not null
  and t.station = 'www.kamenarka.cz'
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

