// ============================================================================
// harnais_interop.mjs -- Squelette du test d'interoperabilite RSABSSA Rust<->JS
// Objectif : prouver que le flux
//   aveugler(JS) -> signer(Rust) -> finaliser(JS) -> verifier(JS)
// fonctionne, avec la MEME variante SHA384-PSS-Randomized des deux cotes.
//
// STRUCTURE PRETE. Les etapes crypto sensibles (marquees TODO) sont a remplir
// a tete reposee -- c'est la que se joue l'alignement des octets/DER.
// ============================================================================

import { RSABSSA } from '@cloudflare/blindrsa-ts';

const suite = RSABSSA.SHA384.PSS.Randomized();

// ----------------------------------------------------------------------------
// ETAPE 0 -- Recuperer la cle publique du serveur (format DER, cote Rust)
// ----------------------------------------------------------------------------
// Le serveur VERA expose sa cle publique en DER (PublicKeySha384PSSRandomized).
// La lib JS attend un objet CryptoKey (WebCrypto). Le pont = convertir.
//
// TODO(demain) : recuperer la cle publique DER du serveur.
//   Option A : via un endpoint /api/cle_publique (a creer cote serveur).
//   Option B : pour le test isole, exporter une cle depuis vera_blind_sig
//              (generer_cles) et la passer ici en base64.
// TODO(demain) : convertir DER -> CryptoKey via crypto.subtle.importKey(
//   'spki', derBytes, {name:'RSA-PSS', hash:'SHA-384'}, true, ['verify']).
async function chargerClePublique() {
    // PLACEHOLDER : a remplir demain
    throw new Error('TODO: charger la cle publique DER du serveur et convertir en CryptoKey');
}

// ----------------------------------------------------------------------------
// ETAPE 1 -- Cote CLIENT (JS) : preparer + aveugler le message
// ----------------------------------------------------------------------------
async function aveuglerCoteClient(publicKey, messageTexte) {
    const msg = new TextEncoder().encode(messageTexte);
    const prepared = suite.prepare(msg);            // prepare(msg) -> 1 arg
    const { blindedMsg, inv } = await suite.blind(publicKey, prepared); // blind -> 2 args
    return { prepared, blindedMsg, inv };
}

// ----------------------------------------------------------------------------
// ETAPE 2 -- Cote SERVEUR (Rust) : signer le message aveugle
// ----------------------------------------------------------------------------
// C'est la SEULE etape qui reste cote serveur. Le serveur recoit blindedMsg,
// appelle vera_blind_sig.signer_aveugle(cle_privee, blindedMsg), renvoie la
// signature aveugle. Il ne voit JAMAIS le message final ni la signature finale.
//
// TODO(demain) : appeler le serveur Rust. Pour le test isole, on peut appeler
//   vera_blind_sig depuis Python via un petit script, ou exposer un endpoint.
async function signerCoteServeur(blindedMsg) {
    // PLACEHOLDER : a remplir demain (pont vers vera_blind_sig Rust)
    throw new Error('TODO: envoyer blindedMsg au serveur Rust, recevoir blindSignature');
}

// ----------------------------------------------------------------------------
// ETAPE 3 -- Cote CLIENT (JS) : finaliser (definaliser) la signature
// ----------------------------------------------------------------------------
async function finaliserCoteClient(publicKey, prepared, inv, blindSignature) {
    // finalize(publicKey, preparedMsg, inv, blindSignature) -> 4 args
    const signature = await suite.finalize(publicKey, prepared, inv, blindSignature);
    return signature;
}

// ----------------------------------------------------------------------------
// ETAPE 4 -- Verification : le token final est-il valide ?
// ----------------------------------------------------------------------------
async function verifier(publicKey, signature, messageTexte) {
    const msg = new TextEncoder().encode(messageTexte);
    // verify(publicKey, signature, message) -> 3 args
    return await suite.verify(publicKey, signature, msg);
}

// ----------------------------------------------------------------------------
// ORCHESTRATION -- le flux complet (a activer demain une fois les TODO remplis)
// ----------------------------------------------------------------------------
async function main() {
    console.log('=== Test interop RSABSSA Rust<->JS ===');
    console.log('Structure prete. Etapes crypto a remplir (voir TODO).');
    console.log('');
    console.log('Flux cible :');
    console.log('  0. charger cle publique serveur (DER -> CryptoKey)');
    console.log('  1. [JS]   preparer + aveugler le message');
    console.log('  2. [Rust] signer le message aveugle (seule etape serveur)');
    console.log('  3. [JS]   finaliser -> token complet');
    console.log('  4. [JS]   verifier -> doit etre valide');
    console.log('');
    console.log('Point critique demain : alignement DER (Rust) <-> CryptoKey (JS)');
    console.log('et format des octets entre les deux libs.');

    // TODO(demain) : decommenter une fois les fonctions remplies
    // const pk = await chargerClePublique();
    // const { prepared, blindedMsg, inv } = await aveuglerCoteClient(pk, 'test-vote');
    // const blindSig = await signerCoteServeur(blindedMsg);
    // const signature = await finaliserCoteClient(pk, prepared, inv, blindSig);
    // const valide = await verifier(pk, signature, 'test-vote');
    // console.log('Signature valide :', valide);
}

main().catch(e => { console.error('Erreur:', e.message); process.exit(1); });
