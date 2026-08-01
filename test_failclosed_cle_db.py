#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_failclosed_cle_db.py -- Porte 11 : refus de demarrer sur mauvaise cle.

CE QUE CE TEST PROTEGE
Si VERA_DB_KEY est erronee au demarrage (faute de frappe dans l'unite systemd,
restauration sur une autre machine, rotation mal appliquee), le service doit
REFUSER de demarrer plutot que d'ignorer les cles existantes et d'en generer de
nouvelles.

Le comportement dangereux, corrige le 01/08 : un echec de dechiffrement etait
avale par un `continue` silencieux. Les cles en base etaient ignorees sans
signal, de nouvelles etaient creees, et TOUS les liens de vote deja distribues
-- qui portent l'empreinte de l'ancienne cle dans leur fragment -- devenaient
invalides en pleine consultation. Le RH ne l'apprenait que par les plaintes des
votants.

Ce test verifie les trois cas, dont deux ou le garde-fou ne doit PAS se
declencher : un garde-fou qui bloque le fonctionnement normal est aussi mauvais
qu'un garde-fou absent.
"""

import importlib
import os
import sys

import vera_persistance as p


class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def _recharger_avec_cle(nouvelle_cle):
    """Simule un demarrage de service avec une VERA_DB_KEY donnee."""
    p._conn.close()
    os.environ["VERA_DB_KEY"] = nouvelle_cle
    importlib.reload(p)
    p.initialiser()
    return p


def main():
    print("Test Porte 11 -- fail-closed sur cle de dechiffrement")
    print("-" * 55)
    ok = True

    cle_correcte = os.environ.get("VERA_DB_KEY", "cle_de_test_" + "a" * 36)
    os.environ["VERA_DB_KEY"] = cle_correcte
    p.initialiser()

    # 1. Base VIDE : le demarrage doit reussir.
    #    C'est le cas legitime d'une rotation de cle apres cloture : la table
    #    est vide, il n'y a rien a dechiffrer, le garde-fou ne doit pas mordre.
    try:
        resultat = p.charger_toutes_cles_chiffrees()
        if resultat != {}:
            raise Echec(f"base vide attendue, obtenu {resultat}")
        _ok("1. base vide : demarrage autorise (rotation legitime)")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False
    except RuntimeError as e:
        print(f"ECHEC 1. le garde-fou bloque une base VIDE : {e}")
        ok = False

    # 2. Cle correcte : la cle persistee se dechiffre.
    try:
        p.persister_cle_rsa_chiffree("DeptTest", b"cle_privee_fictive", b"cle_pub", 1785000000)
        resultat = p.charger_toutes_cles_chiffrees()
        if "DeptTest" not in resultat:
            raise Echec("la cle persistee ne se recharge pas avec la BONNE cle")
        if resultat["DeptTest"][0] != b"cle_privee_fictive":
            raise Echec("la cle dechiffree ne correspond pas a l'originale")
        _ok("2. cle correcte : dechiffrement nominal")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. LE TEST CENTRAL : mauvaise cle -> refus de demarrer.
    #    Sans ce garde-fou, le service demarrerait et regenererait des cles,
    #    invalidant silencieusement tous les liens en circulation.
    try:
        module = _recharger_avec_cle("MAUVAISE_cle_" + "z" * 36)
        try:
            resultat = module.charger_toutes_cles_chiffrees()
            raise Echec(
                f"AUCUNE exception levee (retour : {resultat}). Le service "
                "demarrerait et regenererait des cles : tous les liens de vote "
                "deja distribues deviendraient invalides sans aucun signal."
            )
        except RuntimeError:
            pass  # comportement attendu
        _ok("3. mauvaise cle : le service REFUSE de demarrer (fail-closed)")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. Le message d'erreur est exploitable par un operateur.
    #    Un fail-closed muet obligerait a fouiller le code pour comprendre.
    try:
        try:
            p.charger_toutes_cles_chiffrees()
            raise Echec("pas d'exception au second appel")
        except RuntimeError as e:
            message = str(e)
            if "VERA_DB_KEY" not in message:
                raise Echec(
                    "le message ne mentionne pas VERA_DB_KEY : l'operateur ne "
                    f"saura pas quoi corriger. Message : {message[:80]}"
                )
        _ok("4. le message d'erreur nomme la variable a corriger")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("FAIL-CLOSED : bloque sur mauvaise cle, laisse passer les cas legitimes.")
        return 0
    print("ECHEC : le garde-fou sur la cle de dechiffrement ne fonctionne plus.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
