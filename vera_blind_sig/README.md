# vera_blind_sig -- primitive de signature aveugle

Module Python natif (Rust + PyO3) qui expose la signature aveugle **RSABSSA
(RFC 9474)** au reste de VERA.

## Pourquoi ce module est publie

VERA revendique un anonymat **prouve**, pas promis. Cette revendication repose
entierement sur deux proprietes assurees par ce module :

- **non-liaison (unlinkability)** : le serveur signe un message qu'il ne voit
  pas, il ne peut donc pas relier une signature finalisee au jeton
  d'autorisation qui a permis de l'obtenir ;
- **infalsifiabilite** : une signature ne peut pas etre forgee sans la cle
  privee, ce qui empeche le bourrage.

Tant que ce module n'etait pas publie, un auditeur pouvait verifier tout le
reste du systeme sauf le maillon qui porte la preuve -- ce qui revenait a dire
« prouve, sauf a cet endroit, ou il faut me croire ». Un audit externe l'a
signale le 01/08/2026 ; c'est corrige par cette publication.

## Ce que ce module fait, et ce qu'il ne fait pas

**Il ne contient AUCUNE cryptographie ecrite pour VERA.** Les 91 lignes de
`src/lib.rs` sont de la glue : elles deserialisent du DER, appellent la
bibliotheque, reserialisent. Toutes les operations sensibles (generation de
cles, aveuglement, signature, finalisation, verification) sont deleguees a
[`blind-rsa-signatures`](https://crates.io/crates/blind-rsa-signatures)
version 0.17, bibliotheque publique et auditable independamment.

La variante RFC 9474 utilisee est fixee **par le systeme de types Rust** et non
par un parametre d'execution : `PublicKeySha384PSSRandomized` /
`SecretKeySha384PSSRandomized`, soit **RSABSSA-SHA384-PSS-Randomized**, modules
de 2048 bits. Il est donc impossible de melanger accidentellement deux
variantes incompatibles.

## Fonctions exposees

| Fonction | Role | Appelee par |
|---|---|---|
| `generer_cles()` | Paire RSA 2048 bits, renvoyee en DER | Serveur, a l'ouverture d'une consultation |
| `signer_aveugle(sk_der, message_aveugle)` | Signe un message **deja aveugle** | Serveur (`/api/signer_aveugle`) |
| `aveugler_message(pk_der, message)` | Aveugle un message, renvoie (aveugle, secret, randomizer) | Tests ; en production c'est le **navigateur** qui aveugle |
| `finaliser_signature(...)` | Definalise une signature aveugle | Tests ; en production c'est le navigateur |
| `verifier_signature(pk_der, message, signature, randomizer)` | Verifie une signature finalisee | Serveur (`/api/repondre`) |

En production, l'aveuglement et la finalisation sont faits **dans le navigateur
du votant** (`static/vote.html`, bibliotheque `@cloudflare/blindrsa-ts`, meme
variante RFC 9474). Le serveur n'execute que `generer_cles`, `signer_aveugle`
et `verifier_signature` : il ne voit jamais le message en clair avant son
depot, ni le secret d'aveuglement.

## Compiler et verifier

Prerequis : Rust stable, Python 3.11+, `maturin`.

```bash
cd vera_blind_sig
pip install maturin
maturin build --release
pip install target/wheels/vera_blind_sig-*.whl
```

`Cargo.lock` est versionne deliberement : il fige les versions exactes de
toutes les dependances transitives, de sorte qu'une recompilation produise la
meme chaine de dependances que celle utilisee en production.

Verification rapide apres installation :

```python
import vera_blind_sig as vbs

sk, pk = vbs.generer_cles()
message = b"test"
aveugle, secret, randomizer = vbs.aveugler_message(pk, message)
sig_aveugle = vbs.signer_aveugle(sk, aveugle)
signature = vbs.finaliser_signature(pk, message, aveugle, secret, sig_aveugle, randomizer)

assert vbs.verifier_signature(pk, message, signature, randomizer) is True
assert vbs.verifier_signature(pk, b"autre", signature, randomizer) is False
print("OK : signature aveugle fonctionnelle, message modifie rejete")
```

## Note de conception

`verifier_signature` renvoie `False` sur toute erreur (`.is_ok()`), sans
distinguer « signature invalide » de « cle illisible ». C'est volontaire et
sans consequence : l'appelant refuse le vote dans les deux cas. Le diagnostic
fin appartient aux couches superieures, qui disposent du contexte.

Le `msg_randomizer` est valide strictement (32 octets exactement, erreur
explicite sinon) plutot que tronque silencieusement.

## Dependance et licence

- `blind-rsa-signatures` 0.17 -- implementation RFC 9474
- `pyo3` 0.22 -- interface Python

Voir la licence du depot principal.
