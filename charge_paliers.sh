#!/bin/bash
# charge_paliers.sh -- montee en charge par lots de 1000.
#
# La generation de jetons est plafonnee a 1000 par appel (Field le=1000 dans
# l'API). Ce n'est pas une limite du systeme mais un garde-fou : il evite
# qu'une erreur de saisie ne genere un million de liens. Pour tester au-dela,
# on enchaine les lots -- ce que ferait un vrai RH pour une grande
# organisation, en cliquant plusieurs fois.
#
# USAGE : ./charge_paliers.sh 5000 [parallele]

set -e
TOTAL=${1:-5000}
PARALLELE=${2:-8}
LOTS=$(( (TOTAL + 999) / 1000 ))
DEPT="CHARGE${TOTAL}"
PY=/root/vera_blind_sig/.venv/bin/python3

# Le mot de passe est SAISI, pas extrait de la configuration.
#
# Cette ligne lisait auparavant VERA_ADMIN_PASS dans l'unite systemd. Deux
# raisons de ne plus le faire. D'abord elle ne peut plus fonctionner : le repli
# en clair a ete retire le 23/08/2026 et l'unite ne porte plus qu'une empreinte
# PBKDF2, dont on ne retrouve pas le mot de passe. Ensuite, extraire un secret
# d'un fichier de configuration pour le poser dans une variable d'environnement
# etait douteux independamment de cette panne : la variable se retrouve dans
# l'environnement de chaque processus fils, donc lisible dans /proc.
#
# La saisie a lieu UNE fois ; charge_votants.py lit ensuite VERA_TEST_MDP au
# lieu de redemander a chaque lot.
read -r -s -p "Mot de passe RH (saisie masquee) : " VERA_TEST_MDP
echo
if [ -z "$VERA_TEST_MDP" ]; then
    echo "Aucun mot de passe saisi -- abandon." >&2
    exit 1
fi
export VERA_TEST_MDP

echo "Montee en charge : $TOTAL votants en $LOTS lots de 1000, sur le departement $DEPT"
echo "Parallele : $PARALLELE"
echo "========================================================"
DEBUT=$(date +%s)

for i in $(seq 1 $LOTS); do
  RESTANT=$(( TOTAL - (i - 1) * 1000 ))
  N=$(( RESTANT > 1000 ? 1000 : RESTANT ))
  printf "\n--- lot %d/%d (%d votants) ---\n" "$i" "$LOTS" "$N"
  # Meme departement a chaque lot : les votes s'accumulent, ce qui permet de
  # voir si le debit se degrade quand la base grossit.
  $PY charge_votants.py --votants "$N" --departement "$DEPT" \
      --identifiant asso_acer --parallele "$PARALLELE" 2>&1 \
    | grep -E "Generation|Duree|Reussis|Latence|Echecs|Votes recus|Publie|Ecart|Somme"
done

FIN=$(date +%s)
unset VERA_TEST_MDP
echo ""
echo "========================================================"
echo "Total : $TOTAL votants en $(( FIN - DEBUT )) s"
echo "Debit moyen : $(( TOTAL / (FIN - DEBUT + 1) )) votes/s"
