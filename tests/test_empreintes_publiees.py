#!/usr/bin/env python3
"""Garde structurelle : VERIFICATION_CLIENT.md doit decrire les fichiers du depot.

POURQUOI CE TEST EXISTE

Le 22/08/2026, un correctif de bourrage a modifie static/vote.html. Le document
qui publie son empreinte n'a pas suivi. Pendant sept jours, tout tiers appliquant
la procedure du README -- `curl .../vote | sha256sum`, comparaison a
VERIFICATION_CLIENT.md -- obtenait une DIVERGENCE, c'est-a-dire exactement le
signal que cette procedure existe pour produire en cas de client modifie.

Une verification qui se declenche a tort ne protege plus : elle apprend a son
lecteur a l'ignorer. C'est le troisieme cas de porte rouverte par une
modification ulterieure, et le premier a toucher le mecanisme de detection
lui-meme.

Ce test ferme la CLASSE : toute modification de static/vote.html ou de
static/blindrsa-bundle.js qui ne s'accompagne pas de la mise a jour des
empreintes publiees fait echouer le workflow, a chaque push.

Il est STRUCTUREL : il lit des fichiers, sans base, sans module Rust, sans
opendp. Il tourne sur n'importe quel Python.
"""

import base64
import hashlib
import pathlib
import re
import sys

# tests/ etant un sous-repertoire, la racine du depot est le parent.
RACINE = pathlib.Path(__file__).resolve().parent.parent
DOC = RACINE / "VERIFICATION_CLIENT.md"
PAGE = RACINE / "static" / "vote.html"
BUNDLE = RACINE / "static" / "blindrsa-bundle.js"

echecs = []


def sha256(chemin):
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def sha384_b64(chemin):
    return "sha384-" + base64.b64encode(
        hashlib.sha384(chemin.read_bytes()).digest()).decode()


texte = DOC.read_text(encoding="utf-8")

# 1. Les empreintes SHA-256 publiees, par nom de fichier.
publiees = dict(
    (nom, empreinte)
    for empreinte, nom in re.findall(
        r"([0-9a-f]{64})\s+(static/[A-Za-z0-9_.\-]+)", texte)
)

for chemin in (PAGE, BUNDLE):
    cle = "static/" + chemin.name
    reelle = sha256(chemin)
    if cle not in publiees:
        echecs.append(
            f"{cle} : aucune empreinte SHA-256 publiee dans {DOC.name}. "
            f"Empreinte reelle : {reelle}")
    elif publiees[cle] != reelle:
        echecs.append(
            f"{cle} : empreinte publiee perimee.\n"
            f"    publiee dans {DOC.name} : {publiees[cle]}\n"
            f"    reelle                  : {reelle}\n"
            f"    -> un tiers appliquant la procedure du README verrait une "
            f"divergence, c'est-a-dire le signal d'un client modifie.")

# 2. L'empreinte SRI publiee doit etre celle du bundle.
sri_reel = sha384_b64(BUNDLE)
sri_publies = re.findall(r"sha384-[A-Za-z0-9+/=]{60,}", texte)
if not sri_publies:
    echecs.append(f"{DOC.name} : aucune empreinte SHA-384 publiee.")
elif sri_reel not in sri_publies:
    echecs.append(
        f"{DOC.name} : l'empreinte SHA-384 publiee ne correspond pas au "
        f"bundle.\n    publiee : {sri_publies[0]}\n    reelle  : {sri_reel}")

# 3. L'attribut integrity de la page de vote doit etre celui du bundle.
#    Qui sert la page sert l'attribut : ce controle ne protege pas d'un
#    operateur actif (LIMITS.md section 6). Il garantit seulement que la page
#    du DEPOT est coherente avec le bundle du DEPOT -- sans quoi le navigateur
#    refuserait de charger le module cryptographique et aucun vote
#    n'aboutirait. Ce cas s'est produit (commit 1c3d938).
page = PAGE.read_text(encoding="utf-8")
attributs = re.findall(r'integrity="(sha384-[A-Za-z0-9+/=]+)"', page)
if not attributs:
    echecs.append(
        "static/vote.html : aucun attribut integrity. Le module "
        "cryptographique serait charge sans verification par le navigateur.")
elif sri_reel not in attributs:
    echecs.append(
        f"static/vote.html : l'attribut integrity ne correspond pas au "
        f"bundle servi.\n    declare : {attributs[0]}\n    reel    : {sri_reel}"
        f"\n    -> le navigateur refuserait de charger le module : aucun vote "
        f"n'aboutirait.")

if echecs:
    print("ECHEC : empreintes publiees et fichiers du depot divergent.\n")
    for e in echecs:
        print("  - " + e)
    print("\nPour reparer, depuis la racine du depot :")
    print("    sha256sum static/vote.html static/blindrsa-bundle.js")
    print("    openssl dgst -sha384 -binary static/blindrsa-bundle.js "
          "| openssl base64 -A")
    print("puis reporter ces valeurs dans VERIFICATION_CLIENT.md "
          "(et dans l'attribut integrity de static/vote.html).")
    sys.exit(1)

print("OK : empreintes publiees, attribut SRI et fichiers du depot concordent.")
sys.exit(0)
