#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="prace.hobrasoft.cz"
DB_USER="tycho"

describe() {
  cat <<'JSON'
{
  "name": "Práce Bravenec",
  "description": "Zjistí rozpracované úkoly Petra Bravence",
  "questions": [
    "Na čem pracuje Petr Bravenec?",
    "Co dělá Petr Bravenec?",
    "Jakou práci má Petr Bravenec rozdělanou?",
    "Jaký je pracovní výkaz Petr Bravence?",
    "Co má právě rozpracováno Petr Bravenec?"
  ],
  "params": {}
}
JSON
}

execute() {
  result="$(
    psql -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" -At <<'SQL'
        with params as (
            select
                2 as "user", 
                true as valid
        ),
        subdotaz as (
            select c.description as category_description, tsw.date, tsw.description, tsw.status_description, tt.ticket_time, round(to_hours(ticket_time) * tsw.price) as price
                from ticket_status_vw  tsw
                cross join params p
                left join statuses sts using (status)
                left join (select ticket, sum(coalesce(date_to, now()) - date_from) as ticket_time
                    from ticket_timesheets
                    group by ticket
                    ) tt using (ticket)
                left join categories c on (c.category = tsw.category)
                where sts.can_be_run
                  and tsw."user" = p."user"
        ),
        dotaz as (
            select * from subdotaz
            union all
            select null, null, null, null, sum(ticket_time), sum(price)
            from subdotaz
        )

        select coalesce(
            json_agg(
                json_build_object(
                        'Kategorie',    category_description,
                        'Datum',        to_char(date, 'FMDD.FMMM.YYYY'),
                        'Popis',        description,
                        'Status',       status_description,
                        'Čas',          to_char(ticket_time, 'HH24:MI'),
                        'Cena',         price
                        ) 
                    ), '[]'::json)
            from dotaz
        ;
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

