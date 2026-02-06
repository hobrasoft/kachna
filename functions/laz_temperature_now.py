#!/usr/bin/env python3

from kachna import Function

f = Function()

f.setName           ("Teplota Láz")
f.setDescription    ("Teplota Láz")
f.addQuestion       ("Jaká je poslední teplota na Láze?")
f.addQuestion       ("Je v tento moment na Lázei zima?")
f.addQuestion       ("Je v tento moment na Lázeh orko?")
f.addQuestion       ("Jaký je v tento moment tlak na Lázu?")
f.addQuestion       ("Jaký je nyní tlak na Lázu?")
f.addQuestion       ("Kolik je stupňů na Lázu?")
f.addQuestion       ("Kolik je nyní stupňů na Lázu?")
f.addQuestion       ("Kolik je teď stupňů na Láze?")

f.setDbHost         ("hrabos")
f.setDbDatabase     ("kamenarka.eu")
f.setDbUser         ("kamenarka.eu")
f.setDbPassword     ("kamenarka.eu")

f.setSQL("""
        SELECT
            1.0 / (1.0 + ln(1 + to_hours(now() - t.date) / 3.0)) as confidence,
            t.date AS timestamp,
            round(t.temperature*10)/10 AS temperature_c,
            round(t.pressure*10)/10    AS pressure_hpa
        FROM telemetry_view t
        WHERE t.temperature IS NOT NULL
          AND t.station = 'hobrasoft.cz sensor 2'
        ORDER BY t.date DESC
        LIMIT 1
    """
    )

f.setFormat("sentence")
f.setAdvice("Stručně odpověz, kolik je stupňů a kdy byla hodnota naměřena.")

f.exec()

