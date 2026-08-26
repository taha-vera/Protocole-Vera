#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_accumulation_epsilon.py -- Porte 4 : le budget s'ACCUMULE.

CE QUE CE TEST PROTEGE
Les consommations partielles doivent s'additionner, pas s'ecraser. Si le
compteur ecrasait au lieu d'additionner, un appelant pourrait consommer 0.2
autant de fois qu'il veut sans jamais epuiser un budget de 0.5 -- l'epsilon
reel deviendrait illimite et la garantie de confidentialite differentielle
serait vide.

POURQUOI CE TEST MANQUAIT
Les tests existants consomment toujours le budget entier en un seul appel
(0.5 sur 0.5). Ils passeraient a l'identique avec un `=` a la place d'un `+=` :
ils verifient le refus au-dela du plafond, pas le mecanisme d'addition.

Le cas flottant est teste separement : 5 x 0.1 vaut 0.5000000000000001 en
arithmetique IEEE 754, pas 0.5. Une comparaison stricte refuserait a tort la
derniere consommation legitime, ou en autoriserait une de trop.

PERIMETRE. Ce test porte sur l'accumulation A L'INTERIEUR d'une consultation.
Entre deux consultations le budget est remis a zero a la cloture -- c'est une
limite structurelle documentee (LIMITS.md section 14), pas un defaut : suivre
l'exposition d'un individu supposerait de l'identifier.
"""

import sys

from vera_epsilon_budget import BudgetEpsilonParDepartement


class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test Porte 4 -- accumulation du budget epsilon")
    print("-" * 55)
    ok = True

    DEPT = "Service"

    # 1. Deux consommations partielles s'additionnent.
    #    LE TEST CENTRAL : avec un `=` au lieu d'un `+=`, le restant serait
    #    0.3 apres les deux appels au lieu de 0.1.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer(DEPT, 0.2)
        b.consommer(DEPT, 0.2)
        etat = b.etat(DEPT)
        if abs(etat["epsilon_consomme"] - 0.4) > 1e-9:
            raise Echec(
                f"epsilon consomme = {etat['epsilon_consomme']}, attendu 0.4. "
                "Les consommations s'ECRASENT au lieu de s'additionner : le "
                "budget serait contournable a l'infini."
            )
        if abs(etat["epsilon_restant"] - 0.1) > 1e-9:
            raise Echec(f"restant = {etat['epsilon_restant']}, attendu 0.1")
        _ok("1. deux consommations de 0.2 laissent bien 0.1")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. Une demande qui depasse le restant est refusee.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer(DEPT, 0.2)
        b.consommer(DEPT, 0.2)
        if b.peut_publier(DEPT, 0.2):
            raise Echec("0.2 autorise alors qu'il ne reste que 0.1")
        _ok("2. une demande superieure au restant est refusee")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. Ce qui tient exactement dans le restant est accepte.
    #    Garde-fou : un budget qui refuserait TOUT ferait passer le test 2
    #    pour une mauvaise raison.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        b.consommer(DEPT, 0.2)
        b.consommer(DEPT, 0.2)
        if not b.peut_publier(DEPT, 0.1):
            raise Echec("0.1 refuse alors qu'il reste exactement 0.1")
        _ok("3. ce qui tient exactement dans le restant est accepte")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. Cas flottant : 5 x 0.1 sur un budget de 0.5.
    #    En IEEE 754, la somme vaut 0.5000000000000001. Une comparaison sans
    #    tolerance refuserait la cinquieme consommation, pourtant legitime.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        for i in range(5):
            if not b.peut_publier(DEPT, 0.1):
                raise Echec(
                    f"consommation {i+1}/5 de 0.1 refusee sur un budget de 0.5 : "
                    "erreur d'arrondi flottant non toleree"
                )
            b.consommer(DEPT, 0.1)
        if b.peut_publier(DEPT, 0.1):
            raise Echec("une SIXIEME consommation reste autorisee")
        _ok("4. cinq consommations de 0.1 passent, la sixieme est refusee")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. Un cout nul ou negatif est refuse.
    #    Sans cette garde, consommer(dept, -1.0) CREDITERAIT du budget, et un
    #    cout de 0 autoriserait un nombre illimite de publications.
    try:
        b = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)
        for cout in (0, -1.0):
            try:
                b.consommer(DEPT, cout)
                raise Echec(f"un cout de {cout} a ete ACCEPTE")
            except (ValueError, Echec) as e:
                if isinstance(e, Echec):
                    raise
        etat = b.etat(DEPT)
        if etat["epsilon_consomme"] < 0:
            raise Echec("le budget a ete credite par un cout negatif")
        _ok("5. un cout nul ou negatif est refuse")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("BUDGET EPSILON : les consommations s'additionnent, le plafond tient.")
        return 0
    print("ECHEC : le budget epsilon ne s'accumule plus correctement.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
