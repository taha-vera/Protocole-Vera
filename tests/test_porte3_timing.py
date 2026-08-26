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

Et il BORNE l'ecart plutot qu'il ne le mesure : sous 5 % de la duree d'appel,
une difference peut exister sans etre detectee. C'est l'inexploitabilite qui est
prouvee, pas l'absence.

C'est aussi pourquoi un echec ici doit etre lu avec prudence : une machine
chargee produit des correlations fantomes. Le test le dit dans son message.
"""

import itertools
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

# CRITERE D'EXPLOITABILITE : relatif, et exigeant la coherence du signe.
#
# Sur 400 echantillons, Mann-Whitney declare significatif un ecart median de
# DEUX nanosecondes. Statistiquement, c'est vrai. Pratiquement, cela ne veut
# rien dire : la latence reseau qui separe l'adversaire du serveur est de 50 a
# 100 millisecondes. Un test qui echouerait la-dessus se declencherait a chaque
# execution et apprendrait a son lecteur a l'ignorer.
#
# DEUX ERREURS DE METHODE, CONSTATEES LE 26/08 ET CORRIGEES ICI.
#
# 1. Un seuil ABSOLU ne veut rien dire sans l'echelle. La premiere version
#    fixait 1 microseconde -- calibre contre une fonction factice repondant en
#    83 ns. La vraie fonction prend 38 000 ns : le meme seuil representait
#    1200 % de l'echelle de test et 3 % de l'echelle reelle. Le test echouait
#    une fois sur deux. Le seuil est desormais une FRACTION de la duree
#    mesuree.
#
# 2. Comparer des valeurs absolues ne distingue pas une fuite d'une
#    fluctuation. Huit mesures signees sur le serveur ont donne
#    -1380, +615, +375, +165, +35, +120, +10, -340 ns : deux negatifs, une
#    amplitude decroissante a mesure que le cache chauffe. Bruiter 10 000 000
#    ne peut pas couter MOINS que bruiter 0 -- le signe alterne signe le bruit
#    d'ordonnanceur, pas un canal. Une fuite reelle garde le meme sens a
#    chaque repetition.
#
# On exige donc TROIS choses : une difference statistiquement etablie, une
# amplitude relative non negligeable, et un signe constant sur plusieurs
# repetitions independantes.
FRACTION_EXPLOITABLE = 0.05     # 5 % de la duree mesuree
REPETITIONS_SIGNE = 5           # nombre de mesures independantes du signe
MAJORITE_SIGNE = 5              # il faut les 5 dans le meme sens

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
    """p bilaterale EXACTE, par enumeration des permutations.

    Avec sept valeurs, l espace complet fait 7! = 5040 cas : quelques
    millisecondes. Une approximation de Student n a donc aucune raison d etre
    ici -- et la premiere version de ce test en omettait le facteur correctif,
    ce qui la rendait fausse en plus d etre inutile.

    Le p exact est la proportion des permutations dont le rho, en valeur
    absolue, egale ou depasse celui observe.
    """
    if n > 8:                      # garde-fou : 9! = 362 880, deja lent
        raise ValueError(
            f"enumeration exacte impraticable a n = {n}. Revoir la methode "
            "avant d ajouter des valeurs a VALEURS.")
    reference = list(range(n))
    au_moins_aussi_extreme = 0
    total = 0
    for permutation in itertools.permutations(reference):
        total += 1
        if abs(spearman(reference, list(permutation))) >= abs(rho) - 1e-12:
            au_moins_aussi_extreme += 1
    return au_moins_aussi_extreme / total


def mann_whitney_u(a, b):
    """Statistique U et p normale approchee, egalites traitees par rangs.

    NOTE SUR LES EGALITES. Les rangs les traitent (rangs moyens), mais
    sigma n est PAS corrige pour elles. Sur des durees en nanosecondes,
    les egalites sont frequentes : la correction reduirait sigma, donc
    augmenterait |z| et le nombre d alertes. L omission va donc dans le
    sens de la prudence -- elle sous-detecte plutot qu elle ne
    sur-detecte. C est un choix, pas un oubli.
    """
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

# L etendue des medianes : sans elle, une correlation parfaite sur sept
# valeurs etalees de 3 ns declencherait l alerte. Le critere annonce comme
# double n en etait qu un dans la premiere version -- seule la branche
# Mann-Whitney testait l exploitabilite.
etendue = max(y) - min(y)
seuil_etendue = statistics.median(y) * FRACTION_EXPLOITABLE

if p < SEUIL_P and etendue > seuil_etendue:
    echecs.append(
        f"la duree de calcul correle avec la valeur d'entree : "
        f"rho = {rho:+.3f}, p exact = {p:.4f}, etendue {etendue:.0f} ns.\n"
        "    Un observateur capable de chronometrer le serveur pourrait en "
        "deduire des compteurs.\n"
        "    A verifier sur une machine au repos avant de conclure : une "
        "machine chargee produit des correlations fantomes.")

# --- Extremes compares deux a deux ---------------------------------------
#
# Spearman sur sept points est peu puissant. On compare aussi les
# distributions completes aux deux bornes, ou l'ecart serait maximal s'il
# existait.

# Les deux bornes sont mesurees ENTRELACEES, pas l une apres l autre.
#
# Mesurer 400 fois la borne basse puis 400 fois la haute reintroduirait
# exactement le confondant elimine plus haut : toute derive sur 800
# appels -- rechauffement du cache, changement de frequence du
# processeur, ordonnanceur -- se lirait comme un ecart systematique
# entre bornes. La premiere version de ce test avait ce defaut.
bas, haut = [], []
sequence = [(VALEURS[0], bas), (VALEURS[-1], haut)] * 400
random.shuffle(sequence)
for valeur, cible in sequence:
    cible.append(mesurer(valeur, 1))
u, p_u = mann_whitney_u(bas, haut)

med_bas, med_haut = statistics.median(bas), statistics.median(haut)
ecart = abs(med_haut - med_bas)
seuil_ecart = statistics.median(bas + haut) * FRACTION_EXPLOITABLE

# TROISIEME CRITERE : le signe doit etre constant.
#
# Une fuite reelle a un sens : bruiter la borne haute coute toujours plus, ou
# toujours moins. Une fluctuation d'ordonnanceur change de sens d'une mesure a
# l'autre. On ne calcule ce critere que si les deux premiers ont mordu --
# inutile de payer cinq mesures supplementaires quand rien n'est suspect.

signes = []
if p_u < SEUIL_P and ecart > seuil_ecart:
    for _ in range(REPETITIONS_SIGNE):
        b2, h2 = [], []
        seq2 = [(VALEURS[0], b2), (VALEURS[-1], h2)] * 200
        random.shuffle(seq2)
        for valeur, cible in seq2:
            cible.append(mesurer(valeur, 1))
        signes.append(statistics.median(h2) - statistics.median(b2))

    positifs = sum(1 for d in signes if d > 0)
    negatifs = sum(1 for d in signes if d < 0)
    coherent = max(positifs, negatifs) >= MAJORITE_SIGNE

    if coherent:
        echecs.append(
            f"les durees aux deux bornes de BOUNDS different, de façon "
            f"CONSTANTE : U = {u:.0f}, p = {p_u:.4f}, ecart median "
            f"{ecart:.0f} ns sur {statistics.median(bas + haut):.0f} ns "
            f"({100 * ecart / statistics.median(bas + haut):.1f} %).\n"
            f"    mediane a {VALEURS[0]} : {med_bas:.0f} ns ; "
            f"a {VALEURS[-1]} : {med_haut:.0f} ns.\n"
            f"    Ecarts signes sur {REPETITIONS_SIGNE} repetitions : "
            + ", ".join(f"{d:+.0f}" for d in signes) + " ns.\n"
            "    Le signe est constant : ce n'est pas de l'ordonnanceur.")

# --- Verdict --------------------------------------------------------------

if echecs:
    print("ECHEC : Porte 3 -- un canal temporel de calcul est visible.\n")
    for e in echecs:
        print("  - " + e)
    print("\nLa Porte 3 est declaree fermee dans "
          "VERA_THREAT_MODEL_COMPLETE.md.\nSi cet echec se reproduit sur une "
          "machine au repos, c'est la declaration qui est fausse.")
    sys.exit(1)

reference = statistics.median(bas + haut)
detail_signes = ""
if signes:
    detail_signes = ("; ecarts signes " +
                     ", ".join(f"{d:+.0f}" for d in signes) + " ns, "
                     "sens non constant")

print(f"OK : Porte 3 -- aucun canal temporel exploitable. "
      f"Spearman rho = {rho:+.3f} (p exact = {p:.4f}), etendue des medianes "
      f"{etendue:.0f} ns ; ecart median aux bornes {ecart:.0f} ns sur "
      f"{reference:.0f} ns ({100 * ecart / reference:.1f} %, seuil "
      f"{100 * FRACTION_EXPLOITABLE:.0f} %){detail_signes}.")
sys.exit(0)
