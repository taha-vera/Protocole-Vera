use blind_rsa_signatures::pbrsa::{PartiallyBlindKeyPair, PartiallyBlindPublicKey, PartiallyBlindSecretKey};
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

// ---------------------------------------------------------------------------
// RSAPBSSA -- signature aveugle PARTIELLE (metadonnee publique).
//
// Difference avec les fonctions ci-dessus : une SEULE paire de cles pour toute
// la consultation, et la cle de chaque departement s'en DERIVE de facon
// deterministe a partir du nom du departement. Le modulus reste le meme, seul
// l'exposant change : e2 = H(n, metadonnee).
//
// Ce que cela change pour le votant. Aujourd'hui il recoit la cle publique de
// son departement du serveur, et compare son empreinte a celle inscrite dans
// son lien -- empreinte que le serveur a lui-meme calculee. Elle ne l'engage
// donc pas : un serveur malveillant genere une cle par personne avec
// l'empreinte correspondante, le controle passe, et au depouillement il
// retrouve qui a produit quelle signature.
//
// Avec la derivation, le votant RECALCULE la cle de son departement a partir
// du modulus maitre et du nom du groupe. Fabriquer une cle par personne
// devient impossible : elle ne correspondrait a aucune metadonnee legitime.
// Et il n'y a plus qu'UNE valeur a publier -- 294 octets -- au lieu d'une
// liste de cles.
//
// Verifie par maquette avant integration : les urnes restent separees (une
// signature obtenue pour un departement ne verifie pas sous un autre), la
// derivation est deterministe, le flux complet aboutit.
//
// Ces fonctions coexistent avec les precedentes pendant la migration : la
// production continue de tourner sur RSABSSA tant que la bascule n'est pas
// faite.
// ---------------------------------------------------------------------------

#[pyfunction]
fn pb_generer_cles() -> PyResult<(Vec<u8>, Vec<u8>)> {
    // Une seule paire pour toute la consultation, tous departements confondus.
    //
    // BOUCLE DE REGENERATION : le produit de deux premiers de 1024 bits fait
    // tantot 2047 bits, tantot 2048. Le DER encode alors 255 ou 256 octets.
    // Le client JavaScript (@cloudflare/blindrsa-ts) deduit la taille du
    // modulus de cet encodage et echoue avec « number does not fit in 255
    // bytes » des que l'arithmetique demande l'octet manquant.
    //
    // On rejette donc les paires trop courtes. Mesure : environ une sur deux,
    // donc 43 secondes en moyenne au lieu de 21. C'est le prix d'une
    // interoperabilite fiable entre deux bibliotheques independantes.
    let mut kp;
    loop {
        kp = PartiallyBlindKeyPair::<Sha384, PSS, Randomized>::generate(&mut DefaultRng, 2048)
            .map_err(|e| PyValueError::new_err(format!("Erreur generation cles PB: {e}")))?;
        let der = kp.pk.to_der()
            .map_err(|e| PyValueError::new_err(format!("Erreur export: {e}")))?;
        if der.len() == 294 {
            break;
        }
    }
    let sk_der = kp.sk.to_der()
        .map_err(|e| PyValueError::new_err(format!("Erreur export cle privee PB: {e}")))?;
    let pk_der = kp.pk.to_der()
        .map_err(|e| PyValueError::new_err(format!("Erreur export cle publique PB: {e}")))?;
    Ok((sk_der, pk_der))
}

#[pyfunction]
fn pb_deriver_cle_publique(cle_publique_der: Vec<u8>, metadonnee: Vec<u8>) -> PyResult<Vec<u8>> {
    // Deterministe : appelee par le serveur ET par le client, elle donne le
    // meme resultat. C'est ce qui permet au votant de ne pas faire confiance
    // a la cle qu'on lui envoie.
    let pk = PartiallyBlindPublicKey::<Sha384, PSS, Randomized>::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique PB invalide: {e}")))?;
    let derivee = pk.derive_public_key_for_metadata(&metadonnee)
        .map_err(|e| PyValueError::new_err(format!("Erreur derivation: {e}")))?;
    let der = derivee.to_der()
        .map_err(|e| PyValueError::new_err(format!("Erreur export cle derivee: {e}")))?;
    Ok(der)
}

#[pyfunction]
fn pb_signer_aveugle(
    cle_privee_der: Vec<u8>,
    cle_publique_der: Vec<u8>,
    message_aveugle: Vec<u8>,
    metadonnee: Vec<u8>,
) -> PyResult<Vec<u8>> {
    // blind_sign ne prend pas de metadonnee : c'est la CLE qui la porte. On
    // derive donc la cle secrete du departement avant de signer. Le serveur
    // connait deja ce departement -- il vient de consommer le jeton
    // d'autorisation qui l'indique -- donc rien de nouveau ne lui est revele.
    // derive_secret_key_for_metadata appartient a la PAIRE, pas a la cle
    // secrete seule : la derivation a besoin des facteurs premiers. Le serveur
    // doit donc conserver les deux moities et les reassembler ici.
    let sk = PartiallyBlindSecretKey::<Sha384, PSS, Randomized>::from_der(&cle_privee_der)
        .map_err(|e| PyValueError::new_err(format!("Cle privee PB invalide: {e}")))?;
    let pk = PartiallyBlindPublicKey::<Sha384, PSS, Randomized>::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique PB invalide: {e}")))?;
    let kp = PartiallyBlindKeyPair { pk, sk };
    let sk_derivee = kp.derive_secret_key_for_metadata(&metadonnee)
        .map_err(|e| PyValueError::new_err(format!("Erreur derivation cle privee: {e}")))?;
    let blind_sig = sk_derivee.blind_sign(&message_aveugle)
        .map_err(|e| PyValueError::new_err(format!("Erreur signature aveugle PB: {e}")))?;
    Ok(blind_sig.into())
}

