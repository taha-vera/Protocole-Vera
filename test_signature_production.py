#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_signature_production.py -- Teste la PRIMITIVE DE PRODUCTION (RSABSSA
RFC 9474, module Rust vera_blind_sig), en memoire pure.

Reecrit le 25/07/2026 pour le Modele B. La version precedente exercait
generer_token_signe() et verifier_et_consommer(), methodes du Modele A qui
levent desormais RuntimeError : le test plantait avant toute assertion.

Intention conservee, et elle est precieuse : exercer la VRAIE primitive
cryptographique, sans base, sans serveur, sans reseau. C'est le seul test de
la chaine complete qui ne depend de rien -- les tests JS equivalents exigent un
serveur vivant. Il tourne en une seconde et attrape toute regression de la
primitive.

Invariants verifies par 'if ... raise' (survit a python -O).
"""

import sys
import vera_blind_sig as vbs


class Echec(Exception):
    pass


def _ok(msg):
    print("OK   " + msg)


def main():
    print("Test PRIMITIVE de production (RSABSSA RFC 9474, memoire pure)")
    print("-" * 60)
    ok = True

    priv, pub = vbs.generer_cles()
    message = list(b"secret_K_de_test_pour_la_primitive_rsabssa_0001")

    # 1. Chaine nominale complete : aveugler, signer, finaliser, verifier.
    try:
        blind_msg, secret, randomizer = vbs.aveugler_message(list(pub), message)
        sig_aveugle = vbs.signer_aveugle(list(priv), list(blind_msg))
        signature = vbs.finaliser_signature(
            list(pub), message, list(blind_msg), list(secret),
            list(sig_aveugle), list(randomizer))
        if not vbs.verifier_signature(list(pub), message, list(signature), list(randomizer)):
            raise Echec("la signature produite par la chaine nominale est REFUSEE")
        _ok("1. chaine complete aveugler/signer/finaliser/verifier")
    except Echec as e:
        print("FAIL 1. " + str(e)); ok = False
        return 1  # sans chaine nominale, le reste n'a pas de sens

    # 2. Le serveur n'a JAMAIS vu le message en clair : ce qu'il signe
    #    (blind_msg) ne contient pas le message. C'est l'aveuglement.
    try:
        if bytes(message) in bytes(blind_msg):
            raise Echec("le message apparait EN CLAIR dans le message aveugle")
        _ok("2. le message n'apparait pas dans le message aveugle")
    except Echec as e:
        print("FAIL 2. " + str(e)); ok = False

    # 3. Signature FORGEE (octets alteres) -> refusee.
    try:
        forgee = list(signature)
        forgee[0] = (forgee[0] + 1) % 256
        if vbs.verifier_signature(list(pub), message, forgee, list(randomizer)):
            raise Echec("une signature alteree a ete ACCEPTEE")
        _ok("3. signature alteree refusee")
    except Echec as e:
        print("FAIL 3. " + str(e)); ok = False

    # 4. Signature valide mais verifiee sous une AUTRE cle -> refusee.
    #    C'est ce qui empeche un jeton d'un departement de voter dans un autre.
    try:
        _priv2, pub2 = vbs.generer_cles()
        if vbs.verifier_signature(list(pub2), message, list(signature), list(randomizer)):
            raise Echec("signature acceptee sous une AUTRE cle publique")
        _ok("4. signature refusee sous une autre cle (isolation par departement)")
    except Echec as e:
        print("FAIL 4. " + str(e)); ok = False

    # 5. Message MODIFIE avec la meme signature -> refuse.
    try:
        autre_message = list(b"secret_K_de_test_pour_la_primitive_rsabssa_9999")
        if vbs.verifier_signature(list(pub), autre_message, list(signature), list(randomizer)):
            raise Echec("signature acceptee sur un message DIFFERENT")
        _ok("5. signature refusee sur un message modifie")
    except Echec as e:
        print("FAIL 5. " + str(e)); ok = False

    # 6. Mauvais randomizer -> refuse. La variante Randomized lie la signature
    #    au sel : le serveur ne peut pas verifier sans lui.
    try:
        mauvais_rand = [(x + 1) % 256 for x in randomizer]
        if vbs.verifier_signature(list(pub), message, list(signature), mauvais_rand):
            raise Echec("signature acceptee avec un randomizer ERRONE")
        _ok("6. signature refusee avec un mauvais randomizer")
    except Echec as e:
        print("FAIL 6. " + str(e)); ok = False

    print("-" * 60)
    print("PRIMITIVE : chaine et rejets valides." if ok else "ECHEC : primitive non conforme.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
