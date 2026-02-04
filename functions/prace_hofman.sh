#!/bin/bash
set -euo pipefail

DB_HOST="hrabos"
DB_NAME="prace.hobrasoft.cz"
DB_USER="tycho"

describe() {
  cat <<'JSON'
{
  "name": "Práce Hofman",
  "description": "Zjistí rozpracované úkoly Tomáše Hofmana",
  "questions": [
    "Na čem pracuje Tomáš Hofman?",
    "Co dělá Tomáš Hofman?",
    "Jakou práci má Tomáš Hofman rozdělanou?",
    "Jaký je pracovní výkaz Tomáše Hofmana?",
    "Co má právě rozpracováno Tomáš Hofman?"
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
                3 as "user", 
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

