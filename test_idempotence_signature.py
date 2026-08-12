#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_idempotence_signature.py -- une voix n'est plus perdue sur incident reseau.

LE DEFAUT CORRIGE
Le jeton d'autorisation etait consomme AVANT la signature, pour qu'un meme
jeton ne puisse pas produire deux credentials differents. Consequence : si le
navigateur echouait apres que le serveur avait signe -- reseau coupe, onglet
ferme, page rechargee -- la voix etait perdue sans recours. Le jeton etait
brule, et rien ne permettait de retrouver la signature emise.

LA CONSTRUCTION
Le serveur memorise le couple (empreinte du jeton, empreinte du message
aveugle) avec la signature. Un rejeu A L'IDENTIQUE retrouve sa signature. Un
message DIFFERENT presente avec le meme jeton est refuse.

CE QUE CE TEST VERIFIE
  1. Un rejeu identique retrouve la MEME signature.
  2. Un message different avec le meme jeton est detecte -- sans quoi le
     correctif ouvrirait le double vote, ce qui serait pire que le defaut.
  3. La memoire expire, pour ne pas conserver indefiniment le lien
     jeton -> message qui est precisement ce que le protocole evite.
  4. La cloture efface cette table.
  5. La memoire survit a un redemarrage, sans quoi elle ne protegerait que
     contre les incidents survenus entre deux crashs.
"""

import os
import sys
import time

import vera_persistance as p


class Echec(Exception):
    pass


def _ok(nom):
    print("OK   " + nom)


def main():
    print("Test idempotence de la signature aveugle")
    print("-" * 58)
    ok = True
    p.initialiser()

    J1 = "empreinte_jeton_" + "a" * 48
    M1 = "empreinte_message_" + "b" * 46
    M2 = "empreinte_message_" + "c" * 46
    SIG = "aabbcc" * 100

    # 1. Rien avant la premiere signature.
    try:
        if p.signature_deja_emise(J1, M1) is not None:
            raise Echec("une signature existe avant toute emission")
        if p.jeton_a_deja_signe(J1):
            raise Echec("le jeton est marque comme ayant signe avant toute emission")
        _ok("1. etat initial vierge")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. LE CAS QUI COMPTE : rejeu a l'identique -> meme signature.
    #    C'est ce qui evite qu'une voix disparaisse sur un rechargement de page.
    try:
        p.enregistrer_signature_emise(J1, M1, SIG, "Atelier")
        relu = p.signature_deja_emise(J1, M1)
        if relu is None:
            raise Echec("la signature n'a pas ete memorisee")
        if relu[0] != SIG:
            raise Echec(f"signature alteree : {relu[0][:20]} au lieu de {SIG[:20]}")
        if relu[1] != "Atelier":
            raise Echec(f"departement altere : {relu[1]}")
        _ok("2. rejeu identique : la MEME signature est renvoyee")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. LE GARDE-FOU : un message DIFFERENT ne doit pas trouver de signature.
    #    Sans ce test, le correctif pourrait ouvrir le double vote -- un defaut
    #    plus grave que celui qu'il corrige.
    try:
        if p.signature_deja_emise(J1, M2) is not None:
            raise Echec("un message different retrouve une signature : "
                        "un jeton pourrait produire DEUX credentials")
        if not p.jeton_a_deja_signe(J1):
            raise Echec("le jeton n'est pas detecte comme ayant deja signe : "
                        "le refus du second message ne se declencherait pas")
        _ok("3. message different : aucune signature, jeton detecte comme utilise")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. Un autre jeton n'est pas affecte.
    try:
        J2 = "empreinte_jeton_" + "z" * 48
        if p.jeton_a_deja_signe(J2):
            raise Echec("un jeton etranger est marque comme ayant signe")
        _ok("4. un autre jeton reste libre")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. La memoire survit a un redemarrage. Sans cela, elle ne protegerait
    #    que contre les incidents survenus entre deux crashs -- alors qu'un
    #    redemarrage est precisement un moment ou des requetes echouent.
    try:
        import importlib
        p._conn.close()
        importlib.reload(p)
        p.initialiser()
        relu = p.signature_deja_emise(J1, M1)
        if relu is None or relu[0] != SIG:
            raise Echec("la signature n'a pas survecu au redemarrage")
        _ok("5. la memoire survit a un redemarrage")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    # 6. Expiration : la donnee la plus sensible du systeme -- le lien
    #    jeton -> message -- ne doit pas s'accumuler.
    try:
        origine = p.RETENTION_SIGNATURES_SECONDES
        p.RETENTION_SIGNATURES_SECONDES = 1
        J3 = "empreinte_jeton_" + "e" * 48
        p.enregistrer_signature_emise(J3, M1, SIG, "Direction")
        time.sleep(2)
        if p.signature_deja_emise(J3, M1) is not None:
            raise Echec("une signature expiree est toujours servie")
        if p.jeton_a_deja_signe(J3):
            raise Echec("un jeton expire est toujours marque")
        p.RETENTION_SIGNATURES_SECONDES = origine
        _ok("6. la memoire expire apres le delai de retention")
    except Echec as e:
        print(f"ECHEC 6. {e}")
        ok = False

    # 7. La cloture efface tout, sans attendre l'expiration.
    try:
        p.enregistrer_signature_emise(J1, M1, SIG, "Atelier")
        p.effacer_etat_consultation()
        if p.signature_deja_emise(J1, M1) is not None:
            raise Echec("les signatures survivent a la cloture")
        _ok("7. la cloture efface les signatures memorisees")
    except Echec as e:
        print(f"ECHEC 7. {e}")
        ok = False

    print("-" * 58)
    if ok:
        print("IDEMPOTENCE : rejeu identique servi, second message refuse,")
        print("memoire bornee dans le temps et effacee a la cloture.")
        return 0
    print("ECHEC : l'idempotence de la signature n'est plus garantie.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
