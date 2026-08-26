#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test des validations ajoutees : cout epsilon <= 0 refuse + accumulation."""
import sys
from vera_epsilon_budget import BudgetEpsilonParDepartement, BudgetEpuiseError

class Echec(Exception): pass
def _ok(n): print(f"OK   {n}")

def main():
    print("Test validations budget epsilon (cout <= 0, accumulation)")
    print("-" * 55)
    ok = True

    # 1. Cout negatif refuse (consommer).
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        try:
            b.consommer("A", -1.0)
            raise Echec("cout negatif aurait du lever ValueError")
        except ValueError:
            _ok("1. consommer(cout negatif) -> ValueError")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Cout zero refuse (consommer).
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        try:
            b.consommer("A", 0.0)
            raise Echec("cout nul aurait du lever ValueError")
        except ValueError:
            _ok("2. consommer(cout nul) -> ValueError")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. peut_publier refuse cout <= 0.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        if b.peut_publier("A", 0.0) or b.peut_publier("A", -1.0):
            raise Echec("peut_publier devrait refuser un cout <= 0")
        _ok("3. peut_publier(cout <= 0) -> False")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. ACCUMULATION : deux consommations partielles s'additionnent.
    #    (Detecte un bug '=' au lieu de '+=' : le point que Fable 5 a souleve.)
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer("A", 0.2)
        b.consommer("A", 0.2)
        etat = b.etat("A")
        if abs(etat["epsilon_consomme"] - 0.4) > 1e-9:
            raise Echec(f"accumulation cassee: consomme={etat['epsilon_consomme']} (attendu 0.4)")
        # il reste 0.1, donc 0.2 doit etre refuse
        if b.peut_publier("A", 0.2):
            raise Echec("0.2 devrait etre refuse avec seulement 0.1 restant")
        _ok("4. accumulation correcte (0.2+0.2=0.4, 0.2 ensuite refuse)")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. Fonctionnement normal preserve (non-regression).
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        if not b.peut_publier("A", 0.5):
            raise Echec("une publication valide a 0.5 devrait rester autorisee")
        b.consommer("A", 0.5)
        if b.peut_publier("A", 0.5):
            raise Echec("apres 0.5 consomme, republier devrait etre refuse")
        _ok("5. non-regression: publication normale a 0.5 toujours OK")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    print("-" * 55)
    if ok:
        print("Validations budget OK : cout <= 0 refuse, accumulation correcte.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
