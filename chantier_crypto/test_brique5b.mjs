// Mot de passe de test : lu depuis VERA_TEST_PASS, valeur de repli
// 'test1234' pour une instance locale jetable. NE JAMAIS y mettre le
// mot de passe de production -- un secret en dur dans le depot public a
// deja fuite le 21/07 et impose une purge d'historique.
import { RSABSSA } from '@cloudflare/blindrsa-ts';

const BASE = 'http://127.0.0.1:8020';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));

// 1. Login RH + generer un jeton d'autorisation (simule le RH)
const login = await fetch(`${BASE}/api/rh/connexion`, {
  method: 'POST', headers: {'Content-Type':'application/json'},
  body: JSON.stringify({identifiant:'asso_acer', mot_de_passe:(process.env.VERA_TEST_PASS || 'test1234')})
});
const cookie = login.headers.get('set-cookie');
console.log('1. login:', login.status);

const gen = await fetch(`${BASE}/api/rh/generer_autorisations`, {
  method: 'POST', headers: {'Content-Type':'application/json', 'Cookie':cookie},
  body: JSON.stringify({departement:'TestNode', quantite:1})
});
const genData = await gen.json();
const jeton = genData.autorisations[0].jeton;
const empreinteAttendue = genData.empreinte_cle;
console.log('2. jeton genere, empreinte:', empreinteAttendue.slice(0,16));

// --- A partir d'ici : ce que fait vote.html cote CLIENT ---

// 3. Recuperer la cle publique
const rPk = await fetch(`${BASE}/api/cle_publique?departement=TestNode`);
const { cle_publique_hex, empreinte_sha256 } = await rPk.json();
console.log('3. cle recue, empreinte correspond au lien:', empreinte_sha256 === empreinteAttendue);
const publicKey = await crypto.subtle.importKey('spki', fromHex(cle_publique_hex),
  {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']);

// 4. Generer K, aveugler
const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);
console.log('4. K aveugle:', blindedMsg.length, 'octets');

// 5. Demander la signature aveugle avec le jeton
const rSig = await fetch(`${BASE}/api/signer_aveugle`, {
  method: 'POST', headers: {'Content-Type':'application/json'},
  body: JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})
});
const sigData = await rSig.json();
console.log('5. signature aveugle recue, departement:', sigData.departement);

// 6. Finaliser
const signature = await suite.finalize(publicKey, prepared, inv, fromHex(sigData.signature_aveugle_hex));
console.log('6. signature finalisee:', signature.length, 'octets');

// 7. VERIFIER que la signature est valide sur K
const valide = await suite.verify(publicKey, signature, prepared);
console.log('7. signature VALIDE sur K:', valide);

// 8. Rejouer le meme jeton -> doit etre refuse (403)
const rSig2 = await fetch(`${BASE}/api/signer_aveugle`, {
  method: 'POST', headers: {'Content-Type':'application/json'},
  body: JSON.stringify({jeton_autorisation:jeton, message_aveugle_hex:toHex(blindedMsg)})
});
console.log('8. rejeu du jeton refuse (403 attendu):', rSig2.status === 403);

console.log(valide && sigData.departement === 'TestNode' && rSig2.status === 403
  ? '\n=== BRIQUE 5b LOGIQUE VALIDEE ===' : '\n### ECHEC');
