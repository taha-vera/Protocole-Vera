#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_lecture_ne_publie_pas.py -- Porte 20 : le GET des resultats ne publie pas.

CE QUE CE TEST PROTEGE
Consulter le tableau de bord ne doit RIEN publier. La publication est un acte
delibere (POST /api/rh/publier), jamais un effet de bord d'une lecture.

Le comportement dangereux, corrige le 31/07 : GET /api/rh/resultats publiait
et figeait le resultat. Consequence sur un departement de 1000 invites -- le
240e vote arrive, le RH consulte son suivi, le resultat est fige sur 240
reponses, et les votes 241 a 1000 sont enregistres en base mais ne seront
JAMAIS publies. Aucun ecran ne signalait l'ecart.

Aggravation anonymat : le resultat fige correspondait aux 240 PREMIERS votants,
sous-ensemble que le RH peut enumerer en surveillant le compteur pendant qu'il
relance les gens. L'ensemble d'anonymat n'etait plus le departement mais une
cohorte identifiable.

Aggravation securite : etant un GET mutant avec un cookie SameSite=Lax, il
etait declenchable par simple navigation cross-site.

Ce test exerce la logique de publication au niveau du module, sans serveur
HTTP : il verifie l'invariant lui-meme (le budget epsilon ne bouge pas a la
lecture), qui est ce qui compte. Un test HTTP complementaire existe en
JavaScript dans chantier_crypto/.
"""

import sys

from vera_epsilon_budget import BudgetEpsilonParDepartement


class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test Porte 20 -- la lecture ne consomme pas de budget")
    print("-" * 55)
    ok = True

    DEPT = "Grand Groupe"
    COUT = 0.5

    # 1. Consulter l'etat du budget ne le consomme pas.
    #    C'est l'operation que faisait le GET : lire pour afficher. Si `etat()`
    #    mutait, toute consultation du tableau de bord epuiserait le budget.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=COUT)
        for i in range(5):
            etat = b.etat(DEPT)
            if etat["nombre_publications"] != 0:
                raise Echec(f"lecture {i+1} : nombre_publications = "
                            f"{etat['nombre_publications']} au lieu de 0")
            if etat["epsilon_consomme"] != 0:
                raise Echec(f"lecture {i+1} : epsilon consomme a la LECTURE")
        _ok("1. cinq lectures de l'etat : aucune consommation")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. Interroger la possibilite de publier ne publie pas.
    #    peut_publier() est appele par le GET pour afficher « publiable ».
    #    S'il consommait, afficher l'ecran suffirait a epuiser le budget.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=COUT)
        for _ in range(5):
            if not b.peut_publier(DEPT, COUT):
                raise Echec("peut_publier devient faux sans publication reelle")
        if b.etat(DEPT)["nombre_publications"] != 0:
            raise Echec("peut_publier a consomme du budget")
        _ok("2. cinq appels a peut_publier : aucune consommation")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. Calculer l'etat futur ne mute pas l'etat courant.
    #    etat_apres_consommation sert a preparer l'ecriture atomique AVANT le
    #    commit. S'il mutait la memoire, une panne d'ecriture laisserait le
    #    budget en avance sur la base : departement vu comme publie alors que
    #    le resultat fige est absent, donc verrouille a jamais.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=COUT)
        futur = b.etat_apres_consommation(DEPT, COUT)
        if futur["nombre_publications"] != 1:
            raise Echec("l'etat FUTUR calcule est incorrect")
        courant = b.etat(DEPT)
        if courant["nombre_publications"] != 0:
            raise Echec(
                "etat_apres_consommation a MUTE l'etat courant : une panne "
                "d'ecriture verrouillerait le departement definitivement"
            )
        _ok("3. le calcul de l'etat futur ne mute pas l'etat courant")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. La publication, elle, consomme bien -- une seule fois.
    #    Garde-fou : sans ce test, un budget qui ne consommerait JAMAIS ferait
    #    passer les trois premiers pour de mauvaises raisons.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=COUT)
        b.consommer(DEPT, COUT)
        etat = b.etat(DEPT)
        if etat["nombre_publications"] != 1:
            raise Echec("la publication n'a pas ete comptee")
        if abs(etat["epsilon_consomme"] - COUT) > 1e-9:
            raise Echec(f"epsilon consomme = {etat['epsilon_consomme']}, attendu {COUT}")
        if b.peut_publier(DEPT, COUT):
            raise Echec("une SECONDE publication reste autorisee apres epuisement")
        _ok("4. la publication consomme, et une seule fois")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. Le cloisonnement par departement tient.
    #    Publier pour l'un ne doit pas entamer le budget de l'autre.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=COUT)
        b.consommer("Dept A", COUT)
        if not b.peut_publier("Dept B", COUT):
            raise Echec("publier pour A a consomme le budget de B")
        _ok("5. les budgets restent cloisonnes par departement")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("LECTURE SEULE : consulter n'engage rien, publier est un acte delibere.")
        return 0
    print("ECHEC : la lecture consomme du budget -- des votes seraient perdus.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
