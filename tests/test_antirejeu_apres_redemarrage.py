#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_antirejeu_apres_redemarrage.py -- Porte 14 : survie de l'anti-rejeu.

CE QUE CE TEST PROTEGE
Un secret deja consomme ne doit JAMAIS redevenir utilisable apres un
redemarrage du service. Si cette propriete cassait, un votant pourrait voter,
attendre un redemarrage (crash, reboot, deploiement) et revoter avec le meme
credential. Le double vote deviendrait possible, sans aucune trace.

POURQUOI CE TEST EXISTE ALORS QUE LE MECANISME FONCTIONNE
Il fonctionne, et il a ete verifie a la main. Ce test ne prouve pas qu'il
marche aujourd'hui : il signale le jour ou une modification le cassera. Le
projet a deja connu deux regressions silencieuses de ce type, dont une porte
fermee rouverte par une fonctionnalite posterieure et non detectee pendant
quatorze jours.

Le redemarrage est simule fidelement : fermeture de la connexion SQLite et
rechargement du module, ce qui reproduit ce que fait le service au boot
(charger_tokens_consommes repeuple le registre memoire depuis la base).

NB : l'anti-rejeu n'est pas une ecriture separee. Il est ATOMIQUE avec le
depot du vote (enregistrer_vote_atomique) : l'empreinte et le compteur sont
ecrits dans une seule transaction, ou pas du tout. Ce test exerce donc le
vrai chemin de production, pas une fonction utilitaire.
"""

import importlib
import sys

import vera_persistance as p


class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def _simuler_redemarrage():
    """Recharge le module comme le ferait un demarrage de service.

    L'etat memoire est perdu, seule la base sur disque subsiste -- c'est
    exactement la situation d'un crash suivi d'un redemarrage par systemd.
    """
    p._conn.close()
    importlib.reload(p)
    p.initialiser()
    return p


def main():
    print("Test Porte 14 -- anti-rejeu apres redemarrage")
    print("-" * 55)
    ok = True

    p.initialiser()

    DEPT = "Service Test"
    EMPREINTE_A = "a" * 64   # empreinte SHA-256 fictive, format realiste
    EMPREINTE_B = "b" * 64

    # 1. Un vote enregistre marque son empreinte comme consommee.
    try:
        p.enregistrer_vote_atomique(DEPT, "oui", EMPREINTE_A)
        if EMPREINTE_A not in p.charger_tokens_consommes():
            raise Echec("empreinte absente apres enregistrement du vote")
        _ok("1. le vote marque son empreinte comme consommee")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. Le rejeu immediat est refuse (avant tout redemarrage).
    #    L'INSERT est strict et vient en premier dans la transaction : un
    #    doublon leve AVANT que le compteur ne soit touche.
    try:
        try:
            p.enregistrer_vote_atomique(DEPT, "non", EMPREINTE_A)
            raise Echec("le rejeu immediat a ete ACCEPTE : double vote possible")
        except p.DoubleVoteErreur:
            pass
        _ok("2. le rejeu immediat est refuse (DoubleVoteErreur)")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. Le compteur n'a PAS bouge lors du rejeu refuse.
    #    Verifie l'atomicite : si l'INSERT anti-rejeu leve, aucune autre
    #    ecriture ne doit avoir eu lieu. Un compteur a 2 signifierait que le
    #    vote refuse a quand meme ete compte.
    try:
        compteurs, effectifs = p.charger_compteurs()
        if effectifs.get(DEPT) != 1:
            raise Echec(
                f"effectif = {effectifs.get(DEPT)} au lieu de 1 : le vote "
                "refuse a quand meme ete compte (atomicite rompue)"
            )
        _ok("3. le rejeu refuse n'incremente aucun compteur (atomicite)")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. LE TEST CENTRAL : l'empreinte survit au redemarrage.
    #    Si celui-ci tombe, l'anti-rejeu ne protege plus qu'entre deux
    #    redemarrages -- autant dire qu'il ne protege pas.
    try:
        module = _simuler_redemarrage()
        if EMPREINTE_A not in module.charger_tokens_consommes():
            raise Echec(
                "l'empreinte a DISPARU apres redemarrage : un secret deja "
                "consomme redeviendrait utilisable"
            )
        _ok("4. l'empreinte survit au redemarrage")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. Et le rejeu reste refuse APRES redemarrage.
    #    C'est la propriete reellement utile : le test 4 verifie la lecture,
    #    celui-ci verifie que le refus s'applique effectivement.
    try:
        try:
            p.enregistrer_vote_atomique(DEPT, "non", EMPREINTE_A)
            raise Echec(
                "le rejeu APRES redemarrage a ete ACCEPTE : un votant pourrait "
                "voter deux fois en attendant un reboot"
            )
        except p.DoubleVoteErreur:
            pass
        _ok("5. le rejeu reste refuse apres redemarrage")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    # 6. Une empreinte jamais vue reste acceptee.
    #    Garde-fou : sans ce test, une fonction qui refuserait TOUT ferait
    #    passer les tests 2 et 5 pour de mauvaises raisons.
    try:
        p.enregistrer_vote_atomique(DEPT, "oui", EMPREINTE_B)
        compteurs, effectifs = p.charger_compteurs()
        if effectifs.get(DEPT) != 2:
            raise Echec("un vote legitime n'a pas ete compte")
        _ok("6. un vote legitime reste accepte")
    except Echec as e:
        print(f"ECHEC 6. {e}")
        ok = False

    # 7. La cloture efface le registre.
    #    Contrepartie : l'etat survit aux crashs, mais doit disparaitre a la
    #    cloture volontaire. Les deux exigences coexistent.
    try:
        p.effacer_etat_consultation()
        if EMPREINTE_A in p.charger_tokens_consommes():
            raise Echec("l'empreinte subsiste apres cloture")
        _ok("7. la cloture efface le registre anti-rejeu")
    except Echec as e:
        print(f"ECHEC 7. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("ANTI-REJEU : atomique, persistant au redemarrage, efface a la cloture.")
        return 0
    print("ECHEC : la garantie anti-rejeu n'est plus assuree.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
