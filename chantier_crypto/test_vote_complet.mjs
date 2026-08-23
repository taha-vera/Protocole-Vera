import { RSABSSA } from '@cloudflare/blindrsa-ts';
const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));

// RH cree un jeton (simule le lien SMS)
const login = await fetch(`${BASE}/api/rh/connexion`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identifiant:'asso_acer', mot_de_passe:'test1234'})});
const cookie = login.headers.get('set-cookie');
const gen = await fetch(`${BASE}/api/rh/generer_autorisations`, {method:'POST', headers:{'Content-Type':'application/json','Cookie':cookie}, body:JSON.stringify({departement:'VoteFinal', quantite:1})});
const genData = await gen.json();
const lien = genData.autorisations[0].lien_sms;
console.log('lien SMS:', lien);

// --- LE CLIENT (vote.html) parse le lien ---
const url = new URL(lien);
const jeton = url.searchParams.get('a');
const departement = url.searchParams.get('d');
const empreinteAttendue = url.hash.replace('#k=', '');
console.log('parse -> jeton, dep:', departement, ', empreinte:', empreinteAttendue.slice(0,12));

// 1. Cle du departement
const rPk = await fetch(`${BASE}/api/cle_publique?departement=${encodeURIComponent(departement)}`);
const { cle_publique_hex, empreinte_sha256 } = await rPk.json();
// 2. BRIQUE 6: verif empreinte
console.log('BRIQUE 6 - empreinte cle == #k= du lien:', empreinte_sha256 === empreinteAttendue);
if (empreinte_sha256 !== empreinteAttendue) { console.log('### ARRET: empreinte non conforme'); process.exit(1); }

const publicKey = await crypto.subtle.importKey('spki', fromHex(cle_publique_hex), {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']);
const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);
const rSig = await fetch(`${BASE}/api/signer_aveugle`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})});
const sigData = await rSig.json();
const signature = await suite.finalize(publicKey, prepared, inv, fromHex(sigData.signature_aveugle_hex));
const randomizer = prepared.slice(0,32);
const Kmsg = prepared.slice(prepared.length-32);

// 3. VOTER
const rVote = await fetch(`${BASE}/api/repondre`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({K_hex:toHex(Kmsg), randomizer_hex:toHex(randomizer), signature_hex:toHex(signature), reponse:'oui', departement:sigData.departement})});
console.log('VOTE:', rVote.status, await rVote.text());

console.log(rVote.status === 200 && empreinte_sha256 === empreinteAttendue
  ? '\n=== FLUX CLIENT COMPLET VALIDE (lien -> brique6 -> vote) ===' : '\n### ECHEC');
