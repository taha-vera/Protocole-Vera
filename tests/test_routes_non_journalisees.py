#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_routes_non_journalisees.py -- aucune requete du parcours de vote ne doit
laisser d'IP dans les journaux.

POURQUOI CE TEST EXISTE
La meme fuite a ete ouverte deux fois.

Le 06/08 : quatre routes avaient `access_log off`, mais le chargement de la
page de vote en declenchait deux autres -- /api/question et le bundle -- qui
tombaient dans `location /` et etaient journalisees avec IP et horodatage a la
seconde. Croise avec une source associant IP et personne, cela reconstitue qui
a vote et quand.

Le 12/08 : un correctif a ajoute un appel a /api/engagement_cles dans le
parcours. La configuration nginx n'a pas suivi. Meme fuite, meme cause.

Le motif est clair : la liste des exemptions est maintenue a la main, le
parcours de vote evolue, et les deux se desynchronisent silencieusement. Aucun
test ne pouvait le voir puisque rien ne reliait les deux fichiers.

CE QUE FAIT CE TEST
Il extrait tous les appels reseau de static/vote.html et verifie que chaque
chemin a son bloc `location =` avec `access_log off` dans la configuration
nginx. Ajouter un appel sans ajouter le bloc fait echouer la suite.

CE QU'IL NE FAIT PAS
Il ne verifie pas la configuration REELLEMENT en vigueur sur le serveur, mais
celle du depot. Un ecart entre les deux resterait invisible -- c'est un
controle a faire au deploiement.
"""

import os
import re
import sys

# tests/ etant un sous-repertoire, la racine du depot est le parent.
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOTE = os.path.join(RACINE, "static", "vote.html")
NGINX = os.path.join(RACINE, "infra", "nginx-vera-consultation.conf")

# Requetes que le navigateur emet sans qu'elles apparaissent dans le code.
IMPLICITES = ["/vote", "/static/blindrsa-bundle.js", "/favicon.ico"]


def chemins_appeles():
    """Chemins que la page de vote sollicite, code et implicites confondus."""
    html = open(VOTE, encoding="utf-8").read()
    chemins = set(IMPLICITES)

    # fetch(`${API_BASE}/xxx`) -> /api/xxx
    for m in re.finditer(r"fetch\(\s*`\$\{API_BASE\}(/[a-zA-Z0-9_\-]+)", html):
        chemins.add("/api" + m.group(1))
    # fetch('/xxx') ou fetch("/xxx")
    for m in re.finditer(r"""fetch\(\s*['"](/[a-zA-Z0-9_\-/\.]+)""", html):
        chemins.add(m.group(1))
    # <script src="/xxx">
    for m in re.finditer(r"""<script[^>]+src=["'](/[^"']+)""", html):
        chemins.add(m.group(1))
    return chemins


def chemins_exemptes():
    """Chemins dont le bloc nginx coupe la journalisation."""
    conf = open(NGINX, encoding="utf-8").read()
    exemptes = set()
    for m in re.finditer(r"location\s*=\s*(\S+)\s*\{([^}]*)\}", conf):
        if "access_log off" in m.group(2):
            exemptes.add(m.group(1))
    return exemptes


def main():
    print("Test : routes du parcours de vote exemptees de journalisation")
    print("-" * 62)

    for f in (VOTE, NGINX):
        if not os.path.exists(f):
            print(f"ECHEC : fichier introuvable -- {f}")
            return 2

    appeles = chemins_appeles()
    exemptes = chemins_exemptes()

    print(f"Requetes du parcours de vote : {len(appeles)}")
    for c in sorted(appeles):
        marque = "OK  " if c in exemptes else "FUITE"
        print(f"  {marque}  {c}")

    manquants = sorted(appeles - exemptes)
    print("-" * 62)

    if manquants:
        print("ECHEC : ces requetes laissent IP et horodatage dans access.log :")
        for c in manquants:
            print(f"  {c}")
        print()
        print("Chacune est emise par le navigateur du votant a l'ouverture de")
        print("son lien. Un lecteur du journal obtient la liste horodatee a la")
        print("seconde des personnes ayant ouvert leur page, par IP.")
        print()
        print("Ajoutez dans infra/nginx-vera-consultation.conf, AVANT `location /` :")
        for c in manquants:
            print(f"""
    location = {c} {{
        access_log off;
        limit_req zone=vera_vote burst=50 nodelay;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}""")
        return 1

    print("Toutes les requetes du parcours de vote sont exemptees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
