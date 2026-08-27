#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porte 2 : l'inference d'appartenance reste sous la borne epsilon-DP.

POURQUOI CE TEST EXISTE

`VERA_THREAT_MODEL_COMPLETE.md` classe la Porte 2 « Fermee », avec des chiffres
precis : « AUC = 0.6209, IC95 % [0.6185, 0.6232], borne theorique 0.6225
incluse (N=100 000, bootstrap) ». Le bilan la range parmi les portes fermees
« avec preuve reproductible sur la production ».

Aucun fichier du depot ne produisait ces chiffres. Constat d'un audit externe le
27/08/2026 : `validation_opendp.py` calcule bien une AUC ANALYTIQUE de pire cas
(0.621311), mais ce n'est ni la meme valeur, ni la meme nature -- une borne
theorique, pas une mesure -- et elle n'est assortie d'aucun intervalle de
confiance.

C'est le meme motif que la Porte 3 la veille : une porte declaree fermee sur la
foi d'une mesure que personne ne peut rejouer. La difference est qu'ici la
preuve n'existait nulle part, pas meme hors du depot.

CE QUE MESURE CE TEST

L'attaque d'appartenance dans son scenario le plus favorable a l'adversaire :
il connait toutes les autres reponses, il sait que la personne visee a repondu
« oui » ou n'a pas repondu, et il observe le comptage bruite. C'est le
Neyman-Pearson optimal -- aucune attaque reelle ne fait mieux.

L'AUC est mesuree empiriquement sur la calibration REELLE, lue depuis
`vera_dp_noise` et non recopiee. L'intervalle de confiance est obtenu par
bootstrap. Deux assertions :

1. L'AUC mesuree reste sous la borne `e^eps / (1 + e^eps)`. C'est la propriete
   que la Porte 2 revendique.
2. La borne analytique de pire cas est elle-meme sous cette borne, et l'AUC
   mesuree ne la depasse pas significativement -- sans quoi la mesure et la
   theorie decriraient deux mecanismes differents.

CE QUE CE TEST NE PROUVE PAS

