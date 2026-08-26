#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_epsilon_budget.py -- Porte 4 : composition sequentielle.
Verifie que le budget epsilon empeche la republication d'une meme cohorte
et reste cloisonne par departement. Comble un trou de couverture : la classe
BudgetEpsilonParDepartement n'avait aucun test dedie.
"""

import sys
from vera_epsilon_budget import BudgetEpsilonParDepartement, BudgetEpuiseError


class Echec(Exception):
    pass

def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test Porte 4 -- budget epsilon par departement")
    print("-" * 55)
    ok = True

    # 1. Une seule publication possible a budget 0.5, cout 0.5.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        if not b.peut_publier("A", 0.5):
            raise Echec("1re publication a 0.5 devrait etre autorisee")
        b.consommer("A", 0.5)
        if b.peut_publier("A", 0.5):
            raise Echec("2e publication devrait etre refusee (budget epuise)")
        _ok("1. une seule publication a budget 0.5 (2e refusee)")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. consommer au-dela leve BudgetEpuiseError.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("A", 0.5)
        try:
            b.consommer("A", 0.5)
            raise Echec("la 2e consommation aurait du lever BudgetEpuiseError")
        except BudgetEpuiseError:
            _ok("2. depassement leve BudgetEpuiseError (refus dur)")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. Cloisonnement : deux departements sont independants.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("A", 0.5)
        if not b.peut_publier("B", 0.5):
            raise Echec("le departement B ne devrait pas etre affecte par A")
        b.consommer("B", 0.5)
        _ok("3. budget cloisonne par departement (A n'affecte pas B)")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. etat() refletе correctement consommation et nb de publications.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("A", 0.5)
        e = b.etat("A")
        if e["nombre_publications"] != 1:
            raise Echec(f"nombre_publications attendu 1, obtenu {e['nombre_publications']}")
        if abs(e["epsilon_consomme"] - 0.5) > 1e-9:
            raise Echec(f"epsilon_consomme attendu 0.5, obtenu {e['epsilon_consomme']}")
        if abs(e["epsilon_restant"]) > 1e-9:
            raise Echec(f"epsilon_restant attendu 0, obtenu {e['epsilon_restant']}")
        _ok("4. etat() coherent (consomme, restant, nb publications)")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. injecter_etat recharge sans rejouer ni refuser (Porte 14).
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.injecter_etat("A", 0.5, 1)  # comme un rechargement depuis la base
        e = b.etat("A")
        if e["nombre_publications"] != 1 or abs(e["epsilon_consomme"] - 0.5) > 1e-9:
            raise Echec("injecter_etat n'a pas restaure l'etat correctement")
        if b.peut_publier("A", 0.5):
            raise Echec("apres rechargement a 0.5, republier devrait etre refuse")
        _ok("5. injecter_etat restaure l'etat (rechargement Porte 14)")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    print("-" * 55)
    if ok:
        print("PORTE 4 : budget epsilon valide -- une publication figee par cohorte.")
        sys.exit(0)
    else:
        print("ECHEC -- la logique de budget ne se comporte pas comme attendu.")
        sys.exit(1)


if __name__ == "__main__":
    main()
