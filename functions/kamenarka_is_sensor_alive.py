#!/usr/bin/env python3

from kachna import Function

f = Function()

f.setName           ("Stav sensoru Kamenárka")
f.setDescription    ("Zjistí, zda je senzor na Kamenárce aktuálně online podle posledního měření")
f.addQuestion       ("Funguje senzor na Kamenárce?")
f.addQuestion       ("Je Kamenárka online?")
f.addQuestion       ("Je senzor na Kamenárce naživu?")
f.addQuestion       ("Je uzel na Kamenárce živý?")
f.addQuestion       ("Kdy se senzor na Kamenárce naposledy ozval?")

f.setDbHost         ("hrabos")
f.setDbDatabase     ("kamenarka.eu")
f.setDbUser         ("kamenarka.eu")
f.setDbPassword     ("kamenarka.eu")

f.setSQL("""
        SELECT
         -- 1.0 / (1.0 + ln(1 + to_hours(now() - t.date) / 3.0)) as confidence,
            1.0 / (1.0 + exp(-1.5 *  abs(to_hours(now() - t.date) - 1.5))) as confidence,
            t.date as timestamp, 
            now() - date as age,
            now() - date < interval '1 hour' as alive
        FROM telemetry_view t
        WHERE t.station = 'www.kamenarka.cz'
        ORDER BY t.date DESC
        LIMIT 1
    """
    )

f.setFormat("sentence")
f.setAdvice("Stručně odpověz, jestli je uzel živý (hodnota v položce alive) a před jakou dobou se ozval naposledy (položka age)")

f.exec()

