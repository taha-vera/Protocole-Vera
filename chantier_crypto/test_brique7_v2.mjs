// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
// test_brique7_v2.mjs — Brique 7 durcie. Prouve ce que la v1 ne prouvait pas :
//   T3  : K survit reellement a un 422 (faute de frappe -> revote possible)
//   T5  : course anti-rejeu (2 requetes simultanees meme K -> exactement un 200)
//   T6  : confusion de departement (signature DepA + champ departement=DepB -> 403)
//   T7  : DoS keygen ferme (departement arbitraire -> 404, pas de creation de cle)
import { RSABSSA } from '@cloudflare/blindrsa-ts';

const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));
const DEP_A = 'Brique7vA';
const DEP_B = 'Brique7vB';

const login = await fetch(`${BASE}/api/rh/connexion`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ identifiant: 'asso_acer', mot_de_passe: (process.env.VERA_TEST_PASS || 'test1234') }),
});
const cookie = login.headers.get('set-cookie');

async function genererJetons(dep, quantite) {
  const r = await fetch(`${BASE}/api/rh/generer_autorisations`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Cookie': cookie },
    body: JSON.stringify({ departement: dep, quantite }),
  });
  return (await r.json()).autorisations.map((a) => a.jeton);
}

async function clePublique(dep) {
  const r = await fetch(`${BASE}/api/cle_publique?departement=${dep}`);
  if (r.status !== 200) throw new Error(`cle_publique ${dep}: ${r.status}`);
  return crypto.subtle.importKey('spki', fromHex((await r.json()).cle_publique_hex),
    { name: 'RSA-PSS', hash: 'SHA-384' }, true, ['verify']);
}

// Flux complet cote client : jeton -> signature aveugle -> payload de vote.
async function preparerVote(dep, jeton, pk) {
  const K = crypto.getRandomValues(new Uint8Array(32));
  const prepared = suite.prepare(K);
  const { blindedMsg, inv } = await suite.blind(pk, prepared);
  const rSig = await fetch(`${BASE}/api/signer_aveugle`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jeton_autorisation: jeton, message_aveugle_hex: toHex(blindedMsg) }),
  });
  const sigData = await rSig.json();
  const signature = await suite.finalize(pk, prepared, inv, fromHex(sigData.signature_aveugle_hex));
  return {
    K_hex: toHex(prepared.slice(32)),
    randomizer_hex: toHex(prepared.slice(0, 32)),
    signature_hex: toHex(signature),
    reponse: 'oui',
    departement: dep,
  };
}

const voter = (payload) => fetch(`${BASE}/api/repondre`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

const jetonsA = await genererJetons(DEP_A, 4);
const jetonsB = await genererJetons(DEP_B, 1);
const pkA = await clePublique(DEP_A);
const resultats = [];
const check = (nom, ok, detail = '') => {
  resultats.push(ok);
  console.log(`${ok ? 'OK ' : '### ECHEC'} ${nom}${detail ? ' -- ' + detail : ''}`);
};

// T1 + T2 : vote nominal puis rejeu.
const p1 = await preparerVote(DEP_A, jetonsA[0], pkA);
const v1 = await voter(p1);
check('T1 vote accepte (200)', v1.status === 200, await v1.text());
const v2 = await voter(p1);
check('T2 rejeu meme K refuse (409)', v2.status === 409);

// T3 : SURVIE DU K. K frais -> reponse invalide (422) -> MEME K, reponse
// valide -> DOIT etre 200. C'est le scenario reel de la faute de frappe.
// La v1 ne testait le 422 qu'avec un K deja consomme : indistinguable.
const p3 = await preparerVote(DEP_A, jetonsA[1], pkA);
const v3a = await voter({ ...p3, reponse: 'bidon' });
const v3b = await voter(p3);
check('T3 K survit au 422 (422 puis 200 avec le meme K)',
  v3a.status === 422 && v3b.status === 200,
  `422=${v3a.status}, revote=${v3b.status}`);

// T4 : signature invalide (K aleatoire non signe) -> 403.
const p4 = { ...p1, K_hex: toHex(crypto.getRandomValues(new Uint8Array(32))) };
const v4 = await voter(p4);
check('T4 signature invalide refusee (403)', v4.status === 403);

// T5 : COURSE ANTI-REJEU. Deux requetes strictement simultanees avec le meme
// K frais. Exigence : exactement UN 200 et UN 409, effectif +1 (pas +2).
// C'est le pattern check-then-act du bug historique des codes courts ; ici
// l'autorite est la contrainte PRIMARY KEY de tokens_consommes.
const p5 = await preparerVote(DEP_A, jetonsA[2], pkA);
const [r5a, r5b] = await Promise.all([voter(p5), voter(p5)]);
const statuts5 = [r5a.status, r5b.status].sort();
check('T5 course: exactement un 200 et un 409',
  statuts5[0] === 200 && statuts5[1] === 409, `statuts=${statuts5}`);

// T6 : CONFUSION DE DEPARTEMENT. Signature valide emise pour DEP_A, mais le
// champ departement du payload annonce DEP_B (qui existe, cle differente).
// La verification DOIT se faire sous la cle de DEP_B -> 403. Aucun chemin ou
// la verif et le comptage utiliseraient des departements differents.
const p6 = await preparerVote(DEP_A, jetonsA[3], pkA);
const v6 = await voter({ ...p6, departement: DEP_B });
check('T6 signature DepA + departement DepB refusee (403)', v6.status === 403,
  `status=${v6.status}`);
// ... et le vrai vote DEP_A avec ce K doit toujours passer (K non consomme par le 403).
const v6b = await voter(p6);
check('T6bis le K refuse en DepB reste utilisable en DepA (200)', v6b.status === 200);

// T7 : DOS KEYGEN FERME. Un departement jamais cree par le RH -> 404 sur
// /api/cle_publique ET sur /api/repondre, et surtout AUCUNE cle n'est creee
// (le second appel renvoie encore 404, pas 200).
const bidon = 'dep_inexistant_' + toHex(crypto.getRandomValues(new Uint8Array(8)));
const k1 = await fetch(`${BASE}/api/cle_publique?departement=${bidon}`);
const k2 = await fetch(`${BASE}/api/cle_publique?departement=${bidon}`);
const v7 = await voter({ ...p1, departement: bidon });
check('T7 departement inconnu -> 404, aucune cle creee',
  k1.status === 404 && k2.status === 404 && v7.status === 404,
  `get1=${k1.status}, get2=${k2.status}, vote=${v7.status}`);

const ok = resultats.every(Boolean);
console.log(ok
  ? '\n=== BRIQUE 7 v2 VALIDEE : survie 422, course, departement croise, keygen ferme ==='
  : '\n### ECHEC brique 7 v2');
process.exit(ok ? 0 : 1);
