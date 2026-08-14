#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_dp_noise.py - Mecanisme de bruitage DP reel, branche sur les
endpoints qui publient des resultats agreges.

Recalibration 04/07/2026 (suite audit 3 IA independantes) :
- Ancien : Delta=10, scale=20, epsilon=0.5
- Nouveau : Delta=2, scale=4, epsilon=0.5 (meme garantie, bruit 5x plus faible)

Justification : la sensibilite reelle d'un vote binaire (oui/non/abstention)
est Delta=2 en modele de voisinage par substitution (bounded DP), pas Delta=10.
L'ancien Delta=10 etait une marge volontairement large non justifiee par la
structure des donnees, qui degradait inutilement la precision des resultats.

Canal temporel (Porte 3) : une fuite sub-microseconde est detectee
statistiquement par Mann-Whitney a N=10000 (p<0.001) sur les deux
configurations (scale=4 et scale=20). L'ecart de medianes est inferieur
a 1 microseconde dans les deux cas -- inexploitable via reseau HTTP dont
la latence est de l'ordre de 50-100 millisecondes. Formulation honnete :
fuite sub-microseconde detectee, non exploitable en conditions reelles.
"""

import opendp.prelude as dp

dp.enable_features("contrib")

DELTA_INT = 2
SCALE = 4.0
# Borne du DOMAINE OpenDP, pas de la calibration. `scale` est passe
# explicitement a make_laplace : elargir cette borne ne change ni le bruit ni
# epsilon = Delta1/scale = 2/4 = 0,5.
#
# POURQUOI ELLE EST SI LARGE
# Une version anterieure la fixait a 10 000 et LEVAIT au-dela, pour ne pas
# publier un resultat faussement ecrete. L'intention etait bonne, la
# consequence formelle ne l'etait pas : deux bases voisines a 10 000 et 10 001
# produisaient des sorties distinguables avec probabilite 1 -- une branche
# dependante des donnees, donc une perte de confidentialite non bornee sur cet
# evenement. Le mecanisme n'etait plus strictement epsilon-DP.
#
# Une borne inatteignable supprime la branche sans rien changer d'autre. Le
# scenario qui la motivait (plus de dix mille reponses dans un seul groupe)
# reste hors de portee de ce systeme, mais il n'a plus besoin d'etre traite
# par une exception.
BOUNDS = (0, 10_000_000)

_domaine = dp.atom_domain(T=int, bounds=BOUNDS)
_metrique = dp.absolute_distance(T=int)
_mecanisme_laplace = dp.m.make_laplace(_domaine, _metrique, scale=SCALE)


def appliquer_bruit_dp(valeur_brute: int) -> int:
    """Ajoute le bruit de Laplace calibre a un comptage.

    AUCUNE BRANCHE DEPENDANTE DES DONNEES ICI.
    Une version anterieure levait au-dela de 10 000 pour eviter un ecretage
    silencieux. L'intention etait juste -- un resultat faux publie en silence
    est pire qu'un refus -- mais la forme ne l'etait pas : le simple fait de
    lever, ou non, distingue deux bases voisines avec probabilite 1. La borne
    est desormais inatteignable (voir BOUNDS), ce qui supprime la branche sans
    toucher a la calibration.
    L'ecretage residuel reste 1-lipschitzien : il n'augmente pas la sensibilite.
    """
    valeur_bornee = max(BOUNDS[0], min(BOUNDS[1], valeur_brute))
    valeur_bruitee = _mecanisme_laplace(valeur_bornee)
    return max(0, valeur_bruitee)


# --------------------------------------------------------------------------
# Publication d'un histogramme a 3 cases avec projection sur le simplexe.
#
# PRINCIPE (Hay et al. 2010, "Boosting the Accuracy of Differentially Private
# Histograms Through Consistency", VLDB) : imposer une contrainte de coherence
# connue a posteriori sur un histogramme bruite, par post-traitement, reduit
# l'erreur sans cout en epsilon. Hay et al. traitent le cas general (contraintes
# hierarchiques). Notre cas est l'instance la plus simple : une seule contrainte,
# la somme exacte = N.
#
# ALGORITHME : projection alternee par clip-and-shift iteratif (POCS -
# Projections Onto Convex Sets) sur le simplexe {x >= 0, somme = N} : on
# annule les negatifs puis on redistribue l'ecart uniformement, en iterant
# jusqu'a convergence. NB : ce n'est PAS la projection L2 euclidienne exacte
# de Duchi et al. 2008 (tri decroissant + seuil) ; c'est une heuristique de
# coherence qui converge vers un point du simplexe. Le total N est publie
# exact car invariant sous substitution (sensibilite 0).
#
# PREUVE DE SENSIBILITE (corrigee le 14/07/2026) :
# Adjacence par SUBSTITUTION : un individu qui change d'avis retire son vote
# d'une case et l'ajoute a une autre -> deux cases changent de 1 -> la
# sensibilite L1 du vecteur histogramme est Delta_1 = 2.
# Le mecanisme est un Laplace VECTORIEL avec scale = Delta_1 / epsilon = 4,
# ce qui donne epsilon = 0.5 pour l'histogramme entier.
# (Ce n'est PAS de la composition parallele : celle-ci exigerait qu'un
# individu n'affecte qu'une seule case, ce qui est faux sous substitution.)
#
# PROJECTION : l'effectif total N est invariant sous substitution
# (sensibilite 0), donc publiable exactement sans consommer de budget.
# On projette le vecteur bruite sur {x >= 0, somme(x) = N}. C'est du
# POST-TRAITEMENT : gratuit en epsilon (theoreme de post-traitement DP,
# valable quelle que soit la projection utilisee). Le gain de precision
# (environ 25%) est MESURE EMPIRIQUEMENT sur notre cas a 3 cases (voir
# test_precision_kmin.py), pas derive analytiquement de la projection L2.
# --------------------------------------------------------------------------

def _projeter_sur_simplexe(valeurs_bruitees: list[float], total: int) -> list[int]:
    """Projette un vecteur bruite sur {x >= 0, somme(x) = total}."""
    v = [float(x) for x in valeurs_bruitees]
    k = len(v)
    for _ in range(100):
        v = [max(0.0, x) for x in v]
        ecart = (total - sum(v)) / k
        v = [x + ecart for x in v]
        if abs(sum(v) - total) < 1e-9 and all(x >= -1e-9 for x in v):
            break
    entiers = [max(0, int(round(x))) for x in v]
    # Correction d'arrondi : forcer la somme exacte
    delta = total - sum(entiers)
    if delta != 0:
        i_max = entiers.index(max(entiers))
        entiers[i_max] = max(0, entiers[i_max] + delta)
    return entiers


def publier_histogramme_dp(comptes: dict, total_reel: int) -> dict:
    """
    Publie un histogramme bruite ET projete.

    comptes     : {'oui': 80, 'non': 30, 'abstention': 10}
    total_reel  : effectif exact du departement (N, sensibilite 0)

    Retourne {'oui': 78, 'non': 32, 'abstention': 10} -- somme exacte = N.
    Budget consomme : epsilon = 0.5 (Laplace vectoriel, Delta_1 = 2).
    """
    cles = list(comptes.keys())
    bruites = [appliquer_bruit_dp(comptes[c]) for c in cles]
    projetes = _projeter_sur_simplexe(bruites, total_reel)
    return dict(zip(cles, projetes))
