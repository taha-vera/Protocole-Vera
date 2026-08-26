#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_precision_kmin.py -- Verifie que la table de precision du README/AUDIT
est reproductible, ET que l'invariant structurel de la projection tient
(somme == n, valeurs >= 0, entiers), y compris sur le cas extreme ou le
clipping+redistribution est reellement exerce.

OpenDP tire son bruit d'un CSPRNG interne NON seedable : ce test est
STOCHASTIQUE (mesure une distribution). Ce n'est pas une preuve DP
(voir validation_opendp.py) ; c'est un garde-fou empirique.

Les invariants sont verifies par 'if ... raise', PAS par 'assert' : assert
est neutralise par 'python -O', ce qui ferait disparaitre le garde-fou en
execution optimisee.
"""

import sys
import numpy as np
from vera_dp_noise import publier_histogramme_dp

TABLE_ATTENDUE = [
    (100, 12.0, 1.5),
    (150,  8.0, 1.5),
    (200,  6.0, 1.0),
    (240,  5.0, 0.8),
    (300,  4.0, 0.8),
    (500,  2.4, 0.6),
]

N_SIM = 3000


class InvariantCasse(Exception):
    pass


def _verifier_invariant(pub, n):
    """somme==n, toutes valeurs entieres >= 0. Leve si viole (pas d'assert)."""
    if sum(pub.values()) != n:
        raise InvariantCasse(f"somme={sum(pub.values())} != {n}")
    for k, v in pub.items():
        if not isinstance(v, int):
            raise InvariantCasse(f"valeur non entiere: {k}={v!r}")
        if v < 0:
            raise InvariantCasse(f"valeur negative: {k}={v}")


def _repartition_equilibree(n):
    a = round(n * 0.34)
    b = round(n * 0.33)
    c = n - a - b
    return {'oui': a, 'non': b, 'abstention': c}


def mesurer(n, repartition=None):
    vrai = repartition if repartition is not None else _repartition_equilibree(n)
    if sum(vrai.values()) != n:
        raise InvariantCasse(f"baseline incoherente: somme={sum(vrai.values())} != {n}")
    errs = []
    for _ in range(N_SIM):
        pub = publier_histogramme_dp(vrai, n)
        _verifier_invariant(pub, n)
        errs.append(max(abs(pub[k]-vrai[k]) for k in vrai))
    return 100 * np.percentile(np.array(errs), 95) / n


def test_cas_extreme_clipping():
    """Repartition {n,0,0} : les cases a 0 partent en negatif ~50% du temps,
    ce qui exerce reellement le clipping+redistribution de la projection.
    On ne verifie ici que l'invariant (pas la precision, non pertinente ici)."""
    n = 300
    vrai = {'oui': n, 'non': 0, 'abstention': 0}
    for _ in range(N_SIM):
        pub = publier_histogramme_dp(vrai, n)
        _verifier_invariant(pub, n)  # leve si la branche clipping casse l'invariant
    return True


def main():
    print(f"Test de precision VERA (K_MIN=240, eps=0.5, {N_SIM} simulations)")
    print("Invariant verifie a chaque tirage : somme==n, entiers, >= 0.")
    print(f"{'n':>5} {'attendu':>9} {'mesure':>9} {'verdict':>10}")
    print("-" * 38)
    ok = True
    for n, attendu, tol in TABLE_ATTENDUE:
        mesure = mesurer(n)
        passe = abs(mesure - attendu) <= tol
        ok = ok and passe
        print(f"{n:>5} {attendu:>8.1f}% {mesure:>8.1f}% {'PASS' if passe else 'FAIL':>10}")

    print("-" * 38)
    # Cas extreme : exerce le clipping. Ne mesure pas la precision, seulement
    # que l'invariant tient quand le bruit force des valeurs negatives.
    try:
        test_cas_extreme_clipping()
        print("Cas extreme {n,0,0} (clipping exerce) : invariant OK")
    except InvariantCasse as e:
        print(f"Cas extreme {{n,0,0}} : INVARIANT CASSE -> {e}")
        ok = False

    err_seuil = mesurer(240)
    promesse_ok = err_seuil <= 5.3
    print(f"Promesse a K_MIN=240 : erreur {err_seuil:.1f}% (doit rester <= 5.3%) ? {'OUI' if promesse_ok else 'NON'}")

    if ok and promesse_ok:
        print("\nTOUS LES TESTS PASSENT -- table reproductible + invariant (somme/entiers/positifs) verifie, clipping inclus.")
        sys.exit(0)
    else:
        print("\nECHEC -- doc non reproduite ou invariant casse. A corriger.")
        sys.exit(1)


if __name__ == "__main__":
    main()
