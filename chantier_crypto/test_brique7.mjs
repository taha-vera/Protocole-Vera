// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
import { RSABSSA } from '@cloudflare/blindrsa-ts';
const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));
const DEP = 'Brique7Test';

const login = await fetch(`${BASE}/api/rh/connexion`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identifiant:'asso_acer', mot_de_passe:(process.env.VERA_TEST_PASS || 'test1234')})});
const cookie = login.headers.get('set-cookie');
const gen = await fetch(`${BASE}/api/rh/generer_autorisations`, {method:'POST', headers:{'Content-Type':'application/json','Cookie':cookie}, body:JSON.stringify({departement:DEP, quantite:1})});
const jeton = (await gen.json()).autorisations[0].jeton;

const rPk = await fetch(`${BASE}/api/cle_publique?departement=${DEP}`);
const publicKey = await crypto.subtle.importKey('spki', fromHex((await rPk.json()).cle_publique_hex), {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']);

const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);
const rSig = await fetch(`${BASE}/api/signer_aveugle`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})});
const sigData = await rSig.json();
const signature = await suite.finalize(publicKey, prepared, inv, fromHex(sigData.signature_aveugle_hex));

const randomizer = prepared.slice(0, 32);
const Kmsg = prepared.slice(32);
const votePayload = {K_hex:toHex(Kmsg), randomizer_hex:toHex(randomizer), signature_hex:toHex(signature), reponse:'oui', departement:sigData.departement};

const v1 = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(votePayload)});
console.log('1. vote accepte (200):', v1.status, await v1.text());

const v2 = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(votePayload)});
console.log('2. rejeu meme K refuse (409):', v2.status === 409);

const badRep = {...votePayload, reponse:'bidon'};
const v3 = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(badRep)});
console.log('3. reponse invalide refusee (422):', v3.status === 422);

const badSig = {...votePayload, K_hex:toHex(crypto.getRandomValues(new Uint8Array(32)))};
const v4 = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(badSig)});
console.log('4. signature invalide refusee (403):', v4.status === 403);

const ok = v1.status === 200 && v2.status === 409 && v3.status === 422 && v4.status === 403;
console.log(ok ? '\n=== BRIQUE 7 VALIDEE : vote Modele B bout-en-bout ===' : '\n### ECHEC brique 7');
