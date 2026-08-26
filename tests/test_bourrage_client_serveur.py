#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bourrage_client_serveur.py -- le bourrage du client doit passer la
validation du serveur.

L'INCIDENT QUI JUSTIFIE CE TEST
Le 22/08, la cible de bourrage du client a ete portee de 200 a 450 octets, pour
corriger un calcul qui comptait des caracteres au lieu d'octets UTF-8. La borne
`max_length` du champ `pad` cote serveur est restee a 200.

Consequence : pour un groupe nomme « RH », le client envoyait un pad de 445
caracteres, rejete en HTTP 422 par Pydantic AVANT d'atteindre le code de vote.
Aucun vote ne pouvait aboutir, et la production est restee dans cet etat
plusieurs heures.

Les 24 tests automatiques n'ont rien vu : aucun n'exerce le chemin HTTP reel
avec le vrai client. Le defaut vit dans la COUTURE entre deux fichiers, chacun
correct isolement.

Aucune dependance : ni base, ni module Rust, ni reseau.
"""

import os
import re
import sys

# tests/ etant un sous-repertoire, la racine du depot est le parent.
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOTE = os.path.join(RACINE, "static", "vote.html")
API = os.path.join(RACINE, "vera_consultation_api.py")


class Echec(Exception):
    pass


def _ok(nom):
    print("OK   " + nom)


def cible_client():
    s = open(VOTE, encoding="utf-8").read()
    m = re.search(r"const LONGUEUR_CIBLE_FIXE = (\d+)", s)
    if not m:
        raise Echec("LONGUEUR_CIBLE_FIXE introuvable dans vote.html")
    return int(m.group(1))


def borne_serveur():
    s = open(API, encoding="utf-8").read()
    d = s.find("class ReponseModeleB(BaseModel):")
    if d == -1:
        raise Echec("ReponseModeleB introuvable")
    m = re.search(r'pad: str = Field\(default="", max_length=(\d+)\)', s[d:d + 2500])
    if not m:
        raise Echec("max_length du champ pad introuvable")
    return int(m.group(1))


def cible_url():
    s = open(VOTE, encoding="utf-8").read()
    m = re.search(r"'x'\.repeat\(Math\.max\(0, (\d+) - _dep\.length\)\)", s)
    if not m:
        raise Echec("cible de bourrage de l'URL introuvable")
    return int(m.group(1))


def main():
    print("Test : le bourrage du client passe la validation du serveur")
    print("-" * 60)
    ok = True

    for f in (VOTE, API):
        if not os.path.exists(f):
            print(f"ECHEC : fichier introuvable -- {f}")
            return 2

    try:
        cible = cible_client()
        borne = borne_serveur()
        _ok(f"1. cible client = {cible} octets, borne serveur = {borne}")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        return 1

    try:
        if borne < cible:
            raise Echec(
                f"la borne serveur ({borne}) est INFERIEURE a la cible client "
                f"({cible}). Un pad de {cible} octets serait rejete en HTTP 422 "
                "avant d'atteindre le code de vote : aucun vote n'aboutirait."
            )
        _ok("2. la borne serveur couvre la cible client")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    try:
        cas = [("RH", "oui"), ("RH", "abstention"), ("Atelier", "non"),
               ("Direction des Ressources Humaines", "abstention"),
               ("e" * 100, "oui"), ("A" * 100, "abstention")]
        for dep, rep in cas:
            pad = max(0, cible - len(rep.encode()) - len(dep.encode()))
            if pad > borne:
                raise Echec(
                    f"groupe « {dep[:20]} » + reponse « {rep} » -> pad de {pad} "
                    f"caracteres, au-dela de la borne {borne}. Rejet en 422."
                )
        _ok(f"3. les {len(cas)} cas reels passent la validation")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    try:
        s = open(VOTE, encoding="utf-8").read()
        if "TextEncoder().encode(departement).length" not in s:
            raise Echec(
                "le bourrage du corps ne semble plus calcule en octets UTF-8. "
                "String.length compte des unites UTF-16 : un nom accentue de "
                "100 caracteres occupe 200 octets, et le bourrage retombe a "
                "zero -- la taille du paquet trahit alors le groupe."
            )
        _ok("4. le bourrage du corps est calcule en octets UTF-8")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    try:
        c = cible_url()
        if c < 900:
            raise Echec(
                f"la cible de bourrage de l'URL ({c}) ne couvre pas le pire cas : "
                "100 caracteres a 9 octets encodes font 900."
            )
        _ok(f"5. la cible de l'URL ({c}) couvre le pire cas d'encodage")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    print("-" * 60)
    if ok:
        print("BOURRAGE COHERENT entre le client et le serveur.")
        return 0
    print("ECHEC : le client et le serveur ne s'accordent pas sur le bourrage.")
    print("Consequence probable : rejet HTTP 422 sur tout depot de vote.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
