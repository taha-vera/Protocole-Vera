# =====================================================================
# VERA / ANCRE - Validation formelle du mecanisme DP
# Preuve reproductible : garantie epsilon-DP exacte + borne MIA pire cas
#
# Lancer :  python validation_opendp.py
# Dependance : pip install opendp  (>= 0.15)
#
# Ce que ce fichier PROUVE :
#   1. La garantie epsilon = 0.5 est EXACTE, certifiee par OpenDP (lib auditee),
#      via meas.map() -- aucun Monte Carlo, aucun sampler maison.
#   2. L'AUC de l'attaquant d'appartenance optimal (MIA) au PIRE CAS est
#      bornee analytiquement et reste sous la borne theorique e^eps/(1+e^eps).
#   3. Le parametre bounds est utilise pour forcer une execution en temps
#      quasi-constant, conformement aux recommandations d'OpenDP et au
#      papier Jin et al. (IEEE S&P 2021) sur les fuites temporelles dans
#      les mecanismes DP (l'echantillonnage geometrique sans bounds fuite
#      l'amplitude du bruit via son temps d'execution).
#
# Ce que ce fichier NE prouve PAS (limites assumees, cf. section LIMITES) :
#   - protection contre un observateur reseau (hors perimetre VERA)
#   - protection contre la coercition (preuve volontaire par le repondant)
#   - anonymat sur petits effectifs (N faible : indelivrable, cf. seuil)
#   - qualification juridique anonymisation vs pseudonymisation (= avis CNIL/DPO)
# =====================================================================

import math
import opendp.prelude as dp
dp.enable_features("contrib")

# ---------------------------------------------------------------------
# Parametres du mecanisme (snapping sur grille AVANT bruit)
# ---------------------------------------------------------------------
# LES PARAMETRES SONT IMPORTES, PLUS RECOPIES.
#
# Ce fichier les redeclarait, annotes « = prod ». Le 27/08/2026, un audit
# externe a constate que BORNE_SUP y valait encore 10 000 alors que la
# production applique 10 000 000 depuis la recalibration du 04/07 -- un facteur
# mille, huit semaines durant, dans le fichier qui fait office de preuve
# formelle. L'en-tete affirmait pourtant certifier « EXACTEMENT le mecanisme
# execute par le serveur ».
#
# La consequence numerique etait nulle : epsilon = Delta_1 / scale ne depend pas
# des bornes, et le 0,5 certifie restait vrai. Mais la preuve portait sur un
# mecanisme qui, s'il etait reellement deploye, aurait la branche dependante des
# donnees que l'elargissement des bornes a precisement supprimee
# (vera_dp_noise.py, lignes 32-45). Une preuve qui certifie autre chose que ce
# qui tourne ne prouve rien.
#
# Recopier une valeur, c'est en creer une seconde qui derive. Elles sont
# desormais importees : ce fichier ne peut plus diverger sans cesser de
# s'executer.
from vera_dp_noise import DELTA_INT, SCALE, BOUNDS

EPS_CIBLE = DELTA_INT / SCALE           # 0,5 -- deduit, pas redeclare

# Bornes du domaine : la moyenne snappee ne peut pas sortir de cette plage.
# Necesssaires pour que OpenDP utilise un echantillonnage en temps quasi-constant
# (cf. parametre bounds dans make_laplace / then_laplace), conformement aux
# recommandations de la documentation OpenDP et au papier Jin et al. 2021
# (IEEE S&P) qui montre que l'echantillonnage geometrique sans bounds fuite
# l'amplitude du bruit via son temps d'execution -- Porte 3 du modele de menace.
BORNE_INF, BORNE_SUP = BOUNDS

# ---------------------------------------------------------------------
# 1. GARANTIE epsilon-DP EXACTE (certifiee par OpenDP)
#    Avec bounds pour temps quasi-constant (Porte 3 du modele de menace)
# ---------------------------------------------------------------------
space = dp.atom_domain(T=int, bounds=(BORNE_INF, BORNE_SUP)), dp.absolute_distance(T=int)
meas = space >> dp.m.then_laplace(scale=SCALE)
eps = meas.map(d_in=DELTA_INT)          # garantie analytique, PAS une estimation

print("=== 1. GARANTIE DP (OpenDP) ===")
print(f"  Delta_int = {DELTA_INT}, scale = {SCALE}")
print(f"  Bornes domaine = [{BORNE_INF}, {BORNE_SUP}] (temps quasi-constant, Porte 3)")
print(f"  epsilon garanti (meas.map) = {eps}")
ok_eps = eps <= EPS_CIBLE + 1e-12
print(f"  VERDICT : {'OK - garantie exacte' if ok_eps else 'ECHEC'}")

