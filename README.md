# VERA Consultation

**Agrégation à confidentialité différentielle, non-persistante.**

VERA publie le résultat collectif d'une consultation sensible sans jamais rendre
lisible la contribution d'un individu — ni pour l'organisateur, ni pour
l'hébergeur, ni pour un tiers.

**VERA est un service hébergé, pas un logiciel à installer.** C'est l'équipe
VERA qui opère le serveur ; l'organisation qui consulte garde sa liste de
membres et n'a rien à déployer. Cette séparation n'est pas une recommandation
adressée au client : c'est la condition de la garantie, et elle est remplie par
construction dans ce modèle.

- Confidentialité différentielle à ε = 0,5 (OpenDP)
- Signatures aveugles RSABSSA — RFC 9474, aveuglement et finalisation dans le
  navigateur du votant
- Aucune persistance du lien identité → réponse
- Modèle de menace public : **26 portes — 15 fermées avec preuve reproductible,
  6 fermées sous condition explicite, 5 limites assumées**

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

VERA convient si les conditions suivantes sont réunies. Les cinq premières sont
les conditions de la garantie — énumérées et justifiées dans
[LIMITS.md](LIMITS.md) §0 ; les deux dernières sont des contraintes d'usage.

| Condition | Seuil | Pourquoi |
|---|---|---|
| Effectif du groupe consulté | **≥ 240 réponses** | En dessous, le bruit rend le résultat inexploitable. VERA refuse alors de publier — pas de version dégradée. |
| Hébergement | **assuré par VERA**, distinct de l'organisation qui consulte | C'est la condition de la garantie, et elle est remplie par défaut. |
| Attestation de l'effectif | par un tiers mandaté (CSE, représentants du personnel) | Sans elle, l'organisation peut fabriquer une partie des réponses sans que rien ne le montre. |
| Découpage en groupes | **sans recoupement** — chaque personne dans un seul groupe publié | Quelqu'un présent dans deux groupes subit ε = 1,0 en une seule consultation, alors que le barème le classe à 0,5. VERA ne peut pas le détecter : il ne connaît pas vos membres. |
| Transporteur des invitations | **indépendant de l'hébergeur** | Le transporteur voit le couple (personne, invitation) ; l'hébergeur détient la base. Réunis, ils désanonymisent. |
| Fenêtre de collecte | ≤ 7 jours | Les clés de signature sont détruites automatiquement à l'expiration. |
| Portée du résultat | consultatif | VERA ne garantit pas l'intégrité du corps électoral. |

**240 réponses, pas 240 invitations.** L'effectif minimal d'un groupe vaut
240 / taux de participation. **Ce taux n'a jamais été mesuré sur VERA** : c'est
l'inconnue principale du projet, et aucun chiffre présenté ici n'est un taux
« attendu » ou « réaliste ». La valeur prudente retenue par défaut est **40 %,
soit 600 personnes par groupe** ; à 25 %, il en faut près de 1 000. Barème
complet : [LIMITS.md](LIMITS.md) §2.

Une organisation de 600 personnes ne peut donc espérer, dans cette hypothèse,
qu'un seul résultat d'ensemble : découper par service produirait des groupes
dont aucun n'atteindrait le seuil.

**Public visé :** grandes entreprises et groupes, fonction publique, hôpitaux,
universités, syndicats de branche, associations de grande taille.

Les structures plus petites ne peuvent pas obtenir un résultat à la fois anonyme
et suffisamment précis à ε = 0,5. C'est une contrainte mathématique, pas un choix
de conception.

### Précision

**Le bruit est absolu, pas proportionnel.** L'erreur sur la valeur publiée vaut
environ **12 voix au 95ᵉ centile, quel que soit l'effectif** — projection sur le
simplexe comprise, celle-ci étant du post-traitement, gratuite en ε. Mesure de
référence : 20 000 tirages à n = 240, erreur maximale sur les trois options
(16,1 voix avant projection, 12,0 après). Les pourcentages n'en sont que la
traduction :

| Effectif | Erreur max |
|---|---|
| 100 | 12 % |
| 150 | 8 % |
| 200 | 6 % |
| **240** | **5 %** ← seuil de publication |
| 500 | 2,4 % |
| 1 000 | 1,2 % |
| 5 000 | 0,24 % |

