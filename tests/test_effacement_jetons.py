#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_effacement_jetons.py -- la cloture efface bien le registre 1.

Reecrit le 25/07/2026. La version precedente avait deux defauts :
- elle supposait la table VIDE au depart (assertion len(avant) == 2), donc
  echouait a la deuxieme execution sur la meme base -- un test fragile pousse
  a ignorer ses echecs, ce qui est pire qu'une absence de test ;
- elle ne verifiait que les jetons, alors que effacer_etat_consultation()
  promet de vider SEPT tables et de preserver la cle RSA.

Elle n'avait par ailleurs aucune base jetable : lancee sur le serveur, elle
detruisait la consultation en cours, registre anti-rejeu compris, rouvrant le
double-vote pour tout K deja utilise. Le garde-fou de vera_persistance
l'empeche desormais (VERA_DB_PATH obligatoire), mais ce fichier reste
l'illustration du risque.
"""

import os
import sys

if "VERA_DB_PATH" not in os.environ:
    print("Ce test exige VERA_DB_PATH vers une base jetable.")
    sys.exit(1)

import vera_persistance as p


def main():
    print("Test effacement de cloture (registre 1 et etat complet)")
    print("-" * 55)
    p.initialiser()
    ok = True

    # 1. Poser de l'etat dans PLUSIEURS tables, sans supposer l'etat initial.
    n_avant = len(p.charger_jetons_autorisation())
    p.persister_jeton_autorisation("jeton_effacement_A", "dept_eff")
    p.persister_jeton_autorisation("jeton_effacement_B", "dept_eff")
    p.enregistrer_vote_atomique("dept_eff", "oui", "empreinte_effacement_test")
    p.persister_publication_atomique("dept_eff", 0.5, 1, {"oui": 1, "non": 0})

    n_apres_pose = len(p.charger_jetons_autorisation())
    if n_apres_pose != n_avant + 2:
        print(f"FAIL 1. jetons non enregistres ({n_avant} -> {n_apres_pose})")
        ok = False
    else:
        print("OK   1. etat pose (2 jetons, 1 vote, 1 publication)")

    # 2. Cloture.
    p.effacer_etat_consultation()

    # 3. TOUTES les tables d'etat doivent etre vides, pas seulement les jetons.
    restes = {
        "jetons_autorisation": len(p.charger_jetons_autorisation()),
        "tokens_consommes": len(p.charger_tokens_consommes()),
        "budget_epsilon": len(p.charger_budget_epsilon()),
    }
    compteurs, effectifs = p.charger_compteurs()
    restes["compteurs_votes"] = len(compteurs)
    restes["effectifs"] = len(effectifs)
    restes["resultats_publies"] = 1 if p.charger_resultat_publie("dept_eff") else 0

    non_vides = {t: n for t, n in restes.items() if n != 0}
    if non_vides:
        print(f"FAIL 2. tables non videes par la cloture : {non_vides}")
        ok = False
    else:
        print("OK   2. les six tables d'etat sont vides apres cloture")

    # 4. La cle RSA NE doit PAS avoir ete effacee : c'est de
    #    l'infrastructure, pas une donnee de consultation. Un effacement trop
    #    large invaliderait les liens deja distribues.
    p.persister_cle_rsa_chiffree("dept_eff", b"privee", b"publique", 1.0)
    p.effacer_etat_consultation()
    if p.charger_cle_rsa_chiffree("dept_eff") is None:
        print("FAIL 3. la cloture a efface la cle RSA (trop large)")
        ok = False
    else:
        print("OK   3. cle RSA preservee (effacement cible, pas aveugle)")

    print("-" * 55)
    print("EFFACEMENT DE CLOTURE : valide." if ok else "ECHEC : effacement incomplet ou trop large.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