Une AUC de 0,62 n'est pas « presque le hasard ». Elle signifie qu'un adversaire
omniscient sur tout le reste devine juste 62 fois sur 100 la ou le hasard en
donne 50. C'est la garantie epsilon = 0,5, pas davantage -- et elle ne porte que
sur les SORTIES PUBLIEES. Les canaux temporels de LIMITS.md section 9 ne sont
pas couverts, et aucune valeur d'epsilon ne les fermerait.
"""

import math
import pathlib
import random
import statistics
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# Calibration LUE, jamais recopiee : un test qui redeclare les parametres
# mesure autre chose que la production (constat du 27/08, cf. LIMITS section 6).
from vera_dp_noise import DELTA_INT, SCALE  # noqa: E402

EPSILON = DELTA_INT / SCALE
BORNE = math.exp(EPSILON) / (1 + math.exp(EPSILON))

# L'ENGAGEMENT, ecrit ici volontairement.
#
# Ailleurs dans le depot, recopier une valeur est proscrit -- elle derive. Ici
# c'est l'inverse : 0,5 est ce que VERA PROMET a ses participants, dans le
# README, dans LIMITS.md et sur /api/engagement_cles. Le role de ce test est de
# confronter le code a cette promesse. La constante doit donc etre independante
# du code testee, sinon le test certifie n'importe quelle calibration.
#
# Constate en ecrivant ce test : sans cette assertion, diviser SCALE par deux
# porte epsilon a 1,0 et le test passait toujours -- il recalculait la borne
# depuis la calibration degradee et concluait a la conformite. Une garde qui
# s'adapte au defaut ne garde rien.
EPSILON_PROMIS = 0.5

N_TIRAGES = 100_000        # comme annonce dans le modele de menace
N_BOOTSTRAP = 400
GRAINE = 20260827

echecs = []


def _ok(message):
    print(f"  OK  {message}")


class Echec(Exception):
    pass


def laplace_discret(alea, echelle):
    """Laplace discret de parametre `echelle`, par difference de geometriques.

    La production tire via OpenDP ; on reproduit ici la meme loi sans dependre
    de son API interne. La propriete testee porte sur la LOI, pas sur
    l'implementation du tirage -- laquelle est validee par
    validation_opendp.py, qui interroge OpenDP directement.
    """
    p = 1 - math.exp(-1 / echelle)
    g1 = int(math.floor(math.log(1 - alea.random()) / math.log(1 - p)))
    g2 = int(math.floor(math.log(1 - alea.random()) / math.log(1 - p)))
    return g1 - g2


def auc_depuis_scores(scores_membres, scores_non_membres):
    """AUC par la statistique de Mann-Whitney, egalites comptees 1/2.

    Definition equivalente : probabilite qu'un membre tire au hasard recoive un
    score superieur a un non-membre tire au hasard.
    """
    tous = sorted(scores_membres + scores_non_membres)
    rangs = {}
    i = 0
    while i < len(tous):
        j = i
        while j + 1 < len(tous) and tous[j + 1] == tous[i]:
            j += 1
        rang_moyen = (i + j) / 2 + 1
        rangs[tous[i]] = rang_moyen
        i = j + 1
    somme = sum(rangs[s] for s in scores_membres)
    n1, n2 = len(scores_membres), len(scores_non_membres)
    return (somme - n1 * (n1 + 1) / 2) / (n1 * n2)


# --- Mesure ---------------------------------------------------------------
#
# Le score de l'adversaire est le comptage bruite lui-meme : sous Laplace, le
# rapport de vraisemblance entre « a repondu » et « n'a pas repondu » est
# monotone en cette valeur. Le classement par score EST donc l'attaque
# optimale, et l'AUC obtenue est celle de Neyman-Pearson.

alea = random.Random(GRAINE)
membres = [DELTA_INT + laplace_discret(alea, SCALE) for _ in range(N_TIRAGES)]
non_membres = [laplace_discret(alea, SCALE) for _ in range(N_TIRAGES)]

auc = auc_depuis_scores(membres, non_membres)

# Bootstrap : reechantillonnage avec remise des deux populations.
aucs = []
for _ in range(N_BOOTSTRAP):
    m = [membres[alea.randrange(N_TIRAGES)] for _ in range(N_TIRAGES)]
    n = [non_membres[alea.randrange(N_TIRAGES)] for _ in range(N_TIRAGES)]
    aucs.append(auc_depuis_scores(m, n))
aucs.sort()
ic_bas = aucs[int(0.025 * N_BOOTSTRAP)]
ic_haut = aucs[int(0.975 * N_BOOTSTRAP) - 1]

# --- Borne analytique, recalculee ici pour comparaison --------------------

c = (math.exp(1 / SCALE) - 1) / (math.exp(1 / SCALE) + 1)
pmf = lambda x: c * math.exp(-abs(x) / SCALE)
K = int(60 * SCALE)
cdf_n = 0.0
auc_analytique = 0.0
for x in range(-K, K + 1):
    auc_analytique += pmf(x - DELTA_INT) * (cdf_n + 0.5 * pmf(x))
    cdf_n += pmf(x)

print(f"Porte 2 -- inference d'appartenance (epsilon = {EPSILON})")
print(f"  AUC mesuree      = {auc:.4f}  IC95% [{ic_bas:.4f}, {ic_haut:.4f}]")
print(f"  AUC analytique   = {auc_analytique:.6f}  (Neyman-Pearson, pire cas)")
print(f"  Borne eps-DP     = {BORNE:.6f}  (e^eps / (1 + e^eps))")

try:
    if abs(EPSILON - EPSILON_PROMIS) > 1e-9:
        raise Echec(
            f"la calibration donne epsilon = {EPSILON} (DELTA_INT="
            f"{DELTA_INT} / SCALE={SCALE}), alors que VERA promet "
            f"{EPSILON_PROMIS} a ses participants.\n"
            "    Ce n'est pas une divergence de documentation : c'est la "
            "garantie annoncee qui n'est plus celle appliquee.")
    _ok(f"0. Calibration conforme a l'engagement : epsilon = {EPSILON}")

    if auc > BORNE:
        raise Echec(
            f"AUC mesuree {auc:.4f} au-dessus de la borne {BORNE:.4f} : "
            "l'inference d'appartenance depasse ce que epsilon garantit.")
    _ok(f"1. AUC mesuree {auc:.4f} sous la borne {BORNE:.4f}")

    if auc_analytique > BORNE + 1e-9:
        raise Echec(
            f"la borne analytique {auc_analytique:.6f} depasse la borne "
            f"epsilon-DP {BORNE:.6f} : la calibration est incoherente.")
    _ok(f"2. Borne analytique {auc_analytique:.6f} sous la borne eps-DP")

    # La mesure et la theorie doivent decrire le meme mecanisme. Un ecart
    # au-dela de l'intervalle de confiance signifierait que le test mesure
    # autre chose que ce que la borne calcule.
    if not (ic_bas - 0.005 <= auc_analytique <= ic_haut + 0.005):
        raise Echec(
            f"la borne analytique {auc_analytique:.6f} tombe hors de "
            f"l'intervalle mesure [{ic_bas:.4f}, {ic_haut:.4f}] : mesure et "
            "theorie ne portent pas sur le meme mecanisme.")
    _ok("3. Mesure et borne analytique concordent")

except Echec as e:
    print(f"\nECHEC : {e}")
    print("\nLa Porte 2 est declaree fermee dans "
          "VERA_THREAT_MODEL_COMPLETE.md.\nSi cet echec se reproduit, c'est la "
          "declaration qui est fausse.")
    sys.exit(1)

print(f"\nOK : Porte 2 -- AUC {auc:.4f} "
      f"[{ic_bas:.4f}, {ic_haut:.4f}], sous la borne {BORNE:.4f}.")
sys.exit(0)
