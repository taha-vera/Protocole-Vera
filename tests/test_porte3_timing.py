#!/usr/bin/env python3
"""Porte 3 : le temps de calcul du bruit ne doit pas dependre de la valeur.

POURQUOI CE TEST EXISTE

`VERA_THREAT_MODEL_COMPLETE.md` declare la Porte 3 « Fermee », avec des chiffres
precis : Spearman rho = -0,14, p = 0,76. Le README annonce de son cote « 15
fermees avec preuve reproductible ».

La preuve n'etait pas reproductible. Elle vivait dans `/root/test_porte3_timing.py`,
hors du depot, datee du 02/07/2026, et dependait de `scipy` -- absent de
`requirements.txt`. Un tiers voulant verifier ce rho ne pouvait pas : le fichier
n'existait que sur le serveur de l'operateur. Constat du 26/08/2026, meme motif
que `/root/vera_test` decouvert trois jours plus tot.

Ce test reprend la mesure SANS dependance externe : Spearman et Mann-Whitney
tiennent en quelques dizaines de lignes de Python standard. Le prix d'une
dependance lourde pour un seul test etait plus eleve que celui de les ecrire.

CE QUE LA PORTE PROTEGE

`appliquer_bruit_dp()` borne la valeur puis y ajoute un bruit de Laplace. Si sa
duree d'execution correlait avec la valeur d'entree, un observateur capable de
chronometrer le serveur en deduirait des compteurs -- donc contournerait le
bruit par le bas, exactement comme les canaux temporels de la section 9 de
LIMITS.md contournent la publication bruitee.

CE QUE CE TEST NE PROUVE PAS

Une absence de correlation mesuree n'est pas une preuve d'independance. Le test
etablit qu'aucune fuite n'est visible a cette resolution et sur cet
echantillon ; il ne dit rien d'un adversaire disposant d'un acces local et d'un
compteur de cycles. Le modele de menace note d'ailleurs que la fuite eventuelle
est sub-microseconde, donc noyee dans une latence reseau de 50 a 100 ms.

C'est aussi pourquoi un echec ici doit etre lu avec prudence : une machine
chargee produit des correlations fantomes. Le test le dit dans son message.
"""

import math
import pathlib
import random
import statistics
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from vera_dp_noise import appliquer_bruit_dp  # noqa: E402

# Sept valeurs : les deux extremes de BOUNDS et cinq intermediaires. La
# methodologie du 30/06 est conservee pour que les deux mesures restent
# comparables.
VALEURS = [0, 1, 100, 10_000, 1_000_000, 9_999_999, 10_000_000]
REPETITIONS = 3000
SEUIL_P = 0.01           # on n'alerte que sur une correlation tres marquee
SEUIL_RHO = 0.30         # et d'amplitude non negligeable

# SEUIL D'EXPLOITABILITE, et c'est le parametre qui compte.
#
# Sur 400 echantillons, Mann-Whitney declare significatif un ecart median de
# DEUX nanosecondes. Statistiquement, c'est vrai. Pratiquement, cela ne veut
# rien dire : la latence reseau qui separe l'adversaire du serveur est de 50 a
# 100 millisecondes, soit sept ordres de grandeur au-dessus. Un test qui
# echouerait sur deux nanosecondes se declencherait a chaque execution et
# apprendrait a son lecteur a l'ignorer -- le defaut exact de l'empreinte
# perimee du 22/08.
#
# On exige donc les DEUX : une difference statistiquement etablie ET une
# amplitude qui puisse survivre au reseau. Un micro-seconde reste tres
# conservateur -- le modele de menace note que la fuite eventuelle est
# sub-microseconde et deja inexploitable.
ECART_EXPLOITABLE_NS = 1_000

echecs = []


def rangs(valeurs):
    """Rangs moyens, egalites comprises -- indispensable sur des durees."""
    indices = sorted(range(len(valeurs)), key=lambda i: valeurs[i])
    r = [0.0] * len(valeurs)
    i = 0
    while i < len(indices):
        j = i
        while j + 1 < len(indices) and \
                valeurs[indices[j + 1]] == valeurs[indices[i]]:
            j += 1
        rang_moyen = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[indices[k]] = rang_moyen
        i = j + 1
    return r


def spearman(x, y):
    """Coefficient de Spearman : Pearson sur les rangs."""
    rx, ry = rangs(x), rangs(y)
    n = len(x)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return 0.0 if dx == 0 or dy == 0 else num / (dx * dy)


