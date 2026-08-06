#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_separation_phases.py -- l'emission et les depots sont separes dans le temps.

CE QUE CE TEST PROTEGE
L'unlinkability cryptographique ne suffit pas si les deux registres peuvent
etre rapproches par le temps. Le serveur voit un jeton consomme a 14h02:11 --
donc une identite, via la liste de l'organisation -- puis un vote depose a
14h02:47. Il n'a rien a casser : la proximite temporelle joint les deux
registres que tout le protocole existe pour tenir disjoints. Dans un groupe de
douze personnes, cela suffit a savoir qui a repondu quoi.

Fixer une date d'ouverture posterieure a la fin de l'envoi des invitations
garantit qu'entre l'obtention d'un credential et son depot, beaucoup d'autres
se sont intercales.

CE QUE CE TEST NE PROTEGE PAS
La correlation reste possible si le RH fixe une ouverture immediate, ou s'il
n'en fixe aucune. Le controle technique verifie que la date est respectee ; il
ne verifie pas qu'elle est bien choisie. C'est une limite documentee.
"""

import os
import sys
import time

import vera_persistance as p


class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test separation des phases -- emission / depots")
    print("-" * 55)
    ok = True

    p.initialiser()

    # 1. Aucune date fixee : les depots sont ouverts.
    #    Comportement des consultations anterieures, qu'on ne casse pas.
    try:
        if p.charger_ouverture_depots() is not None:
            raise Echec("une date existe alors qu'aucune n'a ete fixee")
        _ok("1. sans date fixee : depots ouverts (retrocompatible)")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. Une date future est persistee et relue exactement.
    try:
        futur = time.time() + 3600
        p.persister_ouverture_depots(futur)
        lu = p.charger_ouverture_depots()
        if lu is None:
            raise Echec("la date n'a pas ete persistee")
        if abs(lu - futur) > 0.001:
            raise Echec(f"date alteree : {lu} au lieu de {futur}")
        _ok("2. une date future est persistee et relue exactement")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. LE TEST CENTRAL : avant l'ouverture, les depots doivent etre refuses.
    #    On verifie ici la condition que l'API applique.
    try:
        ouverture = p.charger_ouverture_depots()
        if not (time.time() < ouverture):
            raise Echec("la condition de refus n'est pas remplie alors que "
                        "l'ouverture est dans une heure")
        _ok("3. avant l'ouverture : la condition de refus s'applique")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. Apres l'ouverture, les depots passent.
    #    Garde-fou : un systeme qui refuserait TOUJOURS ferait passer le test 3
    #    pour une mauvaise raison.
    try:
        passe = time.time() - 10
        p.persister_ouverture_depots(passe)
        ouverture = p.charger_ouverture_depots()
        if time.time() < ouverture:
            raise Echec("les depots restent refuses alors que l'heure est passee")
        _ok("4. apres l'ouverture : les depots sont acceptes")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. La date survit a un redemarrage.
    #    Sans persistance, un redemarrage rouvrirait les depots prematurement
    #    et la separation ne vaudrait qu'entre deux crashs.
    try:
        futur = time.time() + 7200
        p.persister_ouverture_depots(futur)
        import importlib
        p._conn.close()
        importlib.reload(p)
        p.initialiser()
        lu = p.charger_ouverture_depots()
        if lu is None or abs(lu - futur) > 0.001:
            raise Echec("la date n'a pas survecu au redemarrage")
        _ok("5. la date survit a un redemarrage")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    # 6. La cloture efface la date avec le reste.
    #    Elle ne doit pas fuiter d'une consultation a la suivante.
    try:
        p.effacer_etat_consultation()
        if p.charger_ouverture_depots() is not None:
            raise Echec("la date subsiste apres cloture")
        _ok("6. la cloture efface la date d'ouverture")
    except Echec as e:
        print(f"ECHEC 6. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("SEPARATION DES PHASES : date persistee, respectee, effacee a la cloture.")
        return 0
    print("ECHEC : la separation emission/depots n'est plus garantie.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