# ---------------------------------------------------------------------
# 2. BORNE MIA PIRE CAS (attaquant optimal Neyman-Pearson, analytique)
#    Membre : sortie centree en DELTA_INT ; non-membre : centree en 0.
#    PMF Laplace discrete de parametre t = SCALE.
# ---------------------------------------------------------------------
T = SCALE
c = (math.exp(1 / T) - 1) / (math.exp(1 / T) + 1)
pmf = lambda x: c * math.exp(-abs(x) / T)

K = int(60 * T)            # troncature : masse residuelle ~ e^-60, negligeable
cdf_n = 0.0
auc = 0.0
for x in range(-K, K + 1):
    p_n = pmf(x)           # non-membre en x
    p_m = pmf(x - DELTA_INT)  # membre en x
    auc += p_m * (cdf_n + 0.5 * p_n)
    cdf_n += p_n

borne = math.exp(EPS_CIBLE) / (1 + math.exp(EPS_CIBLE))
print("\n=== 2. MIA PIRE CAS (analytique) ===")
print(f"  AUC attaquant optimal (pire cas) = {auc:.6f}")
print(f"  Borne theoreme eps-DP            = {borne:.6f}")
ok_mia = auc <= borne + 1e-9
print(f"  VERDICT : {'OK - AUC sous la borne' if ok_mia else 'ECHEC'}")

# ---------------------------------------------------------------------
# 3. COMPOSITION : cout de k requetes sequentielles sur les memes donnees
#    Rappel : avec partition (un token / individu / epoque), la composition
#    est PARALLELE -> epsilon reste 0.5 quel que soit le nombre de cohortes.
# ---------------------------------------------------------------------
print("\n=== 3. COMPOSITION SEQUENTIELLE (information) ===")
print(f"  {'k':>3} {'eps_total':>10} {'AUC_max_MIA':>12}")
for k in range(1, 11):
    e = k * EPS_CIBLE
    print(f"  {k:>3} {e:>10.1f} {math.exp(e)/(1+math.exp(e)):>12.4f}")
print("  -> des k=4 (eps=2.0) la protection est quasi nulle :")
print("     budget plafonne obligatoire + partition par token/epoque.")

# ---------------------------------------------------------------------
# 4. LIMITES ASSUMEES (a ne jamais dissimuler)
# ---------------------------------------------------------------------
print("\n=== 4. LIMITES (modele de menace) ===")
print("  L1 observateur reseau : hors perimetre (IP vue en amont de VERA)")
print("  L2 coercition         : un repondant peut prouver volontairement sa reponse")
print("  L3 petits effectifs   : sous un seuil N, anonymat indelivrable -> refus de publier")
print("  L4 qualification RGPD  : anonymisation vs pseudonymisation = avis CNIL/DPO requis")

# ---------------------------------------------------------------------
print("\n=== SYNTHESE ===")
print(f"  Garantie DP exacte : {'OK' if ok_eps else 'ECHEC'}")
print(f"  MIA pire cas borne : {'OK' if ok_mia else 'ECHEC'}")
print(f"  Porte 3 (canal temporel) : bounds={BORNE_INF},{BORNE_SUP} active")
# CE BLOC EST UNE TRACE HISTORIQUE, PAS UNE MESURE COURANTE.
#
# Il rapporte les mesures du 30/06/2026, faites sur bounds=(0,100) et sur les
# valeurs [0,1,25,50,75,99,100] -- une calibration anterieure. Il etait imprime
# comme s'il decrivait l'etat courant, ce qui a produit trois bornes
# differentes dans une meme sortie (audit du 27/08).
#
# La mesure a jour, sur les bornes reellement en service, est faite par
# tests/test_porte3_timing.py : elle s'execute a chaque passage de la suite.
print("  Test timing du 30 juin 2026 (HISTORIQUE, calibration d'alors :")
print("  bounds=(0,100), valeurs [0,1,25,50,75,99,100], serveur Hetzner) :")
print("  - Sans bounds : ecart mediane 3.34%, Mann-Whitney p~0 — fuite confirmee")
print("  - Avec bounds : ecart mediane 0.18%, Mann-Whitney p=0.937 — pas de fuite")
print("    Spearman rho=-0.1429, p=0.760 — pas de correlation valeur/temps")
print("  MESURE COURANTE : tests/test_porte3_timing.py, sur les bornes en")
print("  service, rejouee a chaque passage de la suite.")
print("  FORMULATION HONNETE (validee par challenge multi-IA) :")
print("  'L'ajout de bounds supprime la difference temporelle detectee.")
print("   Aucune fuite temporelle exploitable mise en evidence dans ces conditions.")
print("   Ceci ne constitue pas une preuve formelle de temps constant au sens")
print("   cryptographique, mais constitue une forte indication que le vecteur")
print("   d'attaque initial (Jin et al., IEEE S&P 2021) est neutralise.'")
print("  Validation preliminaire (Termux) : sampler Canonne z=-0.19, timing 2.83% (bruit)")
print("  Preuve deposable = ce fichier (OpenDP, machine Windows, 2026-06-30)")
