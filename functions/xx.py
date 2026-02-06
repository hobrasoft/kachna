from kachna import Function

f = Function()

f.setName           ("Teplota kamenárka")
f.setDescription    ("Teplota kamenárka")
f.addQuestion       ("Jaká je poslední teplota na Kamenárce?")
f.addQuestion       ("Je v tento moment na Kamenárce zima?")
f.addQuestion       ("Je v tento moment na Kamenárce horko?")
f.addQuestion       ("Jaký je v tento moment tlak na Kamenárce?")
f.addQuestion       ("Jaký je nyní tlak na Kamenárce?")
f.addQuestion       ("Kolik je stupňů na Kamenárce?")
f.addQuestion       ("Kolik je nyní stupňů na Kamenárce?")
f.addQuestion       ("Kolik je teď stupňů na Kamenárce?")

f.setDbHost         ("hrabos")
f.setDbDatabase     ("kamenarka.eu")
f.setDbUser         ("kamenarka.eu")
f.setDbPassword     ("kamenarka.eu")

f.setSQL("""
        SELECT
            t.date AS timestamp,
            round(t.temperature*10)/10 AS temperature_c,
            round(t.pressure*10)/10    AS pressure_hpa
        FROM telemetry_view t
        WHERE t.temperature IS NOT NULL
          AND t.station = 'hobrasoft.cz sensor'
        ORDER BY t.date DESC
        LIMIT 1
    """
    )

f.setFormat("sentence")
f.setPrompt(
    "Zformátuj odpověď jako jednu větu v češtině. "
    "Použij jednotky °C a hPa. "
    "Nepřidávej komentáře ani domněnky."
)
f.setAdvice("Stručně odpověz, kolik je stupňů a jaký je tlak.")
f.setConfidence(1.0)

f.exec()