Les valeurs hors de n = 240 découlent du caractère absolu du bruit ; elles ne
sont pas mesurées séparément. Méthode et chiffres : [LIMITS.md](LIMITS.md) §2,
qui fait foi — toute autre série de simulations citée ailleurs est obsolète.

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
impossibilité technique.

**Concrètement, dans le service tel qu'il est proposé :** VERA opère le serveur
et n'a jamais accès à la liste de vos membres — elle ne quitte pas votre
organisation, le système ne la demande à aucun moment. Vous détenez la liste
mais n'avez ni accès au serveur, ni à sa base : vous ne voyez que des totaux
dans un tableau de bord.

Aucune des deux parties ne peut faire le lien seule. C'est ce qui protège vos
membres, et c'est vérifiable : le contrat d'hébergement peut être communiqué à
vos représentants du personnel.

**Le cas à éviter.** Si une organisation installait VERA sur ses propres
serveurs, elle réunirait les deux rôles : elle aurait la liste *et* la base.
Un administrateur pourrait alors rapprocher la consommation d'une invitation et
l'incrément d'un compteur survenu quelques secondes plus tard. Le code
fonctionnerait à l'identique, mais la garantie ne tiendrait plus.

C'est la raison pour laquelle ce projet est distribué comme un service et non
comme un produit à déployer. Le code reste public — pour être vérifié, pas pour
être installé par l'organisation qui consulte.

Face à un opérateur qui chercherait **activement** à contourner le système — en
servant un client modifié — aucune vérification exécutée dans un navigateur ne
protège. Détail : [modèle de menace](VERA_THREAT_MODEL_COMPLETE.md), section 1.

### Ce que la confidentialité différentielle couvre, et ce qu'elle ne couvre pas

ε = 0,5 borne ce qu'un adversaire peut apprendre **des résultats publiés** :
même en connaissant toutes les autres réponses, sa certitude sur une réponse
individuelle reste bornée à 62,25 %, contre 50 % sans information. C'est une
propriété du mécanisme, vérifiable, et elle tient.

**Ce chiffre suppose trois choses**, et il ne veut rien dire sans elles : un
adversaire qui connaît déjà toutes les autres réponses, un a priori équilibré
sur celle qui l'intéresse, et une décision entre deux valeurs. C'est la borne
`e^ε/(1+e^ε)`, un maximum théorique dans le pire cas — pas une probabilité
universelle de réidentification. Dérivation complète et hypothèses :
[LIMITS.md](LIMITS.md) §14.

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

