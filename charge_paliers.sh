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

export VERA_TEST_MDP=$(grep -oP 'VERA_ADMIN_PASS=\K[^"]*' /etc/systemd/system/vera-consultation.service)

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
