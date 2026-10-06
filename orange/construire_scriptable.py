#!/usr/bin/env python3
"""Génère scriptable/Telecommande Orange.js (version iPhone) à partir de index.html."""
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ICI, "index.html"), encoding="utf-8") as f:
    html = f.read()
with open(os.path.join(ICI, "scriptable", "modele.js"), encoding="utf-8") as f:
    modele = f.read()

sortie = os.path.join(ICI, "scriptable", "Telecommande Orange.js")
with open(sortie, "w", encoding="utf-8") as f:
    f.write(modele.replace("__HTML__", json.dumps(html, ensure_ascii=False), 1))
print("écrit :", os.path.relpath(sortie, ICI))
