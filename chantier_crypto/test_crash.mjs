// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
// test_crash.mjs — Crash test Modele B. Deux phases separees par un kill -9
// du serveur (orchestre par crash_test.sh).
//   Phase 1 : vote A commite (200) + signature B obtenue mais PAS votee.
//             Etat sauve dans crash_state.json.
//   --- kill -9 + redemarrage ---
//   Phase 2 : rejeu A -> 409 (le vote a survecu au crash, tokens_consommes
//             recharge). Vote B -> 200 (la signature pre-crash verifie sous
//             la cle RSA rechargee depuis la DB chiffree : cycle de vie OK).
//             Jeton frais C -> 200 (le flux complet refonctionne).
import { RSABSSA } from '@cloudflare/blindrsa-ts';
import { readFileSync, writeFileSync } from 'node:fs';

const BASE = 'http://127.0.0.1:8020';
const ETAT = '/root/crypto_test/crash_state.json';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));
const DEP = 'CrashTest';
const phase = process.argv[2];

async function cookieRH() {
  const r = await fetch(`${BASE}/api/rh/connexion`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifiant: 'asso_acer', mot_de_passe: (process.env.VERA_TEST_PASS || 'test1234') }),
  });
  if (r.status !== 200) throw new Error(`connexion RH: ${r.status}`);
  return r.headers.get('set-cookie');
}

async function jetons(cookie, quantite) {
  const r = await fetch(`${BASE}/api/rh/generer_autorisations`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Cookie': cookie },
    body: JSON.stringify({ departement: DEP, quantite }),
  });
  return (await r.json()).autorisations.map((a) => a.jeton);
}

async function clePublique() {
  const r = await fetch(`${BASE}/api/cle_publique?departement=${DEP}`);
  if (r.status !== 200) throw new Error(`cle_publique: ${r.status}`);
  return crypto.subtle.importKey('spki', fromHex((await r.json()).cle_publique_hex),
    { name: 'RSA-PSS', hash: 'SHA-384' }, true, ['verify']);
}

async function preparerVote(jeton, pk) {
  const K = crypto.getRandomValues(new Uint8Array(32));
  const prepared = suite.prepare(K);
  const { blindedMsg, inv } = await suite.blind(pk, prepared);
  const rSig = await fetch(`${BASE}/api/signer_aveugle`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jeton_autorisation: jeton, message_aveugle_hex: toHex(blindedMsg) }),
  });
  if (rSig.status !== 200) throw new Error(`signer_aveugle: ${rSig.status}`);
  const sigData = await rSig.json();
  const signature = await suite.finalize(pk, prepared, inv, fromHex(sigData.signature_aveugle_hex));
  return {
    K_hex: toHex(prepared.slice(32)),
    randomizer_hex: toHex(prepared.slice(0, 32)),
    signature_hex: toHex(signature),
    reponse: 'oui',
    departement: DEP,
  };
}

const voter = (p) => fetch(`${BASE}/api/repondre`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(p),
});

const check = (nom, ok, detail = '') => {
  console.log(`${ok ? 'OK ' : '### ECHEC'} ${nom}${detail ? ' -- ' + detail : ''}`);
  if (!ok) process.exit(1);
};

if (phase === 'phase1') {
  const cookie = await cookieRH();
  const [jA, jB] = await jetons(cookie, 2);
  const pk = await clePublique();

  const payloadA = await preparerVote(jA, pk);
  const vA = await voter(payloadA);
  check('P1 vote A commite avant crash (200)', vA.status === 200, await vA.text());

  // B : signature obtenue, vote VOLONTAIREMENT non soumis avant le crash.
  const payloadB = await preparerVote(jB, pk);
  check('P1 signature B obtenue, non votee', true);

  writeFileSync(ETAT, JSON.stringify({ payloadA, payloadB }));
  console.log('P1 etat sauve, pret pour kill -9');

} else if (phase === 'phase2') {
  const { payloadA, payloadB } = JSON.parse(readFileSync(ETAT, 'utf8'));

  // Le vote A doit avoir survecu : rejeu -> 409, pas 200 (double vote) ni
  // 403/404 (etat perdu ou cle non rechargee).
  const rA = await voter(payloadA);
  check('P2 rejeu A apres crash refuse (409): vote persiste', rA.status === 409,
    `status=${rA.status}`);

  // La signature B, emise sous la cle d'AVANT le crash, doit verifier sous
  // la cle rechargee depuis la DB chiffree. Un 403 ici = cle regeneree au
  // lieu de rechargee = tous les liens distribues seraient morts.
  const rB = await voter(payloadB);
  check('P2 signature pre-crash votable apres reboot (200): cles rechargees',
    rB.status === 200, `status=${rB.status}`);

  // Flux complet a froid.
  const cookie = await cookieRH();
  const [jC] = await jetons(cookie, 1);
  const pk = await clePublique();
  const payloadC = await preparerVote(jC, pk);
  const rC = await voter(payloadC);
  check('P2 flux complet post-reboot (200)', rC.status === 200);

  console.log('\n=== CRASH TEST VALIDE : vote persiste, cles rechargees, flux operationnel ===');
} else {
  console.error('usage: node test_crash.mjs phase1|phase2');
  process.exit(1);
}
