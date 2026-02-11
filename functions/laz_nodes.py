#!/usr/bin/env python3

from kachna import Function


f = Function()

f.setName("Co je Láz")
f.setDescription("Základní popis lokality Láz a jejího účelu")
f.addQuestion("Co je Láz?")
f.addQuestion("Co je na Lázu?")
f.addQuestion("Co znamená Láz?")
f.addQuestion("K čemu slouží Láz?")
f.addQuestion("Jaký je Láz?")
f.setAdvice  ("Stručně popiš, co je na Lázu")
f.setFormat  ("sentence")


def provider():
    return {
        "description": (
            "Láz je kopec 549m s instalovaným meshtastic environmentálním senzorem používaným pro experimentální měření a monitoring."
        ),
        "purpose": [
            "sběr environmentálních dat",
            "testování meshtastic sítě",
            "monitoring provozu senzorů",
        ],
        "technology": [
            "meshtastic",
            "senzory teploty a tlaku",
            "fotovoltaické panely",
            "akumulátor",
            "GPS",
        ],
    }


f.setProvider(provider)
f.exec()

