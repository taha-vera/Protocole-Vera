#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_persistance.py -- Persistance SQLite chiffree (Portes 11 et 14).
Comble le dernier trou de couverture du chemin critique.

ISOLATION TOTALE : le test surcharge DB_PATH vers un fichier TEMPORAIRE et
definit une VERA_DB_KEY de test AVANT initialiser(). La base de production
(/root/vera_state.db) et la vraie cle ne sont JAMAIS touchees. Le fichier
temporaire est supprime a la fin.

Verifie : round-trip des donnees (compteurs, effectifs, budget, codes,
resultats), chiffrement/dechiffrement de la cle RSA (salt aleatoire),
et effacement complet (cloture).
"""

import os
import sys
import tempfile
from pathlib import Path

# --- Environnement de test AVANT tout import qui lirait VERA_DB_KEY ---
os.environ["VERA_DB_KEY"] = "cle_de_test_jetable_pour_ce_test_uniquement"

import vera_persistance as p

# Surcharge du chemin vers une base temporaire jetable
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
p.DB_PATH = Path(_tmp.name)


class Echec(Exception):
    pass

def _ok(nom):
    print(f"OK   {nom}")


def _nettoyer():
    for suffixe in ("", "-wal", "-shm"):
        chemin = Path(str(_tmp.name) + suffixe)
        try:
            chemin.unlink()
        except FileNotFoundError:
            pass


def main():
    print("Test persistance SQLite chiffree (base temporaire jetable)")
    print("-" * 58)
    ok = True

    try:
        p.initialiser()
        _ok("0. initialisation (tables creees sur base temporaire)")
    except Exception as e:
        print(f"FAIL 0. initialisation : {e}")
        _nettoyer()
        sys.exit(1)

    # 1. Round-trip compteurs + effectifs
    try:
        p.persister_vote("A", "oui", 5, 12)
        p.persister_vote("A", "non", 3, 12)
        compteurs, effectifs = p.charger_compteurs()
        if compteurs.get("A", {}).get("oui") != 5 or compteurs.get("A", {}).get("non") != 3:
            raise Echec(f"compteurs incorrects: {compteurs}")
        if effectifs.get("A") != 12:
            raise Echec(f"effectif incorrect: {effectifs}")
        _ok("1. round-trip compteurs + effectifs")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Round-trip budget epsilon
    try:
        p.persister_budget_epsilon("A", 0.5, 1)
        budget = p.charger_budget_epsilon()
        if abs(budget.get("A", {}).get("epsilon_consomme", 0) - 0.5) > 1e-9:
            raise Echec(f"budget incorrect: {budget}")
        _ok("2. round-trip budget epsilon")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. (retire le 12/08) Le mecanisme de code court a ete supprime : sa table
    #    conservait le jeton EN CLAIR, alors que le reste du systeme etait passe
    #    aux empreintes precisement pour qu'un lecteur de base ne puisse pas
    #    rejouer un jeton et priver son titulaire de son vote. Aucun endpoint ne
    #    l'alimentait plus ; seul ce test l'exercait encore.

    # 4. Round-trip resultat publie
    try:
        p.persister_resultat_publie("A", {"oui": 5, "non": 3})
        r = p.charger_resultat_publie("A")
        if r != {"oui": 5, "non": 3}:
            raise Echec(f"resultat publie incorrect: {r}")
        _ok("4. round-trip resultat publie fige")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. Chiffrement / dechiffrement de la cle RSA (Porte 11)
    try:
        cle_privee = b"FAUSSE_CLE_PRIVEE_POUR_TEST_1234567890"
        cle_publique = b"FAUSSE_CLE_PUBLIQUE_POUR_TEST"
        p.persister_cle_rsa_chiffree("DeptTest", cle_privee, cle_publique, 1234567.0)
        rechargee = p.charger_cle_rsa_chiffree("DeptTest")
        if rechargee is None:
            raise Echec("cle RSA non rechargee")
        cp, cpub, ts = rechargee
        if cp != cle_privee or cpub != cle_publique:
            raise Echec("la cle dechiffree ne correspond pas a l'originale")
        _ok("5. chiffrement/dechiffrement cle RSA (round-trip Fernet+salt)")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    # 6. Le chiffrement utilise bien un salt (deux ecritures -> hex different)
    try:
        p.persister_cle_rsa_chiffree("DeptTest", b"meme_cle", b"meme_pub", 1.0)
        row1 = p._conn.execute("SELECT cle_privee_hex, salt_hex FROM cle_rsa_active WHERE departement='DeptTest'").fetchone()
        p.persister_cle_rsa_chiffree("DeptTest", b"meme_cle", b"meme_pub", 1.0)
        row2 = p._conn.execute("SELECT cle_privee_hex, salt_hex FROM cle_rsa_active WHERE departement='DeptTest'").fetchone()
        if row1[1] == row2[1]:
            raise Echec("le salt devrait changer a chaque ecriture")
        if row1[0] == row2[0]:
            raise Echec("le chiffre devrait differer (salt aleatoire)")
        _ok("6. salt aleatoire par ecriture (meme cle -> chiffre different)")
    except Echec as e:
        print(f"FAIL 6. {e}"); ok = False

    # 7. Effacement complet (cloture) : tout est vide, cle RSA preservee
    try:
        p.effacer_etat_consultation()
        compteurs, effectifs = p.charger_compteurs()
        if compteurs or effectifs:
            raise Echec("compteurs/effectifs auraient du etre vides")
        if p.charger_budget_epsilon():
            raise Echec("budget aurait du etre vide")
        # la cle RSA n'est PAS touchee par effacer_etat_consultation
        if p.charger_cle_rsa_chiffree("DeptTest") is None:
            raise Echec("la cle RSA (infrastructure) ne devrait PAS etre effacee")
        _ok("7. effacement etat consultation (tout vide, cle RSA preservee)")
    except Echec as e:
        print(f"FAIL 7. {e}"); ok = False

    _nettoyer()
    print("-" * 58)
    if ok:
        print("PERSISTANCE : round-trips, chiffrement cle RSA et effacement valides.")
        sys.exit(0)
    else:
        print("ECHEC -- la persistance ne se comporte pas comme attendu.")
        sys.exit(1)


if __name__ == "__main__":
    main()
