#!/bin/bash
# run_tests.sh -- lance toute la suite Python et PROPAGE les codes de sortie.
#
# Raison d'etre (audit du 25/07/2026) : quatre tests plantaient avant toute
# assertion depuis le refactor du Modele B, et personne ne s'en etait apercu
# pendant des jours. Sans lanceur unique qui remonte les echecs, un test mort
# le reste indefiniment -- il figure dans le depot, rassure, et ne verifie
# rien. C'est le pire etat possible pour une suite de securite.
#
# Usage :
#   ./run_tests.sh
#
# Chaque test tourne sur une base JETABLE (VERA_DB_PATH). Le garde-fou de
# vera_persistance refuse de toute facon qu'un test_*.py touche la production.

set -u

VENV="${VERA_PYTHON:-/root/vera_blind_sig/.venv/bin/python3}"
UNIT="/etc/systemd/system/vera-consultation.service"

if [ -z "${VERA_DB_KEY:-}" ] && [ -r "$UNIT" ]; then
    VERA_DB_KEY=$(grep VERA_DB_KEY "$UNIT" | sed 's/.*VERA_DB_KEY=//; s/"//g')
    export VERA_DB_KEY
fi
export VERA_ADMIN_USER="${VERA_ADMIN_USER:-compte_de_test}"

# La suite exerce la voie de PRODUCTION -- VERA_ADMIN_HASH -- et jamais le
# repli en clair VERA_ADMIN_PASS. Constat du 23/08/2026 : ce script exportait
# le mot de passe en clair, donc chaque test empruntait le chemin par lequel
# des secrets ont fuite le 31/07, tandis que le chemin reellement en service
# n'etait couvert par rien. Le repli devant etre retire, sa disparition aurait
# casse la suite sans qu'aucun test n'ait jamais valide son remplacant.
unset VERA_ADMIN_PASS
if [ -z "${VERA_ADMIN_HASH:-}" ]; then
    VERA_ADMIN_HASH=$("$VENV" -c \
        "import vera_admin_auth as a; print(a.generer_empreinte('motdepasse_de_test'))" \
        2>/dev/null) || VERA_ADMIN_HASH=""
    if [ -z "$VERA_ADMIN_HASH" ]; then
        echo "ECHEC : impossible de deriver VERA_ADMIN_HASH avec $VENV." >&2
        exit 1
    fi
    export VERA_ADMIN_HASH
fi

# CONTROLE DE DIVERGENCE depot / production.
# Les tests importent les modules du REPERTOIRE COURANT (le depot), alors que
# le service tourne sur ceux de /root. Constat du 26/07 : un sabotage applique
# a /root n'etait pas vu par la suite, qui exerçait la copie du depot. Si les
# deux divergent, les tests valident une version qui n'est pas celle en
# service -- un correctif commite mais non deploye, ou l'inverse, passerait
# inaperçu.
PROD_DIR="${VERA_PROD_DIR:-/root}"
divergents=""
for module in vera_consultation_api.py vera_persistance.py \
              vera_signature_manager.py vera_epsilon_budget.py \
              vera_dp_noise.py vera_admin_auth.py; do
    if [ -f "$module" ] && [ -f "$PROD_DIR/$module" ]; then
        if ! cmp -s "$module" "$PROD_DIR/$module"; then
            divergents="$divergents $module"
        fi
    fi
done
if [ -n "$divergents" ]; then
    echo "AVERTISSEMENT : le depot et $PROD_DIR divergent sur :$divergents"
    echo "Les tests ci-dessous valident la version du DEPOT, pas celle en service."
    echo "---------------------------------------------------"
fi

passes=0
echecs=0
liste_echecs=""

echo "Suite de tests VERA"
echo "==================================================="

# Les tests vivent dans tests/ depuis le 26/08. Lances depuis ce
# sous-repertoire, ils ne trouveraient plus les modules de l'application, que
# Python cherche a cote du script execute et non dans le repertoire courant.
# PYTHONPATH rend la racine du depot importable : une ligne ici plutot qu'un
# sys.path.insert recopie dans chacun des trente fichiers.
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)${PYTHONPATH:+:$PYTHONPATH}"

if [ ! -d tests ]; then
    echo "ECHEC : le repertoire tests/ est introuvable." >&2
    echo "Lancer ce script depuis la racine du depot." >&2
    exit 1
fi

for f in tests/test_*.py; do
    [ -e "$f" ] || continue
    base_jetable=$(mktemp -u /tmp/vera_test_XXXXXX.db)
    sortie=$(VERA_DB_PATH="$base_jetable" "$VENV" "$f" 2>&1)
    code=$?
    rm -f "$base_jetable" "$base_jetable"-wal "$base_jetable"-shm
    if [ $code -eq 0 ]; then
        printf "PASS   %s\n" "$(basename "$f")"
        passes=$((passes + 1))
    else
        printf "ECHEC  %s (code %d)\n" "$(basename "$f")" "$code"
        echo "$sortie" | tail -3 | sed 's/^/         /'
        echecs=$((echecs + 1))
        liste_echecs="$liste_echecs $f"
    fi
done

echo "==================================================="
echo "$passes reussis, $echecs echoues"

if [ $echecs -ne 0 ]; then
    echo "Fichiers en echec :$liste_echecs"
    exit 1
fi

echo
echo "Les tests JS (chantier_crypto/) exigent un serveur de test vivant."
echo "Voir chantier_crypto/test_brique7_v2.mjs et test_crash.mjs, qui sont"
echo "les plus complets de la suite : chemin HTTP reel, courses concurrentes,"
echo "et survie de l'anti-rejeu a un kill -9."
exit 0
