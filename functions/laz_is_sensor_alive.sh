#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="kamenarka.eu"
DB_USER="kamenarka.eu"
STATION="www.kamenarka.cz"

describe() {
  cat <<'JSON'
{
  "name": "Stav senzoru Kamenárka",
  "description": "Zjistí, zda je senzor na Kamenárce aktuálně online podle posledního měření",
  "questions": [
    "Funguje senzor na Kamenárce?",
    "Je Kamenárka online?",
    "Je senzor na Kamenárce naživu?",
    "Kdy se senzor na Kamenárce naposledy ozval?"
  ],
  "params": {}
}
JSON
}

execute() {
  result="$(
    psql -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" -At -F $'\t' <<SQL
select
    date,
    now() - date as age,
    now() - date < interval '1 hour' as alive
from telemetry_view
where station = '$STATION'
order by date desc
limit 1;
SQL
  )"

  if [[ -z "$result" ]]; then
    echo '{"error":"no_data"}'
    exit 0
  fi

  IFS=$'\t' read -r date age alive <<<"$result"

  cat <<JSON
{
  "alive": $alive,
  "last_seen": "$date",
  "age": "$age",
  "station": "Kamenárka"
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