def p_spearman(rho, n):
    """p bilaterale par approximation de Student, valable des n >= 6.

    Sur sept points, cette approximation est grossiere -- c'est assume : elle
    sert a distinguer « rien de visible » de « quelque chose d'enorme », pas a
    publier un resultat statistique.
    """
    if n < 3 or abs(rho) >= 1.0:
        return 0.0
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    # Approximation normale de la loi de Student, suffisante ici.
    z = abs(t) / math.sqrt(1 + t * t / (2 * (n - 2)))
    return math.erfc(z / math.sqrt(2))


def mann_whitney_u(a, b):
    """Statistique U et p normale approchee, egalites traitees par rangs."""
    combine = list(a) + list(b)
    r = rangs(combine)
    somme_a = sum(r[:len(a)])
    n1, n2 = len(a), len(b)
    u1 = somme_a - n1 * (n1 + 1) / 2
    u = min(u1, n1 * n2 - u1)
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma == 0:
        return u, 1.0
    z = (u - mu) / sigma
    return u, math.erfc(abs(z) / math.sqrt(2))


def mesurer(valeur, repetitions=REPETITIONS):
    """Duree mediane d'appel, en nanosecondes.

    La mediane plutot que la moyenne : une seule interruption de
    l'ordonnanceur suffirait a deplacer une moyenne de plusieurs
    microsecondes.
    """
    durees = []
    for _ in range(repetitions):
        debut = time.perf_counter_ns()
        appliquer_bruit_dp(valeur)
        durees.append(time.perf_counter_ns() - debut)
    return statistics.median(durees)


# --- Mesure, en ordre aleatoire ------------------------------------------
#
# L'ordre est melange a chaque execution : mesurer les valeurs dans l'ordre
# croissant ferait correler la duree avec le rechauffement du cache et
# produirait une fausse alerte.

ordre = VALEURS[:]
random.shuffle(ordre)
medianes = {v: mesurer(v) for v in ordre}

x = VALEURS
y = [medianes[v] for v in VALEURS]

rho = spearman(x, y)
p = p_spearman(rho, len(x))

if abs(rho) > SEUIL_RHO and p < SEUIL_P:
    echecs.append(
        f"la duree de calcul correle avec la valeur d'entree : "
        f"rho = {rho:+.3f}, p = {p:.3f}.\n"
        "    Un observateur capable de chronometrer le serveur pourrait en "
        "deduire des compteurs.\n"
        "    A verifier sur une machine au repos avant de conclure : une "
        "machine chargee produit des correlations fantomes.")

# --- Extremes compares deux a deux ---------------------------------------
#
# Spearman sur sept points est peu puissant. On compare aussi les
# distributions completes aux deux bornes, ou l'ecart serait maximal s'il
# existait.

bas = [mesurer(VALEURS[0], 1) for _ in range(400)]
haut = [mesurer(VALEURS[-1], 1) for _ in range(400)]
u, p_u = mann_whitney_u(bas, haut)

med_bas, med_haut = statistics.median(bas), statistics.median(haut)
ecart = abs(med_haut - med_bas)

if p_u < SEUIL_P and ecart > ECART_EXPLOITABLE_NS:
    echecs.append(
        f"les durees aux deux bornes de BOUNDS different : U = {u:.0f}, "
        f"p = {p_u:.4f}, ecart median {ecart:.0f} ns.\n"
        f"    mediane a {VALEURS[0]} : {med_bas:.0f} ns ; "
        f"a {VALEURS[-1]} : {med_haut:.0f} ns.\n"
        "    Rejouer sur une machine au repos : cet ecart peut venir de "
        "l'ordonnanceur.")

# --- Verdict --------------------------------------------------------------

if echecs:
    print("ECHEC : Porte 3 -- un canal temporel de calcul est visible.\n")
    for e in echecs:
        print("  - " + e)
    print("\nLa Porte 3 est declaree fermee dans "
          "VERA_THREAT_MODEL_COMPLETE.md.\nSi cet echec se reproduit sur une "
          "machine au repos, c'est la declaration qui est fausse.")
    sys.exit(1)

print(f"OK : Porte 3 -- aucun canal temporel exploitable "
      f"(Spearman rho = {rho:+.3f}, p = {p:.3f} ; "
      f"ecart median aux bornes {ecart:.0f} ns, seuil "
      f"{ECART_EXPLOITABLE_NS} ns).")
sys.exit(0)
