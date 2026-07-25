#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_antirejeu_persistant.py -- Porte 14 : l'anti-rejeu doit survivre a un
redemarrage.

Reecrit le 25/07/2026 pour le Modele B. La version precedente passait par
generer_token_signe() et verifier_et_consommer(), methodes du Modele A qui
levent desormais RuntimeError : le test plantait avant toute assertion depuis
le refactor, et l'invariant n'etait plus couvert par aucun test Python.

Scenario Modele B : enregistrer un vote (donc une empreinte K en base),
simuler un redemarrage en recreant le gestionnaire, verifier que l'empreinte
est rechargee ET qu'un rejeu du meme K est refuse par la contrainte de base.

Isolation : VERA_DB_PATH doit pointer vers une base jetable (impose par le
garde-fou de vera_persistance).
"""

import os
import sys
import hashlib

if "VERA_DB_PATH" not in os.environ:
    print("Ce test exige VERA_DB_PATH vers une base jetable.")
    print("Exemple : VERA_DB_PATH=/tmp/antirejeu.db python3 " + sys.argv[0])
    sys.exit(1)

import vera_persistance as p
import vera_signature_manager as vsm


class Echec(Exception):
    pass


def _ok(msg):
    print("OK   " + msg)


def main():
    print("Test anti-rejeu PERSISTANT (Porte 14, Modele B)")
    print("-" * 55)
    ok = True
    p.initialiser()

    K = b"secret_de_test_pour_anti_rejeu_32"
    empreinte = hashlib.sha384(K).hexdigest()

    # 1. Enregistrer un vote : l'empreinte de K part en base.
    try:
        p.enregistrer_vote_atomique("dept_A", "oui", empreinte)
        _ok("1. vote enregistre, empreinte K persistee")
    except Exception as e:
        print("FAIL 1. " + str(e)); ok = False

    # 2. L'empreinte est-elle bien en base ?
    try:
        consommes = p.charger_tokens_consommes()
        if empreinte not in consommes:
            raise Echec("empreinte absente de la base -- persistance cassee")
        _ok("2. empreinte presente en base (persistee)")
    except Echec as e:
        print("FAIL 2. " + str(e)); ok = False

    # 3. SIMULER UN REDEMARRAGE : un nouveau gestionnaire doit recharger
    #    l'anti-rejeu depuis la base dans son cache memoire.
    try:
        g2 = vsm.GestionnaireSignature()
        if empreinte not in g2._tokens_consommes:
            raise Echec("le nouveau gestionnaire n'a PAS recharge l'empreinte "
                        "-- un rejeu passerait apres redemarrage")
        _ok("3. apres redemarrage simule, empreinte rechargee en memoire")
    except Echec as e:
        print("FAIL 3. " + str(e)); ok = False

    # 4. Le rejeu est-il refuse ? La DB est l'autorite : l'INSERT strict doit
    #    lever DoubleVoteErreur, meme sur un gestionnaire neuf.
    try:
        try:
            p.enregistrer_vote_atomique("dept_A", "oui", empreinte)
            raise Echec("le rejeu a ete ACCEPTE -- double vote possible")
        except p.DoubleVoteErreur:
            _ok("4. rejeu du meme K refuse (DoubleVoteErreur)")
    except Echec as e:
        print("FAIL 4. " + str(e)); ok = False

    # 5. Le compteur n'a PAS ete incremente par le rejeu.
    try:
        compteurs, _eff = p.charger_compteurs()
        n = compteurs.get("dept_A", {}).get("oui", 0)
        if n != 1:
            raise Echec("compteur a " + str(n) + " au lieu de 1 -- le rejeu a compte")
        _ok("5. compteur inchange par le rejeu (1 vote, pas 2)")
    except Echec as e:
        print("FAIL 5. " + str(e)); ok = False

    print("-" * 55)
    print("ANTI-REJEU PERSISTANT : valide." if ok else "ECHEC : anti-rejeu non garanti.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
