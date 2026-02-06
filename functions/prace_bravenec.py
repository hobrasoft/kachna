#!/usr/bin/env python3

from kachna import Function

f = Function()
f.setName           ("Práce Bravenec")
f.setDescription    ("Zjistí rozpracované úkoly Petra Bravence")
f.addQuestion       ("Na čem pracuje Petr Bravenec?")
f.addQuestion       ("Co dělá Petr Bravenec?")
f.addQuestion       ("Jakou práci má Petr Bravenec rozdělanou?")
f.addQuestion       ("Jaký je pracovní výkaz Petr Bravence?")
f.addQuestion       ("Co má právě rozpracováno Petr Bravenec?")

f.setDbHost         ("hrabos")
f.setDbDatabase     ("prace.hobrasoft.cz")
f.setDbUser         ("tycho")

f.setSQL("""
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
    select * from dotaz;
    """
    )

f.setFormat("table")

f.exec()

