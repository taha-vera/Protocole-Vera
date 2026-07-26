// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
import { RSABSSA } from '@cloudflare/blindrsa-ts';
const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));

const login = await fetch(`${BASE}/api/rh/connexion`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identifiant:'asso_acer', mot_de_passe:(process.env.VERA_TEST_PASS || 'test1234')})});
const cookie = login.headers.get('set-cookie');
const gen = await fetch(`${BASE}/api/rh/generer_autorisations`, {method:'POST', headers:{'Content-Type':'application/json','Cookie':cookie}, body:JSON.stringify({departement:'FragTest', quantite:1})});
const lien = (await gen.json()).autorisations[0].lien_sms;
console.log('LIEN:', lien);
console.log('rien en query string:', !lien.includes('?'));

const frag = new URLSearchParams(new URL(lien).hash.slice(1));
const jeton = frag.get('a'), dep = frag.get('d'), emp = frag.get('k');
console.log('parse fragment -> dept:', dep, '| empreinte:', emp.slice(0,12));

const rPk = await fetch(`${BASE}/api/cle_publique?departement=${encodeURIComponent(dep)}`);
const pk = await rPk.json();
console.log('empreinte cle == k du fragment:', pk.empreinte_sha256 === emp);
const publicKey = await crypto.subtle.importKey('spki', fromHex(pk.cle_publique_hex), {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']);

const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);
const rSig = await fetch(`${BASE}/api/signer_aveugle`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})});
const sd = await rSig.json();
const signature = await suite.finalize(publicKey, prepared, inv, fromHex(sd.signature_aveugle_hex));
const rVote = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({K_hex:toHex(prepared.slice(32)), randomizer_hex:toHex(prepared.slice(0,32)), signature_hex:toHex(signature), reponse:'oui', departement:sd.departement})});
console.log('VOTE:', rVote.status, await rVote.text());
console.log(rVote.status === 200 && !lien.includes('?') ? '\n=== FRAGMENT VALIDE : rien en query, vote OK ===' : '\n### ECHEC');
