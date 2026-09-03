use blind_rsa_signatures::{DefaultRng, KeyPair, Randomized, Sha384, PSS};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::Bound;

#[pyfunction]
fn generer_cles() -> PyResult<(Vec<u8>, Vec<u8>)> {
    let kp = KeyPair::<Sha384, PSS, Randomized>::generate(&mut DefaultRng, 2048)
        .map_err(|e| PyValueError::new_err(format!("Erreur generation cles: {e}")))?;
    let sk_der = kp.sk.to_der()
        .map_err(|e| PyValueError::new_err(format!("Erreur export cle privee: {e}")))?;
    let pk_der = kp.pk.to_der()
        .map_err(|e| PyValueError::new_err(format!("Erreur export cle publique: {e}")))?;
    Ok((sk_der, pk_der))
}

#[pyfunction]
fn signer_aveugle(cle_privee_der: Vec<u8>, message_aveugle: Vec<u8>) -> PyResult<Vec<u8>> {
    let sk = blind_rsa_signatures::SecretKeySha384PSSRandomized::from_der(&cle_privee_der)
        .map_err(|e| PyValueError::new_err(format!("Cle privee invalide: {e}")))?;
    let blind_sig = sk.blind_sign(&message_aveugle)
        .map_err(|e| PyValueError::new_err(format!("Erreur signature aveugle: {e}")))?;
    Ok(blind_sig.into())
}

#[pyfunction]
fn aveugler_message(cle_publique_der: Vec<u8>, message: Vec<u8>) -> PyResult<(Vec<u8>, Vec<u8>, Vec<u8>)> {
    let pk = blind_rsa_signatures::PublicKeySha384PSSRandomized::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique invalide: {e}")))?;
    let resultat = pk.blind(&mut DefaultRng, &message)
        .map_err(|e| PyValueError::new_err(format!("Erreur aveuglement: {e}")))?;
    // unwrap_or_default() rend un vecteur VIDE si le crate ne produit pas de
    // randomizer. finaliser_signature en exige alors exactement 32 octets et
    // refuse -- mais l'echec surviendrait APRES que le serveur a signe et
    // consomme le jeton : le votant perdrait sa voix sans recours.
    //
    // Le type Randomized (voir generer_cles) garantit sa presence : le cas ne
    // peut pas se produire tant que ce parametre de type ne change pas. C'est
    // une fragilite de forme, relevee lors de la premiere lecture de ce fichier
    // le 03/09/2026 -- dix audits l'avaient laisse dans leurs angles morts,
    // faute de chaine Rust.
    //
    // Si le type devait changer, echouer ICI plutot qu'a la finalisation : le
    // jeton n'est pas encore consomme a ce stade.
    let randomizer_bytes: Vec<u8> = resultat.msg_randomizer.map(|r| r.0.to_vec()).unwrap_or_default();
    Ok((resultat.blind_message.into(), resultat.secret.into(), randomizer_bytes))
}

#[pyfunction]
fn finaliser_signature(
    cle_publique_der: Vec<u8>,
    message: Vec<u8>,
    blind_message: Vec<u8>,
    secret: Vec<u8>,
    signature_aveugle: Vec<u8>,
    msg_randomizer: Vec<u8>,
) -> PyResult<Vec<u8>> {
    let pk = blind_rsa_signatures::PublicKeySha384PSSRandomized::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique invalide: {e}")))?;
    if msg_randomizer.len() != 32 {
        return Err(PyValueError::new_err(format!("msg_randomizer doit faire 32 octets, recu: {}", msg_randomizer.len())));
    }
    let mut randomizer_array = [0u8; 32];
    randomizer_array.copy_from_slice(&msg_randomizer);
    let blinding_result = blind_rsa_signatures::BlindingResult {
        blind_message: blind_message.into(),
        secret: secret.into(),
        msg_randomizer: Some(blind_rsa_signatures::MessageRandomizer(randomizer_array)),
    };
    let blind_sig: blind_rsa_signatures::BlindSignature = signature_aveugle.into();
    let signature = pk.finalize(&blind_sig, &blinding_result, &message)
        .map_err(|e| PyValueError::new_err(format!("Erreur finalisation: {e}")))?;
    Ok(signature.into())
}

#[pyfunction]
fn verifier_signature(
    cle_publique_der: Vec<u8>,
    message: Vec<u8>,
    signature: Vec<u8>,
    msg_randomizer: Vec<u8>,
) -> PyResult<bool> {
    let pk = blind_rsa_signatures::PublicKeySha384PSSRandomized::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique invalide: {e}")))?;
    if msg_randomizer.len() != 32 {
        return Err(PyValueError::new_err(format!("msg_randomizer doit faire 32 octets, recu: {}", msg_randomizer.len())));
    }
    let mut randomizer_array = [0u8; 32];
    randomizer_array.copy_from_slice(&msg_randomizer);
    let randomizer = blind_rsa_signatures::MessageRandomizer(randomizer_array);
    let sig: blind_rsa_signatures::Signature = signature.into();
    Ok(pk.verify(&sig, Some(randomizer), &message).is_ok())
}

// Une exploration de RSAPBSSA (signature partiellement aveugle, RFC 9474 §5)
// a occupe cette place jusqu'au 16/08. Elle fonctionnait cote serveur mais
// n'est pas deployable : Chrome refuse d'importer une cle dont l'exposant
// public depasse la taille standard, ce que la derivation RSAPBSSA produit
// necessairement. Firefox l'accepte, ce qui montre qu'il s'agit d'une
// restriction d'implementation et non de la specification.
//
// Le code a ete retire plutot que conserve. Du code mort dans un module
// cryptographique invite l'erreur de lecture : un auditeur peut croire actif
// un chemin qui ne l'est pas. Le meme principe avait ete applique au client
// JavaScript ; il valait aussi ici.
//
// L'exploration complete, avec la mesure des navigateurs et les six pieges
// rencontres, est conservee dans LIMITS.md, section 8 (historique).

#[pymodule]
fn vera_blind_sig(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generer_cles, m)?)?;
    m.add_function(wrap_pyfunction!(signer_aveugle, m)?)?;
    m.add_function(wrap_pyfunction!(aveugler_message, m)?)?;
    m.add_function(wrap_pyfunction!(finaliser_signature, m)?)?;
    m.add_function(wrap_pyfunction!(verifier_signature, m)?)?;
    Ok(())
}
