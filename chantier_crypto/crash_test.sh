#!/bin/bash
# crash_test.sh — Orchestration du crash test Modele B.
#
# AUCUN SECRET REEL DANS CE FICHIER. Les valeurs ci-dessous sont des
# constantes de test, volontairement courtes et lisibles, utilisees contre
# une base jetable (crash_test.db) sur le port 8020. Les secrets de
# production sont dans l'unite systemd, permissions 600, jamais versionnes.
# La passphrase doit etre FIXE et identique aux deux lancements : c'est ce
# qui permet de prouver que les cles chiffrees se rechargent apres un kill -9.
# DB FRAICHE dediee (crash_test.db), passphrase de test fixe (la meme aux
# deux lancements : indispensable pour prouver le rechargement des cles),
# port 8020, prod intouchee. kill -9 = panne electrique simulee cote
# processus (WAL + synchronous=FULL font le reste cote disque).
set -e

PY=/root/vera_blind_sig/.venv/bin/python3
LOG=/tmp/crash_test.log
PIDF=/tmp/crash_test.pid

# LE CODE EXERCE EST CELUI DU DEPOT, PAS UNE COPIE.
# Ce script executait /root/vera_test et /root/crypto_test : deux exemplaires
# hors depot que rien ne mettait a jour. Au 23/08/2026, /root/vera_test datait
# du 26 juillet -- le test le plus complet de la suite validait depuis un mois
# une version qui n'etait plus deployee, sans qu'aucun echec ne le signale.
RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_JETABLE=/tmp/vera_crash_test
BASE=http://127.0.0.1:8020
if [ ! -f "$RACINE/vera_consultation_api.py" ]; then
  echo "### $RACINE ne contient pas vera_consultation_api.py." >&2
  exit 1
fi
mkdir -p "$BASE_JETABLE"

# Empreinte du compte de test, derivee une fois et reutilisee aux deux
# lancements. Ce script passait auparavant VERA_ADMIN_PASS ; ce repli en clair
# a ete retire le 23/08/2026 et l'API refuse desormais de demarrer avec cette
# variable -- le crash test ne pouvait donc plus s'executer du tout.
#
# La constante reste une constante de test, en clair et assumee : elle vaut
# contre une base jetable sur le port 8020. Ce qui change est la VOIE, pas le
# secret : le crash test emprunte maintenant le meme chemin d'amorcage que la
# production.
# Le compte d'amorcage cree ici et celui auquel test_crash.mjs se connecte
# doivent coincider. Ils ne coincidaient pas : le script creait compte_de_test
# tandis que le .mjs se connectait comme asso_acer/test1234. Cela ne marchait
# que sur /root/crypto_test, ou un environnement local fournissait les bonnes
# valeurs -- valeurs qui n'existaient nulle part dans le depot. Une constante,
# partagee par les deux.
UTILISATEUR_DE_TEST=asso_acer
MDP_DE_TEST=CONSTANTE_DE_TEST_PAS_UN_SECRET
export VERA_TEST_PASS="$MDP_DE_TEST"

EMPREINTE_DE_TEST=$(cd "$RACINE" && "$PY" -c \
  "import vera_admin_auth as a; print(a.generer_empreinte('$MDP_DE_TEST'))")
if [ -z "$EMPREINTE_DE_TEST" ]; then
  echo "### impossible de deriver l'empreinte du compte de test" >&2
  exit 1
fi

lancer() {
  cd "$RACINE"
  VERA_DB_KEY=CONSTANTE_DE_TEST_PAS_UN_SECRET \
  VERA_DB_PATH=$BASE_JETABLE/crash_test.db \
  VERA_ADMIN_USER="$UTILISATEUR_DE_TEST" \
  VERA_ADMIN_HASH="$EMPREINTE_DE_TEST" \
  nohup "$PY" -m uvicorn vera_consultation_api:app --host 127.0.0.1 --port 8020 >> "$LOG" 2>&1 &
  echo $! > "$PIDF"
  sleep 3
  curl -sf http://127.0.0.1:8020/api/health > /dev/null || { echo "### serveur ne demarre pas, voir $LOG"; exit 1; }
}

echo "--- Nettoyage + lancement 1 ---"
rm -f "$BASE_JETABLE"/crash_test.db* "$BASE_JETABLE"/crash_state.json "$LOG"
lancer

# PREPARATION DE L'ETAT EXERCE PAR LE TEST.
#
# test_crash.mjs genere des jetons pour le groupe CrashTest sans jamais le
# declarer : il supposait un etat preexistant. Cet etat vivait dans la base de
# /root/crypto_test, amorcee a la main par des essais anciens et documentee
# nulle part -- le test le plus complet de la suite n'etait donc reproductible
# par personne, et il aurait suffi d'effacer cette base pour le perdre.
#
# L'ordre est impose par le code : /api/rh/question n'est acceptee que tant
# qu'aucune cle n'existe, et /api/rh/declarer_groupes cree les cles.
preparer_consultation() {
  local cookie
  cookie=$(curl -s -i -X POST "$BASE/api/rh/connexion" \
      -H "Content-Type: application/json" \
      -d "{\"identifiant\":\"$UTILISATEUR_DE_TEST\",\"mot_de_passe\":\"$MDP_DE_TEST\"}" \
    | grep -i '^set-cookie:' | sed 's/^[Ss]et-[Cc]ookie: //' | tr -d '\r')
  if [ -z "$cookie" ]; then
    echo "### connexion RH impossible -- voir $LOG" >&2
    exit 1
  fi

  curl -sf -X POST "$BASE/api/rh/question" \
    -H "Content-Type: application/json" -H "Cookie: $cookie" \
    -d '{"intitule":"Question de test du crash test, sans valeur reelle."}' \
    > /dev/null || { echo "### /api/rh/question a echoue" >&2; exit 1; }

  curl -sf -X POST "$BASE/api/rh/declarer_groupes" \
    -H "Content-Type: application/json" -H "Cookie: $cookie" \
    -d '{"groupes":["CrashTest"]}' \
    > /dev/null || { echo "### /api/rh/declarer_groupes a echoue" >&2; exit 1; }

  # L'API refuse une ouverture immediate (422) : elle exigerait que l'emission
  # des invitations et les depots se separent dans le temps, sans quoi la
  # proximite des deux horodatages suffirait a joindre les deux registres --
  # LIMITS.md section 9. On fixe donc l'ouverture a +2 s, puis on attend.
  local ouverture=$(( $(date +%s) + 2 ))
  curl -sf -X POST "$BASE/api/rh/ouverture" \
    -H "Content-Type: application/json" -H "Cookie: $cookie" \
    -d "{\"ouverture_unix\":$ouverture}" \
    > /dev/null || { echo "### /api/rh/ouverture a echoue" >&2; exit 1; }
  sleep 3

  echo "--- Consultation preparee (groupe CrashTest, depots ouverts) ---"
}

preparer_consultation

echo "--- Phase 1 (vote + signature en attente) ---"
cd "$RACINE/chantier_crypto"
node test_crash.mjs phase1

echo "--- CRASH BRUTAL (kill -9) ---"
kill -9 "$(cat "$PIDF")"
sleep 1

echo "--- Relancement (meme passphrase, meme DB) ---"
lancer

echo "--- Phase 2 (verification survie) ---"
cd "$RACINE/chantier_crypto"
node test_crash.mjs phase2

kill -9 "$(cat "$PIDF")" 2>/dev/null || true
rm -f "$BASE_JETABLE"/crash_test.db* "$BASE_JETABLE"/crash_state.json
echo "--- Bac a sable nettoye ---"
