#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_porte8_outlier.py -- Porte 8 : resistance a l'inference outlier.

Reecrit le 25/07/2026. Les deux fichiers test_porte8_* precedents n'etaient
pas des tests : zero assertion, zero code de sortie, ils imprimaient un tableau
et sortaient 0 quoi qu'il arrive. Ils reimplementaient Laplace a la main avec
DELTA_INT = 10 (scale 20) alors que la production est a DELTA_INT = 2,
SCALE = 4.0. Le rapport Delta/scale etant identique (0.5), les chiffres
produits restaient valables -- verifie le 25/07, TPR@1%FPR = 1.67% avec la
calibration reelle, contre 1.6% documente -- mais c'etait une coincidence, pas
une garantie : une modification de SCALE seul aurait rendu ces scripts muets.

Ce test verifie la propriete sur la calibration REELLE, lue depuis
vera_dp_noise, et ASSERTE. Un adversaire qui observe un comptage bruite et
cherche a savoir si un individu donne a repondu obtient un TPR marginal a bas
FPR : c'est ce que la Porte 8 revendique.
"""

import sys
import math
import random
import statistics

import vera_dp_noise as dpn


class Echec(Exception):
    pass


def _ok(msg):
    print("OK   " + msg)


def _tirage_laplace(scale, n, rng):
    """Laplace de parametre scale, tire par le RNG fourni."""
    out = []
    for _ in range(n):
        u = rng.random() - 0.5
        out.append(-scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u)))
    return out


def main():
    print("Test Porte 8 : inference outlier (calibration de production)")
    print("-" * 60)
    ok = True

    # Calibration LUE depuis la production, pas recopiee. Si SCALE ou
    # DELTA_INT changent, ce test suit -- il ne peut plus decrire un autre
    # systeme que celui deploye.
    delta = dpn.DELTA_INT
    scale = dpn.SCALE
    print(f"     calibration lue : DELTA_INT={delta}, SCALE={scale}")

    try:
        if scale <= 0 or delta <= 0:
            raise Echec("calibration invalide")
        _ok("1. calibration de production lue depuis vera_dp_noise")
    except Echec as e:
        print("FAIL 1. " + str(e)); ok = False
        return 1

    # Scenario : un individu a repondu (comptage reel + delta) ou non
    # (comptage reel). L'adversaire observe la valeur bruitee et doit trancher.
    N = 200000
    rng = random.Random(20260725)
    absent = sorted(_tirage_laplace(scale, N, rng))
    present = sorted(d + delta for d in _tirage_laplace(scale, N, rng))

    def tpr_at(fpr):
        seuil = absent[int((1 - fpr) * len(absent))]
        return sum(1 for v in present if v >= seuil) / len(present)

    t10, t1, t01 = tpr_at(0.10), tpr_at(0.01), tpr_at(0.001)
    print(f"     TPR@10%FPR={t10:.4f}  TPR@1%FPR={t1:.4f}  TPR@0.1%FPR={t01:.4f}")

    # 2. A 1% de faux positifs, l'attaque doit rester marginale. Le seuil de 3%
    #    laisse une marge large devant la valeur attendue (~1.7%) : le test ne
    #    doit pas clignoter au gre du tirage, seulement attraper une degradation
    #    reelle de la calibration.
    try:
        if t1 > 0.03:
            raise Echec(f"TPR@1%FPR = {t1:.4f} > 3% -- protection degradee")
        _ok(f"2. TPR@1%FPR = {t1:.4f} reste marginal (seuil 3%)")
    except Echec as e:
        print("FAIL 2. " + str(e)); ok = False

    # 3. L'avantage doit croitre de facon monotone avec le FPR tolere.
    #    Une inversion signalerait une erreur de mesure ou de mecanisme.
    try:
        if not (t01 <= t1 <= t10):
            raise Echec(f"TPR non monotone : {t01:.4f}, {t1:.4f}, {t10:.4f}")
        _ok("3. TPR croissant avec le FPR tolere (mesure coherente)")
    except Echec as e:
        print("FAIL 3. " + str(e)); ok = False

    # 4. Garde-fou anti-regression : si quelqu'un augmente SCALE sans toucher
    #    DELTA_INT, le rapport change et la protection aussi. On verifie que le
    #    rapport reste celui qui fonde les chiffres publies (Delta/scale = eps).
    try:
        eps_effectif = delta / scale
        if abs(eps_effectif - 0.5) > 1e-9:
            raise Echec(
                f"DELTA_INT/SCALE = {eps_effectif} au lieu de 0.5 -- les chiffres "
                "publies dans README et threat model ne decrivent plus le systeme")
        _ok("4. DELTA_INT/SCALE = 0.5, conforme a epsilon documente")
    except Echec as e:
        print("FAIL 4. " + str(e)); ok = False

    print("-" * 60)
    print("PORTE 8 : inference outlier marginale." if ok else "ECHEC : protection degradee.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
