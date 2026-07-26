#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_admin_auth.py -- Authentification RH. Comble un trou de couverture :
vera_admin_auth n'avait aucun test dedie. Verifie le hachage, la verification
des identifiants, et le cycle de vie des sessions.
"""

import sys
import time
import vera_admin_auth as auth


class Echec(Exception):
    pass

def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test authentification RH (vera_admin_auth)")
    print("-" * 50)
    ok = True

    # 1. Creation de compte + bon mot de passe accepte.
    try:
        if not auth.creer_compte("org1", "motdepasse_correct"):
            raise Echec("creation du compte devrait reussir")
        if not auth.verifier_identifiants("org1", "motdepasse_correct"):
            raise Echec("le bon mot de passe devrait etre accepte")
        _ok("1. compte cree, bon mot de passe accepte")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Mauvais mot de passe rejete.
    try:
        if auth.verifier_identifiants("org1", "mauvais_mdp"):
            raise Echec("un mauvais mot de passe ne devrait jamais etre accepte")
        _ok("2. mauvais mot de passe rejete")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. Compte inexistant rejete (sans crash).
    try:
        if auth.verifier_identifiants("compte_fantome", "peu_importe"):
            raise Echec("un compte inexistant ne devrait jamais s'authentifier")
        _ok("3. compte inexistant rejete proprement")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. Pas de doublon de compte.
    try:
        if auth.creer_compte("org1", "autre"):
            raise Echec("creer un compte deja existant devrait retourner False")
        _ok("4. creation d'un compte deja existant refusee")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. Session valide apres ouverture, invalide apres fermeture.
    try:
        jeton = auth.ouvrir_session("org1")
        if auth.session_valide(jeton) != "org1":
            raise Echec("la session ouverte devrait etre valide et rendre 'org1'")
        auth.fermer_session(jeton)
        if auth.session_valide(jeton) is not None:
            raise Echec("la session fermee ne devrait plus etre valide")
        _ok("5. session valide a l'ouverture, invalide apres fermeture")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    # 6. Jeton de session inconnu rejete.
    try:
        if auth.session_valide("sess_inexistant") is not None:
            raise Echec("un jeton de session inconnu devrait etre rejete")
        _ok("6. jeton de session inconnu rejete")
    except Echec as e:
        print(f"FAIL 6. {e}"); ok = False

    # 7. Le sel rend deux hash du meme mdp differents.
    try:
        auth.creer_compte("org2", "motdepasse_correct")  # meme mdp que org1
        h1 = auth._comptes_rh["org1"]["hash_mdp"]
        h2 = auth._comptes_rh["org2"]["hash_mdp"]
        if h1 == h2:
            raise Echec("deux comptes au meme mdp devraient avoir des hash differents (sel)")
        _ok("7. sel par compte : meme mot de passe -> hash differents")
    except Echec as e:
        print(f"FAIL 7. {e}"); ok = False

    # 8. EXPIRATION DE SESSION. Trou signale par l'audit du 25/07 : les sept
    #    tests ci-dessus passaient tous meme si les sessions n'expiraient
    #    JAMAIS. On force l'echeance dans le passe plutot que d'attendre huit
    #    heures.
    try:
        auth.creer_compte("compte_expiration", "motdepasse123")
        jeton_exp = auth.ouvrir_session("compte_expiration")
        if auth.session_valide(jeton_exp) != "compte_expiration":
            raise Echec("session fraiche deja invalide")
        auth._sessions[jeton_exp]["expire_a"] = time.time() - 1
        if auth.session_valide(jeton_exp) is not None:
            raise Echec("une session EXPIREE est encore acceptee -- un cookie "
                        "vole resterait valable indefiniment")
        if jeton_exp in auth._sessions:
            raise Echec("session expiree non purgee du registre (fuite memoire)")
        _ok("8. session expiree refusee et purgee du registre")
    except Echec as e:
        print(f"FAIL 8. {e}"); ok = False

    print("-" * 50)
    if ok:
        print("AUTH RH : hachage, verification et sessions valides.")
        sys.exit(0)
    else:
        print("ECHEC -- l'authentification ne se comporte pas comme attendu.")
        sys.exit(1)


if __name__ == "__main__":
    main()