> **Cette section ne s'adresse pas à l'organisation qui consulte.** Celle-ci n'a
> rien à installer : elle utilise un tableau de bord web, et son guide est
> [GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md).
>
> Elle s'adresse à qui veut **vérifier** le code en le faisant tourner, ou à une
> organisation qui opérerait VERA pour le compte d'autres — jamais pour
> elle-même. Une organisation qui héberge sa propre consultation réunit les deux
> rôles et perd la garantie : voir [ci-dessus](#ce-sur-quoi-cette-garantie-repose).

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
cd vera_blind_sig
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release
cd ..

# Clé de chiffrement de la base — À CONSERVER HORS DU SERVEUR.
# Sans elle, aucun redémarrage n'est possible et les données sont illisibles.
python3 -c "import secrets; print(secrets.token_hex(32))"

# Empreinte du mot de passe d'administration
python3 -c "from vera_admin_auth import generer_empreinte; print(generer_empreinte('votre-mot-de-passe'))"
```

> **Sur la variable `PYO3_USE_ABI3_FORWARD_COMPATIBILITY`.** PyO3 refuse de
> compiler contre une version de Python qu'il ne connaît pas encore — c'est le
> cas de la 3.14. Sans cette variable, `maturin` échoue avec un message qui
> ressemble à une erreur de code alors que le code est correct. Elle est inutile
> sur Python 3.11 à 3.13, et sans effet négatif.

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
| `VERA_DOMAINE` | Origine HTTPS du service. Sert d'origine CORS et de base aux liens d'invitation. Le démarrage échoue si elle n'est pas en `https://`. | `https://vera-consultation.duckdns.org` |

La variable de repli `VERA_ADMIN_PASS`, qui acceptait le mot de passe en clair,
a été retirée le 23/08/2026 — c'était le canal par lequel des secrets ont fuité
le 31/07. Si elle figure encore dans une unité systemd sans `VERA_ADMIN_HASH`,
**le service refuse de démarrer** et indique la migration à faire. Voir
[LIMITS.md](LIMITS.md) §12.

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
testable. Vérifié sur le serveur de production : un état de dix départements
ramené à zéro après clôture.

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

**Vous pouvez aussi reconstruire le bundle vous-même** et vérifier qu'il dérive
bien du code source publié :

```bash
cd chantier_crypto && npm ci && npm run build:verifier
sha256sum /tmp/vera_bundle_verif.js ../static/blindrsa-bundle.js
```

Les deux empreintes doivent être identiques. Le build est déterministe : mêmes
sources, mêmes dépendances figées par `package-lock.json`, même fichier au bit
près, quelle que soit la machine.

Ces empreintes sont tenues à jour par une garde d'intégration continue
(`test_empreintes_publiees.py`, `test_bundle_reconstructible.py`) : toute modification de la page de vote ou du
bundle qui ne s'accompagnerait pas de la mise à jour du document fait échouer le
workflow. Une procédure de vérification qui se déclenche à tort n'en est plus
une.

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

**Une porte fermée peut être rouverte par une modification apportée plus tard.**
Ce n'est pas une précaution théorique : **c'est arrivé cinq fois sur ce projet**,
et le décompte est tenu à jour dans [LIMITS.md](LIMITS.md). Une fois sans être
détecté pendant quatorze jours. Une fois dans le mécanisme de détection
lui-même — le 22/08, un correctif a modifié la page de vote sans que son
empreinte publiée suive, si bien que pendant sept jours la procédure ci-dessus
produisait, chez tout tiers qui l'appliquait, le signal d'un client modifié. Et
une fois dans un correctif censé fermer une classe, qui n'a fermé qu'un cas.

Toute modification touchant les mécanismes d'une porte fermée doit s'accompagner
d'une re-vérification de celle-ci.

Cette consigne s'adresse à qui modifie le code. Elle n'implique aucune
vérification de la part de l'organisation qui utilise VERA.

---

## Ce qui reste de votre responsabilité

VERA ne connaît pas la liste de vos membres : c'est ce qui protège leur
anonymat. La contrepartie est que **VERA ne peut vérifier ni que les invitations
sont parties aux bonnes personnes, ni qu'elles ne sont parties qu'à elles.**

La fiabilité des résultats repose donc sur l'intégrité de votre liste de
diffusion.

- **Consultation d'opinion :** faire attester la liste par un tiers mandaté
  suffit. Le nombre d'invitations émises par groupe est exposé publiquement sur
  `/api/engagement_cles` : un représentant du personnel peut le comparer à
  l'effectif du registre sans rien vous demander.
- **Scrutin contraignant ou juridiquement opposable :** cette garantie manquante
  est rédhibitoire. VERA n'est pas conçu pour cet usage.

**Cette responsabilité se délègue, et elle doit l'être.**

**À inscrire dans l'accord, avant l'ouverture des dépôts :**

> L'organisation communique aux représentants du personnel le nombre
> d'invitations émises par groupe et l'effectif inscrit au registre du personnel
> pour ce même groupe. L'écart est justifié par écrit.

C'est la troisième condition du dispositif, au même rang que le seuil de 240 et
l'hébergement séparé. Aucun code ne peut la remplacer : vérifier qu'une
invitation correspond à une personne réelle supposerait de connaître les
personnes — exactement ce que VERA s'interdit.

Détail : [LIMITS.md](LIMITS.md) §13.

Vous restez également responsable de la notice RGPD jointe aux invitations, du
choix d'un hébergeur tiers effectivement indépendant, et de celui d'un
transporteur d'invitations sans lien avec cet hébergeur ([LIMITS.md](LIMITS.md)
§12bis).

---

## Règles d'usage

**Les groupes déclarés doivent former une partition de votre population** —
chaque personne dans un groupe, un seul. Un découpage par service convient ; un
découpage croisant service et statut ne convient pas : ceux qui se trouvent à
l'intersection paient le double, silencieusement, et rien dans les chiffres
publiés ne le signale. VERA ne peut pas le détecter, puisqu'il ne connaît pas
vos membres. Détail : [LIMITS.md](LIMITS.md) §11bis.

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

