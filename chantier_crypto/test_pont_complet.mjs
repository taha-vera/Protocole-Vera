// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
import { RSABSSA } from '@cloudflare/blindrsa-ts';
import { execFileSync } from 'child_process';
const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));

const login = await fetch(`${BASE}/api/rh/connexion`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identifiant:'asso_acer', mot_de_passe:(process.env.VERA_TEST_PASS || 'test1234')})});
const cookie = login.headers.get('set-cookie');
const gen = await fetch(`${BASE}/api/rh/generer_autorisations`, {method:'POST', headers:{'Content-Type':'application/json','Cookie':cookie}, body:JSON.stringify({departement:'PontTest', quantite:1})});
const jeton = (await gen.json()).autorisations[0].jeton;

const rPk = await fetch(`${BASE}/api/cle_publique?departement=PontTest`);
const { cle_publique_hex } = await rPk.json();
const publicKey = await crypto.subtle.importKey('spki', fromHex(cle_publique_hex), {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']);

const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);

const rSig = await fetch(`${BASE}/api/signer_aveugle`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})});
const sigData = await rSig.json();
const signature = await suite.finalize(publicKey, prepared, inv, fromHex(sigData.signature_aveugle_hex));

const randomizer = prepared.slice(0, 32);
const Kmsg = prepared.slice(32);
console.log('K == Kmsg extrait:', toHex(K) === toHex(Kmsg));

const res = execFileSync('/root/vera_blind_sig/.venv/bin/python3',
  ['/tmp/test_pont.py', cle_publique_hex, toHex(Kmsg), toHex(signature), toHex(randomizer)],
  {encoding:'utf8'});
console.log(res.trim());
console.log(res.includes('True') ? '\n=== PONT JS->RUST VALIDE : le serveur verifie la signature du client ===' : '\n### ECHEC PONT');
