#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="kamenarka.eu"
DB_USER="kamenarka.eu"

describe() {
  cat <<'JSON'
{
  "name": "Teplota Láz",
  "description": "Zjistí poslední známou teplotu a tlak na Lázu",
  "questions": [
    "Jaká je poslední teplota na Lázu?",
    "Je v tento moment na Lázu zima?",
    "Je v tento moment na Lázu horko?",
    "Jaký je v tento moment tlak na Lázu?",
    "Jaký je nyní tlak na Lázu?"
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
  and t.station = 'hobrasoft.cz sensor 2'
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
  "location": "Láz"
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