**Une consultation porte une question, à trois options.** VERA produit donc au
plus quatre référendums d'entreprise par an et par population. Si votre besoin
est un questionnaire ou un baromètre à plusieurs items, ce n'est pas l'outil :
[LIMITS.md](LIMITS.md) §0.

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
| [LIMITS.md](LIMITS.md) | Limites détaillées, canaux non couverts, barèmes — **fait foi en cas de divergence** |
| [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md) | Modèle de menace (26 portes), modèle d'adversaire, analyses |
| [VERA_AUDIT_REFERENCE.md](VERA_AUDIT_REFERENCE.md) | Instantané daté du 31/07 — trace historique, **paramètres périmés** |
| [VERIFICATION_CLIENT.md](VERIFICATION_CLIENT.md) | Vérifier que le serveur sert bien ce code |
| [GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md) | Guide de l'organisation qui consulte, notice RGPD |

### Composants principaux

| Fichier | Rôle |
|---|---|
| `vera_consultation_api.py` | Tous les endpoints HTTP |
| `vera_dp_noise.py` | Mécanisme de bruit (OpenDP, Δ₁ = 2 sous adjacence par substitution, scale = 4, ε = 0,5) |
| `vera_signature_manager.py`, `vera_blind_sig/` | Signature aveugle RSABSSA (RFC 9474). L'aveuglement et la finalisation ont lieu dans le navigateur du votant : le serveur ne voit ni le secret ni la signature finale. |
| `vera_persistance.py` | Persistance chiffrée de l'état — portes 11 et 14 (SQLite en `journal_mode=DELETE`, Fernet/AES-128) |
| `vera_epsilon_budget.py` | Budget de confidentialité |
| `vera_admin_auth.py` | Authentification de l'organisateur |
| `static/vote.html`, `static/admin.html` | Page du votant, tableau de bord |
| `verifier_engagement.py` | Outil du tiers vérificateur |

L'architecture est **plate** : fichiers Python à la racine, module Rust dans
`vera_blind_sig/`, deux pages dans `static/`. Il n'existe ni `routes/`, ni
`models/`, ni `auth/`.

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

**Version courante :** branche `main`, 26 août 2026 — 30 tests automatiques,
plus un test de résistance au crash exercé sur le chemin HTTP réel.

**L'équipe d'exploitation est réduite.** Ce n'est pas un détail d'organisation :
cela limite ce qui peut être promis en matière de continuité, d'astreinte et de
chaîne de sous-traitance au sens de l'article 28 du RGPD. Une organisation qui
envisage VERA doit poser la question avant de s'engager, et la réponse figurera
au contrat.

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

**Code :** AGPL-3.0 — voir [LICENSE](LICENSE).
**Documentation :** CC-BY 4.0.

**Pourquoi une licence copyleft réseau.** Dans ce projet, la garantie annoncée
aux participants dépend du code exécuté dans leur navigateur : un opérateur qui
sert un JavaScript modifié défait l'anonymat sans que rien ne le signale
(`LIMITS.md` §6). L'AGPL fait de cette limite documentée une obligation
juridique — quiconque opère une version modifiée de VERA pour des utilisateurs
distants doit leur en proposer le code source correspondant.

C'est la seule licence qui atteigne un opérateur de service. Sous MIT, ou même
sous GPL, une version modifiée servie sur un serveur ne déclenche aucune
obligation de publication : le logiciel n'est pas *distribué*, il est seulement
*exécuté*. C'est précisément le cas de VERA.

**Ce que cela n'apporte pas, et qu'il ne faut pas confondre.** L'AGPL est une
obligation, pas un mécanisme de détection. Un opérateur malveillant qui sert un
client piégé viole la licence — il ne devient pas détectable pour autant. Ce que
la licence change, c'est qu'un écart constaté devient opposable en droit et plus
seulement en fait. La protection réelle reste la séparation des rôles.

**Ce que l'AGPL impose à qui opère VERA.** La section 13 demande d'offrir le
code source aux utilisateurs *distants* — pas seulement à qui reçoit une copie
du logiciel. La page de vote porte donc un lien vers le dépôt. Sans lui,
l'obligation existerait en droit sans qu'aucun votant ait le moyen de l'exercer.

Cette mention a aussi une valeur propre : la garantie annoncée au votant dépend
du JavaScript exécuté dans *son* navigateur. Lui donner l'adresse du code, c'est
lui donner de quoi le faire vérifier.

**Sur le changement de licence.** Le projet était sous MIT jusqu'au 23/08/2026.
Les copies déjà obtenues sous MIT le restent — une licence accordée ne se retire
pas. Le changement vaut pour les versions publiées à partir de cette date.
