from kachna import Function

f = Function()
f.setName           ("Práce Hofman")
f.setDescription    ("Zjistí rozpracované úkoly Tomáše Hofmana")
f.addQuestion       ("Na čem pracuje Tomáš Hofman?")
f.addQuestion       ("Co dělá Tomáš Hofman?")
f.addQuestion       ("Jakou práci má Tomáš Hofman rozdělanou?")
f.addQuestion       ("Jaký je pracovní výkaz Tomáše Hofmana?")
f.addQuestion       ("Co má právě rozpracováno Tomáš Hofman?")

f.setDbHost         ("hrabos")
f.setDbDatabase     ("prace.hobrasoft.cz")
f.setDbUser         ("tycho")

f.setSQL("""
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
    select * from dotaz;
    """
    )

f.setFormat("sentence")
#f.setPrompt(
#    "Zformátuj odpověď jako jednu větu v češtině. "
#    "Použij jednotky °C a hPa. "
#    "Nepřidávej komentáře ani domněnky."
#)
f.setAdvice("Stručně odpověz, kolik je stupňů a jaký je tlak.")
f.setConfidence(1.0)

f.exec()

