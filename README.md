# VERA Consultation

**Agrégation à confidentialité différentielle, non-persistante.**

VERA publie le résultat collectif d'une consultation sensible sans jamais rendre
lisible la contribution d'un individu — ni pour l'organisateur, ni pour
l'hébergeur, ni pour un tiers.

- Confidentialité différentielle à ε = 0,5 (OpenDP)
- Signatures aveugles RSABSSA — RFC 9474, aveuglement et finalisation dans le
  navigateur du votant
- Aucune persistance du lien identité → réponse
- Modèle de menace public : **26 portes, 21 fermées avec preuve reproductible,
  5 limites assumées**

> ⚠️ **VERA n'est pas conçu pour un scrutin contraignant ou juridiquement
> opposable.** Il ne peut pas vérifier que les invitations sont parties aux
> bonnes personnes, et à elles seules. Voir
> [Ce qui reste de votre responsabilité](#ce-qui-reste-de-votre-responsabilité).

---

## Sommaire

- [Est-ce que VERA répond à votre besoin ?](#est-ce-que-vera-répond-à-votre-besoin-)
- [La garantie, et ce sur quoi elle repose](#la-garantie-et-ce-sur-quoi-elle-repose)
- [Déploiement](#déploiement)
- [Vérifier une installation](#vérifier-une-installation)
- [Ce qui reste de votre responsabilité](#ce-qui-reste-de-votre-responsabilité)
- [Règles d'usage](#règles-dusage)
- [Limites assumées](#limites-assumées)
- [Documentation](#documentation)
- [Sécurité](#sécurité)
- [État du projet et contributions](#état-du-projet-et-contributions)
- [Citer VERA](#citer-vera)
- [Licence](#licence)

---

## Est-ce que VERA répond à votre besoin ?

VERA convient si les quatre conditions suivantes sont réunies.

| Condition | Seuil | Pourquoi |
|---|---|---|
| Effectif du groupe consulté | **≥ 240 réponses** | En dessous, le bruit rend le résultat inexploitable. VERA refuse alors de publier — pas de version dégradée. |
| Fenêtre de collecte | ≤ 7 jours | Les clés de signature sont détruites automatiquement à l'expiration. |
| Hébergement | par un tiers **distinct** de l'organisation qui consulte | C'est la condition de la garantie, pas une précaution. |
| Portée du résultat | consultatif | VERA ne garantit pas l'intégrité du corps électoral. |

**240 réponses, pas 240 invitations.** À un taux de participation réaliste de
50 à 60 %, il faut compter **450 à 500 invités par groupe**. Une organisation de
600 personnes ne peut donc publier qu'un seul résultat d'ensemble : découper par
service produirait des groupes dont aucun n'atteindrait le seuil.

**Public visé :** grandes entreprises et groupes, fonction publique, hôpitaux,
universités, syndicats de branche, associations de grande taille.

Les structures plus petites ne peuvent pas obtenir un résultat à la fois anonyme
et suffisamment précis à ε = 0,5. C'est une contrainte mathématique, pas un choix
de conception.

### Précision réelle (mesurée le 14/07/2026)

Erreur maximale sur trois options — 95ᵉ centile, pire répartition, 3000
simulations, avec projection sur le simplexe :

| Effectif | Erreur max |
|---|---|
| 100 | 12 % |
| 150 | 8 % |
| 200 | 6 % |
| **240** | **5 %** ← seuil de publication |
| 300 | 4 % |
| 500 | 2,5 % |

**Simulation** sur 250 votants, répartition 130/80/40 → publié 123/84/43. Somme
exacte (250), erreur max 2,8 %.

*Ces chiffres proviennent de simulations, pas d'un déploiement réel : VERA n'a
pas encore été utilisé pour une consultation en conditions réelles. Le parcours
complet a été validé de bout en bout dans un navigateur, mais sur trois votes de
test.*

**Sur le choix de ε = 0,5 :** c'est un régime plus strict que les déploiements
industriels connus (Apple : ε = 2–16 ; Google RAPPOR : ε = 2–9 ; US Census
2020 : ε ≈ 19,6). L'imprécision sur les petites cohortes n'est pas un défaut
d'implémentation — c'est la garantie qui s'exerce.

---

## La garantie, et ce sur quoi elle repose

### Ce que VERA garantit

Aucune réponse ne peut être reliée à une personne par l'organisateur de la
consultation, ni par un tiers, ni par quiconque lirait la base à un instant
donné. Le serveur ne stocke jamais le lien entre une identité et un vote : deux
registres disjoints coexistent, et la réponse n'existe que dans un compteur
agrégé.

### Ce sur quoi cette garantie repose

La cryptographie supprime le lien **algébrique** entre l'invitation et la
réponse. Elle ne supprime pas le lien **temporel** : qui lirait la base en
continu verrait une invitation être consommée, puis un compteur s'incrémenter
quelques secondes plus tard. Il lui manquerait la correspondance
personne → invitation, que détient l'organisation qui consulte, et elle seule.

**La protection tient parce que celui qui héberge n'a pas la liste, et que celui
qui a la liste n'héberge pas.** C'est une séparation des rôles, pas une
impossibilité technique — et c'est pourquoi l'hébergement doit être assuré par un
tiers distinct de l'organisation qui consulte.

Face à un opérateur qui chercherait **activement** à contourner le système — en
servant un client modifié — aucune vérification exécutée dans un navigateur ne
protège. Détail : [modèle de menace](VERA_THREAT_MODEL_COMPLETE.md), section 1.

### Ce que la confidentialité différentielle couvre, et ce qu'elle ne couvre pas

ε = 0,5 borne ce qu'un adversaire peut apprendre **des résultats publiés** :
même en connaissant toutes les autres réponses, sa certitude sur une réponse
individuelle reste bornée à environ 62 %, contre 50 % sans information. C'est une
propriété du mécanisme, vérifiable, et elle tient.

Elle ne borne rien d'autre. Elle ne protège ni le fait qu'une personne ait
participé, ni le moment où elle l'a fait, ni ce qu'un adversaire apprendrait en
observant le serveur pendant la consultation. Ces canaux existent, ils sont
décrits dans [LIMITS.md](LIMITS.md), et aucune valeur d'epsilon ne les ferme.

Un lecteur pressé retient « confidentialité différentielle » comme un label de
protection totale. Ce n'en est pas un : c'est une garantie précise sur un
périmètre précis, et c'est hors de ce périmètre que se trouvent les vraies
limites de ce système.

---

## Déploiement

> **Cette section s'adresse à l'hébergeur tiers**, pas à l'organisation qui
> consulte. Celle-ci n'a rien à installer : elle utilise un tableau de bord web.
> Son guide est [GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md).

### Prérequis

- Un serveur Linux (testé sur Ubuntu 24.04 et 26.04), 2 Go de RAM suffisent
- Python 3.11 ou supérieur, et la chaîne de compilation Rust (`rustup`)
- Un nom de domaine et un certificat TLS
- nginx
- **Un hébergeur distinct de l'organisation qui consulte** — c'est la condition
  de la garantie

### Installation

```bash
git clone https://github.com/taha-vera/projet-vera-consultations-.git
cd projet-vera-consultations-

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Le module de signature aveugle est en Rust : il n'est pas sur PyPI.
# Sans lui, l'API refuse de démarrer (fail-closed, porte 7).
pip install maturin
cd vera_blind_sig && maturin develop --release && cd ..

# Clé de chiffrement de la base — À CONSERVER HORS DU SERVEUR.
# Sans elle, aucun redémarrage n'est possible et les données sont illisibles.
python3 -c "import secrets; print(secrets.token_hex(32))"

# Empreinte du mot de passe d'administration
python3 -c "from vera_admin_auth import generer_empreinte; print(generer_empreinte('votre-mot-de-passe'))"
```

Copiez `infra/nginx-vera-consultation.conf` dans vos sites nginx et adaptez le
nom de domaine. **Ne modifiez pas les blocs `access_log off` ni la directive
`error_log crit`** : ils ferment un canal de corrélation documenté (portes 23
et 26).

### Configuration

Variables d'environnement de l'unité systemd :

| Variable | Rôle | Défaut |
|---|---|---|
| `VERA_DB_KEY` | Clé de chiffrement de la base (64 caractères hexadécimaux). **Obligatoire.** | — |
| `VERA_ADMIN_USER` | Identifiant du compte d'amorçage | — |
| `VERA_ADMIN_HASH` | Empreinte PBKDF2 du mot de passe, format `sel$hash` | — |
| `VERA_DB_PATH` | Emplacement de la base | `/root/vera_state.db` |
| `VERA_VERROU_PROCESSUS` | Verrou d'instance unique | à côté de la base |

Deux paramètres ne se configurent pas et sont inscrits dans le code, pour être
vérifiables : le budget de confidentialité (ε = 0,5) et le seuil de publication
(240 réponses). Ils sont exposés publiquement sur `/api/engagement_cles`, ce qui
permet à un tiers de constater qu'ils n'ont pas été modifiés en cours de
consultation.

**uvicorn doit tourner avec un seul worker.** L'état du budget et le cache
d'idempotence vivent en mémoire de processus ; plusieurs workers casseraient
silencieusement la composition ε. Le code refuse de démarrer si une seconde
instance détient le verrou.

**uvicorn doit écouter uniquement sur `127.0.0.1`**, derrière nginx. Exposé
directement, toutes les limitations de débit et les coupures de journalisation
seraient contournables.

### Cycle d'une consultation

1. L'organisateur définit la question, déclare ses groupes et fixe la date
   d'ouverture des votes.
2. Il publie l'empreinte agrégée des clés hors du serveur — auprès des
   représentants du personnel — **avant** d'envoyer la moindre invitation.
3. L'organisation diffuse les invitations depuis sa propre liste, jamais
   transmise à l'hébergeur.
4. Collecte, sept jours au maximum.
5. `POST /api/rh/cloturer` renvoie les résultats une dernière fois — à
   sauvegarder — puis efface définitivement compteurs, effectifs, jetons,
   secrets consommés, budget ε, résultats publiés et clé de signature.

Après clôture, un accès au serveur ne révèle plus rien de la consultation passée.
C'est la minimisation des données (RGPD art. 5) rendue opérationnelle et
testable. Vérifié en conditions réelles : un état de dix départements ramené à
zéro après clôture.

---

## Vérifier une installation

Le code est intégralement lisible, primitive cryptographique comprise
(`vera_blind_sig/`).

```bash
# 1. Les fichiers servis correspondent-ils au code publié ?
curl -s https://votre-domaine/vote | sha256sum
curl -s https://votre-domaine/static/blindrsa-bundle.js | sha256sum
# Comparez aux empreintes de VERIFICATION_CLIENT.md

# 2. Le serveur applique-t-il les paramètres annoncés ?
python3 verifier_engagement.py https://votre-domaine
```

Le second script vérifie le seuil de publication réellement appliqué, la valeur
d'epsilon, l'empreinte de l'ensemble des clés, et le nombre d'invitations émises
par groupe — que vous pouvez comparer aux effectifs réels que vous connaissez.

Procédure détaillée : [VERIFICATION_CLIENT.md](VERIFICATION_CLIENT.md).

**Portée de cette vérification :** elle détecte une divergence entre le code
publié et le code servi. Elle ne protège pas contre un opérateur qui servirait
délibérément un client modifié au moment du vote. Voir
[modèle de menace](VERA_THREAT_MODEL_COMPLETE.md), section 1.

### Méthode d'audit du projet

Le code est audité **en lecture réelle**, pas seulement sur description —
plusieurs correctifs importants n'ont été trouvés que de cette façon, dont un
mécanisme de vérification qui ne vérifiait rien, le navigateur se contentant de
croire le serveur sur parole.

Chaque porte marquée « fermée » l'a été après vérification sur le serveur de
production, avec une preuve reproductible.

**Une porte fermée peut être rouverte par une fonctionnalité ajoutée plus tard.**
Ce n'est pas une précaution théorique : c'est arrivé deux fois sur ce projet,
dont une fois sans être détecté pendant quatorze jours. Toute modification
touchant les mécanismes d'une porte fermée doit s'accompagner d'une
re-vérification de celle-ci.

Cette consigne s'adresse à qui modifie le code. Elle n'implique aucune
vérification de la part de l'organisation qui utilise VERA.

---

## Ce qui reste de votre responsabilité

VERA ne connaît pas la liste de vos membres : c'est ce qui protège leur
anonymat. La contrepartie est que **VERA ne peut vérifier ni que les invitations
sont parties aux bonnes personnes, ni qu'elles ne sont parties qu'à elles.**

La fiabilité des résultats repose donc sur l'intégrité de votre liste de
diffusion.

- **Consultation informelle :** publier le nombre d'invitations envoyées et
  faire vérifier la liste par une seconde personne suffit généralement. Le
  nombre d'invitations émises par groupe est exposé publiquement, ce qui permet
  à un représentant du personnel de le comparer aux effectifs réels.
- **Scrutin contraignant ou juridiquement opposable :** cette garantie manquante
  est rédhibitoire. VERA n'est pas conçu pour cet usage.

Détail : [LIMITS.md](LIMITS.md) §13.

Vous restez également responsable de la notice RGPD jointe aux invitations, et
du choix d'un hébergeur tiers effectivement indépendant.

---

## Règles d'usage

Le budget de confidentialité s'applique **par consultation**, et non par
cohorte : il est remis à zéro à chaque clôture. Reposer une question à la même
population *k* fois coûte ε = 0,5 × *k* sur ces personnes.

VERA ne peut pas l'empêcher techniquement — suivre l'exposition d'un individu
supposerait de l'identifier, ce que l'anonymat interdit, et le nom de groupe
reste modifiable par l'organisateur. Le tableau de bord avertit néanmoins dès la
deuxième consultation d'un même groupe, et fermement à partir de la quatrième.

**Règle : pas plus de 4 consultations par période de 12 mois glissants sur la
même population** (ε cumulé = 2,0, dernier palier défendable).

Barème complet et justification : [LIMITS.md](LIMITS.md) §14.

---

## Limites assumées

| | Limite | Statut |
|---|---|---|
| **L1** | Observateur réseau | Documentée, non fermée |
| **L2** | Coercition du votant | Hors périmètre technique |
| **L3** | Petits effectifs | Refus de publier sous le seuil |
| **L4** | Qualification RGPD : anonymisation ou pseudonymisation | Non tranché — avis CNIL ou DPO externe requis |
| **L5** | Corrélation temporelle entre les deux requêtes d'un même votant | Documentée, fermeture mesurée puis écartée |

**Sur L4 :** c'est la question qui décide de l'adoption dans la plupart des
organisations, puisqu'elle détermine si le traitement sort ou non du champ du
règlement. Si votre DPO fait trancher ce point, une analyse publiée bénéficierait
à l'ensemble des utilisateurs du projet — ouvrez une issue.

**Sur L5 :** deux constructions ont été implémentées puis retirées après mesure
(délai aléatoire avant écriture, écriture par lots mélangés). Les chiffres et le
raisonnement figurent dans le modèle de menace. Cette limite tient à la
séparation des rôles, pas à un défaut d'implémentation.

---

## Documentation

| Document | Contenu |
|---|---|
| [LIMITS.md](LIMITS.md) | Limites détaillées, canaux non couverts, barèmes |
| [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md) | Modèle de menace (26 portes), modèle d'adversaire, analyses |
| [VERA_AUDIT_REFERENCE.md](VERA_AUDIT_REFERENCE.md) | Synthèse et paramètres |
| [VERIFICATION_CLIENT.md](VERIFICATION_CLIENT.md) | Vérifier que le serveur sert bien ce code |
| [GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md) | Guide de l'organisation qui consulte, notice RGPD |

### Composants principaux

| Fichier | Rôle |
|---|---|
| `vera_dp_noise.py` | Mécanisme de bruit (OpenDP, Δ₁ = 2 sous adjacence par substitution, scale = 4, ε = 0,5) |
| `vera_signature_manager.py`, `vera_blind_sig/` | Signature aveugle RSABSSA (RFC 9474). L'aveuglement et la finalisation ont lieu dans le navigateur du votant : le serveur ne voit ni le secret ni la signature finale. |
| `vera_persistance.py` | Persistance chiffrée de l'état — portes 11 et 14 (SQLite en `journal_mode=DELETE`, Fernet/AES-128) |
| `verifier_engagement.py` | Outil du tiers vérificateur |

**Note sur Fernet/AES-128 :** ce chiffrement protège l'état transitoire au
repos, dont la durée de vie est bornée par la clôture. Il n'entre pas dans la
chaîne de garantie de l'anonymat, qui repose sur RSABSSA et sur la disjonction
des registres.

**Note sur le module Rust :** 106 lignes, dont l'essentiel est une liaison PyO3
vers le crate `blind-rsa-signatures` 0.17. Aucune primitive cryptographique n'a
été réimplémentée, ni côté serveur ni côté navigateur — c'est délibéré.

---

## Sécurité

**Signalement de vulnérabilité :** tahahouari@hotmail.fr

Merci de **ne pas ouvrir d'issue publique** pour une vulnérabilité touchant
l'anonymat ou la garantie ε. Délai de réponse visé : **7 jours**.

Voir également [SECURITY.md](SECURITY.md).

---

## État du projet et contributions

**Statut :** fonctionnel et audité, **jamais déployé en conditions réelles.**
Le parcours complet a été validé de bout en bout dans un navigateur ; aucune
consultation avec de vrais participants n'a encore eu lieu.

**Version courante :** commit `main`, 16 août 2026 — 24 tests automatiques.

**Contact :** tahahouari@hotmail.fr

Toute contribution touchant un mécanisme lié à une porte fermée doit inclure la
re-vérification de cette porte, avec sa preuve reproductible.

---

## Citer VERA

Antériorité horodatée (Zenodo) :

- v1.0 (2026-06-12) — https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) — https://doi.org/10.5281/zenodo.20671969

---

## Licence

**Code :** MIT — voir [LICENSE](LICENSE).
**Documentation :** CC-BY 4.0.

> **Point à arbitrer.** Pour un projet où une modification du client peut défaire
> les garanties annoncées, une licence copyleft réseau (AGPL-3.0) obligerait un
> opérateur qui modifie le code à publier ses modifications. C'est cohérent avec
> le modèle de menace, section 1 — et cela transformerait une limite documentée
> en obligation juridique. Ce changement reste à trancher.
