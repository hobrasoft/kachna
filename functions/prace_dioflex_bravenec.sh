#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="prace.hobrasoft.cz"
DB_USER="tycho"

describe() {
  cat <<'JSON'
{
  "name": "Práce Dioflex Bravenec",
  "description": "Zjistí rozpracované úkoly Petr Bravence pro Dioflex",
  "questions": [
    "Co dělá Petr Bravenec pro Dioflex?",
    "Jakou práci má petr Bravenec rozdělanou pro Dioflex?"
  ],
  "params": {}
}
JSON
}

execute() {
  result="$(
    psql -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" -At <<'SQL'
select coalesce(
    json_agg(
        json_build_object(
            'date', ts.date,
            'description', ts.description,
            'status', status_description,
            'worked_time', ticket_time,
            'price_czk', round(to_hours(ticket_time) * ts.price)
                ) order by ts.date
            ), '[]'::json
        )
    from ticket_status_vw ts
    left join (select ticket, sum(coalesce(date_to, now()) - date_from) as ticket_time
        from ticket_timesheets
        group by ticket
        ) tt using (ticket)
    where category = 44
    and status = 'NEW';
SQL
  )"

  if [[ -z "$result" ]]; then
    echo '{"error":"no_data"}'
    exit 0
  fi

  IFS=$'\t' read -r date temperature pressure <<<"$result"

  cat <<JSON
{
  "data": $result,
  "format": "table"
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

