#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_porte8_composition.py -- Porte 4 : la composition ne permet pas de
supprimer le bruit par moyennage.

Reecrit le 25/07/2026. La version precedente simulait l'attaque par moyennage
sur k tirages (le bruit decroit en 1/racine(k)) et imprimait un tableau, sans
aucune assertion ni code de sortie. Elle mesurait donc un DANGER THEORIQUE,
pas la PARADE reellement implementee.

La parade de VERA est structurelle, pas statistique : le resultat bruite est
FIGE a la premiere publication. Republier renvoie le meme resultat, jamais un
nouveau tirage -- il n'y a donc pas k echantillons a moyenner, quel que soit le
nombre d'appels. Et le budget epsilon n'autorise qu'une publication.

Ce test verifie la parade sur le code de production.
"""

import os
import sys

if "VERA_DB_PATH" not in os.environ:
    print("Ce test exige VERA_DB_PATH vers une base jetable.")
    sys.exit(1)

import vera_persistance as p
from vera_epsilon_budget import BudgetEpsilonParDepartement


class Echec(Exception):
    pass


def _ok(msg):
    print("OK   " + msg)


def main():
    print("Test Porte 4 : pas de suppression du bruit par moyennage")
    print("-" * 60)
    p.initialiser()
    ok = True

    resultat_fige = {"oui": 123, "non": 84, "abstention": 43}
    p.persister_publication_atomique("DeptComp", 0.5, 1, resultat_fige)

    # 1. Relire N fois doit rendre EXACTEMENT le meme resultat. Si chaque
    #    lecture retirait du bruit, un adversaire moyennerait N tirages et
    #    ferait tendre l'erreur vers zero (epsilon effectif -> infini).
    try:
        lectures = [p.charger_resultat_publie("DeptComp") for _ in range(50)]
        if any(l != resultat_fige for l in lectures):
            raise Echec("une relecture a renvoye un resultat DIFFERENT "
                        "-- du bruit est re-tire, le moyennage devient possible")
        _ok("1. 50 relectures : resultat identique (fige, pas de nouveau tirage)")
    except Echec as e:
        print("FAIL 1. " + str(e)); ok = False

    # 2. Le budget n'autorise qu'UNE publication a epsilon=0.5.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("DeptComp", 0.5)
        if b.peut_publier("DeptComp", 0.5):
            raise Echec("une seconde publication est autorisee -- la "
                        "composition permettrait deux tirages independants")
        _ok("2. seconde publication refusee par le budget epsilon")
    except Echec as e:
        print("FAIL 2. " + str(e)); ok = False

    # 3. L'invariant anti-lockout : un departement marque publie DOIT avoir
    #    son resultat consultable, sinon republier serait impossible ET le
    #    resultat introuvable.
    try:
        budget = p.charger_budget_epsilon()
        for dept, etat in budget.items():
            if etat["nombre_publications"] > 0 and p.charger_resultat_publie(dept) is None:
                raise Echec(f"{dept} marque publie mais resultat absent")
        _ok("3. tout departement publie a son resultat consultable")
    except Echec as e:
        print("FAIL 3. " + str(e)); ok = False

    print("-" * 60)
    print("PORTE 4 : moyennage impossible, resultat fige." if ok else "ECHEC : composition exploitable.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
