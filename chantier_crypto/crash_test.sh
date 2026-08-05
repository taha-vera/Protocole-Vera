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

lancer() {
  cd /root/vera_test
  VERA_DB_KEY=CONSTANTE_DE_TEST_PAS_UN_SECRET \
  VERA_DB_PATH=/root/vera_test/crash_test.db \
  VERA_ADMIN_USER=compte_de_test \
  VERA_ADMIN_PASS=CONSTANTE_DE_TEST_PAS_UN_SECRET \
  nohup "$PY" -m uvicorn vera_consultation_api:app --host 127.0.0.1 --port 8020 >> "$LOG" 2>&1 &
  echo $! > "$PIDF"
  sleep 3
  curl -sf http://127.0.0.1:8020/api/health > /dev/null || { echo "### serveur ne demarre pas, voir $LOG"; exit 1; }
}

echo "--- Nettoyage + lancement 1 ---"
rm -f /root/vera_test/crash_test.db* /root/crypto_test/crash_state.json "$LOG"
lancer

echo "--- Phase 1 (vote + signature en attente) ---"
cd /root/crypto_test
node test_crash.mjs phase1

echo "--- CRASH BRUTAL (kill -9) ---"
kill -9 "$(cat "$PIDF")"
sleep 1

echo "--- Relancement (meme passphrase, meme DB) ---"
lancer

echo "--- Phase 2 (verification survie) ---"
cd /root/crypto_test
node test_crash.mjs phase2

kill -9 "$(cat "$PIDF")" 2>/dev/null || true
rm -f /root/vera_test/crash_test.db* /root/crypto_test/crash_state.json
echo "--- Bac a sable nettoye ---"
