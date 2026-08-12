#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_non_regression_correctifs.py -- filet sur les correctifs des 23-25/07.

Constat de l'audit du 25/07 : les correctifs deployes ces jours-la n'etaient
proteges par AUCUN test. _expirer_cle, budget_epsilon.reset(),
etat_apres_consommation, _verifier_worker_unique et les deux migrations
pouvaient etre annules sans qu'aucun signal ne se declenche. Deux jours a
fermer des portes, et rien pour empecher qu'elles se rouvrent.

Ce fichier ne remplace pas des tests unitaires par invariant : c'est un filet
cible sur les regressions les plus couteuses, celles qui annulent une garantie
affichee.
"""

import os
import sys
import time
import hashlib

if "VERA_DB_PATH" not in os.environ:
    print("Ce test exige VERA_DB_PATH vers une base jetable.")
    sys.exit(1)

import vera_persistance as p
import vera_signature_manager as vsm
import vera_consultation_api  # noqa: F401  (charge la garde worker-unique)
from vera_epsilon_budget import BudgetEpsilonParDepartement


class Echec(Exception):
    pass


def _ok(msg):
    print("OK   " + msg)


def main():
    print("Non-regression : correctifs des 23-25/07")
    print("-" * 60)
    p.initialiser()
    ok = True

    # 1. EXPIRATION DE CLE (correctif 24/07). Le timer appelait seulement
    #    _detruire_cle_privee, qui zeroise la RAM : la cle chiffree survivait
    #    en base jusqu'au prochain redemarrage. La garantie "a expiration la
    #    cle est detruite" n'etait vraie qu'en memoire.
    try:
        duree_origine = vsm.DUREE_VIE_CLE_SECONDES
        vsm.DUREE_VIE_CLE_SECONDES = 2
        g = vsm.GestionnaireSignature()
        g.ouvrir_consultation()
        g.cle_publique("DeptExpire")
        if p.charger_cle_rsa_chiffree("DeptExpire") is None:
            raise Echec("la cle n'a pas ete persistee, test invalide")
        time.sleep(3)
        if p.charger_cle_rsa_chiffree("DeptExpire") is not None:
            raise Echec("la cle chiffree SURVIT en base apres expiration "
                        "-- le timer ne purge que la memoire")
        if g.consultation_active():
            raise Echec("la consultation est encore active apres expiration")
        _ok("1. expiration : cle purgee de la BASE, pas seulement de la RAM")
        vsm.DUREE_VIE_CLE_SECONDES = duree_origine
    except Echec as e:
        print("FAIL 1. " + str(e)); ok = False
        vsm.DUREE_VIE_CLE_SECONDES = duree_origine

    # 2. RESET DU BUDGET A LA CLOTURE (correctif 24/07). Sans reset, une
    #    nouvelle consultation reutilisant un nom de departement le voyait
    #    "deja publie", cherchait un resultat fige efface, et refusait de
    #    publier -- departement bloque jusqu'au redemarrage.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("DeptReuse", 0.5)
        if not hasattr(b, "reset"):
            raise Echec("la methode reset() a disparu du budget epsilon")
        b.reset()
        if b.etat("DeptReuse")["nombre_publications"] != 0:
            raise Echec("reset() ne remet pas nombre_publications a zero "
                        "-- un departement reutilise resterait bloque")
        if not b.peut_publier("DeptReuse", 0.5):
            raise Echec("apres reset, le departement ne peut toujours pas publier")
        _ok("2. reset du budget : un nom de departement est reutilisable")
    except Echec as e:
        print("FAIL 2. " + str(e)); ok = False

    # 3. ORDRE PERSISTER-PUIS-MUTER (correctif 24/07). etat_apres_consommation
    #    CALCULE l'etat futur sans muter, pour que la memoire ne prenne jamais
    #    d'avance sur la base en cas d'echec d'ecriture.
    try:
        b2 = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        if not hasattr(b2, "etat_apres_consommation"):
            raise Echec("etat_apres_consommation a disparu -- le calcul sans "
                        "mutation n'existe plus, la memoire peut devancer la base")
        avant = b2.etat("DeptOrdre")
        futur = b2.etat_apres_consommation("DeptOrdre", 0.5)
        apres = b2.etat("DeptOrdre")
        if avant != apres:
            raise Echec("etat_apres_consommation a MUTE l'etat -- ce n'est plus "
                        "un calcul, l'ordre persister-puis-muter est casse")
        if futur["nombre_publications"] != avant["nombre_publications"] + 1:
            raise Echec("le calcul de l'etat futur est faux")
        _ok("3. etat_apres_consommation calcule sans muter")
    except Echec as e:
        print("FAIL 3. " + str(e)); ok = False

    # 4. GARDE WORKER-UNIQUE (correctif 24/07). WEB_CONCURRENCY seul ne suffit
    #    pas : uvicorn --workers N ne pose pas cette variable, la garde ne se
    #    declenchait pas, et chaque worker avait son propre budget epsilon.
    try:
        src = open(os.path.join(os.path.dirname(vera_consultation_api.__file__),
                                "vera_consultation_api.py"), encoding="utf-8").read()
        if "sys.argv" not in src or "--workers" not in src:
            raise Echec("la garde worker-unique n'inspecte plus sys.argv "
                        "-- uvicorn --workers 2 redemarrerait silencieusement")
        _ok("4. garde worker-unique inspecte bien la ligne de commande")
    except Echec as e:
        print("FAIL 4. " + str(e)); ok = False

    # 5. MIGRATIONS SUR L'ANTI-REJEU (23-24/07). Elles manipulent
    #    tokens_consommes : une regression y viderait le registre anti-rejeu
    #    et rouvrirait le double-vote pour tout K deja utilise.
    try:
        emp = hashlib.sha384(b"K_de_non_regression").hexdigest()
        p.enregistrer_vote_atomique("DeptMigr", "oui", emp)
        avant_n = len(p.charger_tokens_consommes())
        p.initialiser()  # rejoue les migrations, doivent etre idempotentes
        apres_n = len(p.charger_tokens_consommes())
        if apres_n != avant_n:
            raise Echec(f"les migrations ont change le registre anti-rejeu "
                        f"({avant_n} -> {apres_n}) -- double-vote possible")
        schema = p._conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='tokens_consommes'").fetchone()[0]
        if "WITHOUT ROWID" not in schema.upper():
            raise Echec("tokens_consommes n'est plus WITHOUT ROWID "
                        "-- l'ordre d'insertion des votes redevient lisible")
        if "horodatage" in schema.lower():
            raise Echec("un horodatage est reapparu dans tokens_consommes")
        _ok("5. migrations idempotentes, schema anti-rejeu conforme")
    except Echec as e:
        print("FAIL 5. " + str(e)); ok = False

    print("-" * 60)
    print("NON-REGRESSION : correctifs proteges." if ok else "ECHEC : un correctif a ete annule.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