#[pyfunction]
fn pb_aveugler_message(
    cle_publique_der: Vec<u8>,
    message: Vec<u8>,
    metadonnee: Vec<u8>,
) -> PyResult<(Vec<u8>, Vec<u8>, Vec<u8>)> {
    // ORDRE IMPORTANT : deriver AVANT d'aveugler. Aveugler sous la cle
    // maitresse produit une signature que la finalisation rejette -- c'est le
    // piege rencontre lors de la maquette.
    let pk = PartiallyBlindPublicKey::<Sha384, PSS, Randomized>::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique PB invalide: {e}")))?;
    let pk_derivee = pk.derive_public_key_for_metadata(&metadonnee)
        .map_err(|e| PyValueError::new_err(format!("Erreur derivation: {e}")))?;
    let resultat = pk_derivee.blind(&mut DefaultRng, &message, Some(&metadonnee))
        .map_err(|e| PyValueError::new_err(format!("Erreur aveuglement PB: {e}")))?;
    let randomizer_bytes: Vec<u8> =
        resultat.msg_randomizer.map(|r| r.0.to_vec()).unwrap_or_default();
    Ok((resultat.blind_message.into(), resultat.secret.into(), randomizer_bytes))
}

#[pyfunction]
fn pb_finaliser_signature(
    cle_publique_der: Vec<u8>,
    message: Vec<u8>,
    blind_message: Vec<u8>,
    secret: Vec<u8>,
    signature_aveugle: Vec<u8>,
    msg_randomizer: Vec<u8>,
    metadonnee: Vec<u8>,
) -> PyResult<Vec<u8>> {
    let pk = PartiallyBlindPublicKey::<Sha384, PSS, Randomized>::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique PB invalide: {e}")))?;
    let pk_derivee = pk.derive_public_key_for_metadata(&metadonnee)
        .map_err(|e| PyValueError::new_err(format!("Erreur derivation: {e}")))?;
    if msg_randomizer.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "msg_randomizer doit faire 32 octets, recu: {}", msg_randomizer.len())));
    }
    let mut randomizer_array = [0u8; 32];
    randomizer_array.copy_from_slice(&msg_randomizer);
    let blinding_result = blind_rsa_signatures::BlindingResult {
        blind_message: blind_message.into(),
        secret: secret.into(),
        msg_randomizer: Some(blind_rsa_signatures::MessageRandomizer(randomizer_array)),
    };
    let blind_sig: blind_rsa_signatures::BlindSignature = signature_aveugle.into();
    let signature = pk_derivee
        .finalize(&blind_sig, &blinding_result, &message, Some(&metadonnee))
        .map_err(|e| PyValueError::new_err(format!("Erreur finalisation PB: {e}")))?;
    Ok(signature.into())
}

#[pyfunction]
fn pb_verifier_signature(
    cle_publique_der: Vec<u8>,
    message: Vec<u8>,
    signature: Vec<u8>,
    msg_randomizer: Vec<u8>,
    metadonnee: Vec<u8>,
) -> PyResult<bool> {
    // La metadonnee fait partie de ce qui est verifie : une signature obtenue
    // pour un departement ne vaut pas pour un autre. C'est ce qui remplace la
    // separation assuree aujourd'hui par des cles distinctes.
    let pk = PartiallyBlindPublicKey::<Sha384, PSS, Randomized>::from_der(&cle_publique_der)
        .map_err(|e| PyValueError::new_err(format!("Cle publique PB invalide: {e}")))?;
    let pk_derivee = pk.derive_public_key_for_metadata(&metadonnee)
        .map_err(|e| PyValueError::new_err(format!("Erreur derivation: {e}")))?;
    if msg_randomizer.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "msg_randomizer doit faire 32 octets, recu: {}", msg_randomizer.len())));
    }
    let mut randomizer_array = [0u8; 32];
    randomizer_array.copy_from_slice(&msg_randomizer);
    let randomizer = blind_rsa_signatures::MessageRandomizer(randomizer_array);
    let sig: blind_rsa_signatures::Signature = signature.into();
    Ok(pk_derivee
        .verify(&sig, Some(randomizer), &message, Some(&metadonnee))
        .is_ok())
}

#[pymodule]
fn vera_blind_sig(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generer_cles, m)?)?;
    m.add_function(wrap_pyfunction!(signer_aveugle, m)?)?;
    m.add_function(wrap_pyfunction!(aveugler_message, m)?)?;
    m.add_function(wrap_pyfunction!(finaliser_signature, m)?)?;
    m.add_function(wrap_pyfunction!(verifier_signature, m)?)?;
    // RSAPBSSA -- coexistent avec les precedentes pendant la migration.
    m.add_function(wrap_pyfunction!(pb_generer_cles, m)?)?;
    m.add_function(wrap_pyfunction!(pb_deriver_cle_publique, m)?)?;
    m.add_function(wrap_pyfunction!(pb_signer_aveugle, m)?)?;
    m.add_function(wrap_pyfunction!(pb_aveugler_message, m)?)?;
    m.add_function(wrap_pyfunction!(pb_finaliser_signature, m)?)?;
    m.add_function(wrap_pyfunction!(pb_verifier_signature, m)?)?;
    Ok(())
}
