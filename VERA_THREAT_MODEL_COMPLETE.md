# VERA Consultation — Modele de menace

**Auteur :** Taha Houari · tahahouari@hotmail.fr
**Depot :** https://github.com/taha-vera/projet-vera-consultations-
**Production :** https://vera-consultation.duckdns.org

Ce document decrit l'etat actuel du systeme. Il n'est pas un journal : chaque
enonce porte sur ce que le code fait aujourd'hui.

**Methode.** Un statut n'est marque « ferme » que s'il a ete verifie sur le
serveur de production, avec une preuve reproductible. Une porte fermee peut
etre rouverte par une fonctionnalite ou une modification d'infrastructure
ulterieure : les hypotheses d'une porte fermee sont a re-verifier a chaque
changement touchant les memes mecanismes.

---

## 1. Modele d'adversaire

Toutes les garanties se lisent relativement a un adversaire. VERA distingue
deux niveaux et ne pretend a la garantie forte que contre le premier.

### Niveau 1 — tiers et operateur honnete-mais-curieux

**Garantie forte.** Contre un tiers (lecteur des resultats publies, observateur
reseau, attaquant externe) et contre un operateur qui administre le serveur
sans chercher a falsifier le logiciel, VERA garantit qu'aucune reponse ne peut
etre reliee a une personne.

Cette garantie est structurelle, pas procedurale : le serveur ne stocke jamais
le lien identite ↔ vote. Deux registres disjoints coexistent — les jetons
d'autorisation d'un cote, les empreintes des secrets consommes de l'autre — et
la reponse n'existe que dans un compteur agrege par (departement, reponse).
Un administrateur lisant toute la base ne peut pas desanonymiser un vote.

### Niveau 2 — operateur activement malveillant

**Hors garantie sans hebergement tiers.** Un operateur qui controle toute la
chaine — il sert le JavaScript client, termine le TLS, detient les cles
privees, lit les journaux — contourne la cryptographie sans la casser :

- il sert un client pige qui exfiltre le secret K avant l'aveuglement, ce qui
  retablit le lien identite ↔ vote a la source ;
- il correle les requetes de signature et de vote via des journaux qu'il
  controle ;
- il signe de faux votes avec la cle privee qu'il detient ;
- il reecrit le champ reponse cote serveur, que la signature aveugle ne couvre
  pas (elle couvre K).

Aucune cryptographie ne protege contre l'entite qui controle le code execute et
l'infrastructure.

**Condition pour un anonymat face a l'organisation consultante.** Si
l'organisation qui consulte heberge elle-meme le serveur, elle est dans la base
de confiance de Niveau 2. Un anonymat reel face a elle exige un hebergement par
un tiers distinct (association neutre, prestataire independant), ou un client
verifiable independamment (build reproductible, empreinte publiee).

Ce point doit etre explicite aupres de toute organisation : VERA rend la
desanonymisation passive impossible, il ne remplace pas la confiance dans
l'hebergeur face a un adversaire actif.

---

## 2. Ce que VERA ne garantit pas

### Integrite du scrutin

VERA prouve l'anonymat. Il ne prouve pas que le resultat publie reflete un vrai
scrutin. Le systeme ne connait pas la liste des membres — c'est ce qui protege
leur anonymat — et ne peut donc verifier ni que les invitations sont parties
aux bonnes personnes, ni qu'elles ne sont parties qu'a elles. Il n'existe ni
recu votant, ni urne publique, ni recomptage.

Ce n'est pas un defaut corrigeable : la verifiabilite de bout en bout exige un
decompte exact et publiquement recomptable, incompatible avec le decompte
bruite qu'impose la confidentialite differentielle. Un total verifiable
trahirait les individus que le bruit protege.

**Consequence.** VERA convient a une consultation d'opinion. Il ne convient pas
a un scrutin contraignant, electif ou juridiquement opposable, ou l'organisateur
pourrait avoir interet a fabriquer le resultat et ou la contestation doit
pouvoir s'appuyer sur une preuve.

Deux arguments rassurants sont a ecarter. « Un organisateur qui falsifie son
propre sondage se trompe lui-meme » n'est vrai que si la consultation sert a
l'informer ; un barometre social sert souvent a communiquer un resultat a des
tiers — direction, representants du personnel, tutelle — et l'organisateur ne
se trompe alors pas lui-meme, il trompe autrui. « Les participants verraient
l'ecart » est faux : ils ne voient pas la liste de diffusion.

### Composition entre consultations

Le budget epsilon vaut **par consultation**, pas par cohorte : il est remis a
zero a chaque cloture. Reposer une question aux memes personnes k fois coute
epsilon = 0.5 × k sur ces personnes, sans que le systeme le mesure ni le
signale.

Ce n'est pas corrigeable par un verrou fiable. La composition porte sur les
PERSONNES, et VERA n'a aucune identite persistante. Le seul identifiant
disponible est le nom du departement, controle par l'organisateur lui-meme
donc contournable par un simple renommage. Un blocage dur n'arreterait pas un
organisateur determine et enfermerait un groupe legitime.

**Regle d'usage retenue :** pas plus de 4 consultations par periode de 12 mois
glissants sur une meme population (epsilon cumule 2.0, dernier palier
defendable). Bareme complet : `LIMITS.md` section 14.

### Compteurs agreges lisibles en base

Les tables `compteurs_votes` et `effectifs` sont persistees en clair ; seule la
cle RSA est chiffree. K_MIN protege le RESULTAT PUBLIE, pas la lecture directe
de la base.

Un operateur qui sonde ces tables pendant la consultation lit chaque reponse au
fil de l'eau, a toute taille de cohorte : il releve les compteurs avant et
apres un vote, la difference donne la reponse.

Cette lecture donne le QUOI, pas le QUI : aucune identite n'existe en base.
Pour desanonymiser, il faut une source temporelle externe placant une personne
dans la sequence — et ces canaux sont fermes (journaux des routes de vote,
jeton en fragment d'URL, horodatage retire, table anti-rejeu en `WITHOUT
ROWID`). La protection ne vient donc pas de la DP mais de l'absence d'identite
et de la fermeture des ancres temporelles.

Chiffrer ces tables serait illusoire : l'operateur detient `VERA_DB_KEY`, elle
est dans son unite systemd.

**Regle de deploiement :** ne pas decouper une consultation en departements
dont l'effectif attendu approche ou passe sous K_MIN. Non seulement le resultat
ne sera pas publiable, mais les comptes existent en base pendant toute la
consultation.

### Hors perimetre

- Observateur reseau (IP, timing en transit) — delegue a VPN/Tor
- Coercition physique ou sociale — partage par tout systeme de vote
- Qualification juridique CNIL/DPO (anonymisation vs pseudonymisation,
  art. 5 RGPD) — avis externe requis
- Secret administrateur visible dans `/proc/PID/environ` — acceptable en
  contexte solo-root, ou un acces root donne deja acces a la base

---

## 3. Parametres

| Parametre | Valeur | Note |
|---|---|---|
| Mecanisme de bruit | Laplace discret (OpenDP) | Bibliotheque auditee, immunise Mironov (pas de flottant) |
| Sensibilite Δ₁ | 2 | Sous adjacence par substitution, un individu modifie deux cases. Laplace VECTORIEL sur R³, pas de composition parallele |
| Scale | 4 | Δ₁ / epsilon |
| Epsilon par publication | 0.5 | Calcule analytiquement |
| Bornes de clamp | (0, 10 000) | Pre-traitement ; au-dela de 10 000 votes sur une option le resultat serait tronque |
| K_MIN | 240 | Seuil MESURE : a n=240 l'erreur max reste sous 5 % dans 95 % des publications. En dessous : n=200 → 6 %, n=150 → 8 %, n=100 → 12 % |
| Signature aveugle | RSABSSA-SHA384-PSS-Randomized (RFC 9474) | Modules 2048 bits, `blind-rsa-signatures` 0.17.2 |
| Bourrage constant | 200 octets | > 100 (departement max) + 10 (« abstention ») |
| Chiffrement cle RSA | Fernet + PBKDF2-SHA256 | 100 000 iterations, sel aleatoire par enregistrement |
| Anti-bruteforce | 5 echecs / IP, blocage 5 min | Sur la connexion RH |
| Rate-limit vote | 5 r/s, rafale 50 | Nginx, sur les 4 routes du parcours de vote |
| Rate-limit connexion | 1 r/s, rafale 5 | Nginx, zone dediee |

---

## 4. Etat des portes

| # | Vecteur | Statut | Preuve |
|---|---|---|---|
| 1 | Mecanisme de bruit | Fermee | Laplace vectoriel OpenDP, Δ₁=2, scale=4, ε=0.5. Projection sur le simplexe en post-traitement (gratuite en ε, erreur reduite d'environ 25 %) |
| 2 | Inference d'appartenance (MIA) | Fermee | AUC = 0.6209, IC95 % [0.6185, 0.6232], borne theorique 0.6225 incluse (N=100 000, bootstrap) |
| 3 | Canal temporel | Fermee | Fuite sub-microseconde. Spearman ρ = −0.14, p = 0.76 (7 valeurs, N=10 000). Inexploitable via reseau (latence 50-100 ms) |
| 4 | Composition sequentielle | **Limite assumee** | Le budget vaut par consultation, pas par cohorte — voir section 2. Regle d'usage : 4 consultations/an max |
| 5 | Observateur reseau | Limite assumee | Hors-perimetre |
| 6 | Coercition | Limite assumee | Hors-perimetre |
| 7 | Differenciation « 49/1 » | Fermee | RSABSSA RFC 9474. Aveuglement et finalisation dans le navigateur du votant : le serveur ne voit ni le secret K ni la signature finale. Une cle RSA par departement, empreinte engagee dans le lien et verifiee cote client (parade substitution de cle) |
| 8 | Inference sur le repondant atypique | Fermee | Meme mesure que porte 2. TPR@1%FPR = 1.6 % |
| 9 | Collusion emetteur / agregateur | Fermee | Secret admin distinct, comptes separes, isolation testee |
| 10 | Sondage binaire (seuil) | Fermee | Refus de publier sous K_MIN=240, verifie avant toute consommation de budget. Effectif exact des petites cohortes non expose |
| 11 | Acces direct a la base / cle RSA | Fermee | Chiffrement Fernet, sel aleatoire par enregistrement. Fail-closed : si des cles existent mais qu'aucune ne se dechiffre, le service refuse de demarrer plutot que d'en regenerer |
| 12 | Secret admin visible dans `/proc` | Limite assumee | Contexte solo-root |
| 13 | Soustraction d'agregats | Limite assumee | Limite irreductible de la DP, attenuee par publication unique par consultation — meme reserve que porte 4 |
| 14 | Persistance de l'etat de confidentialite | Fermee | SQLite WAL write-through. Verifie par `kill -9` et par reboot systeme complet. Complete par un effacement ACTIF a la cloture : compteurs, effectifs, jetons, budget, resultats publies et cle de signature detruits en une transaction, suivie de `wal_checkpoint(TRUNCATE)` et `VACUUM` |
| 15 | Trafic en clair | Fermee | HTTPS via Nginx + Let's Encrypt, redirection 301, renouvellement automatique |
| 16 | Retention des journaux | Fermee | Purge manuelle a la cloture + logrotate 3 jours. L'access log applicatif est desactive (voir porte 26) |
| 17 | Correlation temporelle en base | Fermee | Horodatage retire de la table anti-rejeu, table passee en `WITHOUT ROWID` : elle est ordonnee par empreinte SHA-256 pseudo-aleatoire, l'ordre d'insertion des votes n'existe plus |
| 18 | Generation de cles a la volee (DoS keygen) | Fermee | Les endpoints publics sont en lecture seule (404 si le departement n'existe pas) ; la creation de cle est reservee au flux RH authentifie |
| 19 | API exposee hors TLS | Fermee | uvicorn ecoute sur `127.0.0.1` ; Nginx est l'unique chemin d'acces |
| 20 | Publication declenchee par une lecture | Fermee | `GET /api/rh/resultats` est en lecture pure ; la publication est un `POST /api/rh/publier` explicite, avec confirmation. Ferme aussi le CSRF (le cookie `SameSite=Lax` laisse passer les GET de navigation) |
| 21 | Bourrage sature sur departement long | Fermee | Cible portee a 200 octets : la taille du corps de vote ne distingue plus « abstention » de « oui », quelle que soit la longueur du nom de departement |
| 22 | Saturation du threadpool | Fermee | La connexion RH declenche un PBKDF2 200 000 iterations a chaque appel et partage le threadpool avec le depot de vote. Rate-limit Nginx dedie (1 r/s, rafale 5) : verifie en production, 4 requetes passent puis 429 |
| 23 | En-tetes de securite HTTP | Fermee | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy `no-referrer` |
| 24 | Vote accepte puis efface a la cloture | Fermee | Publication et effacement dans le meme verrou : un vote concurrent ne peut plus recevoir « enregistre » puis disparaitre |
| 25 | Exposition de secrets par un canal hors-code | Fermee | Les trois secrets ont ete rotes apres exposition accidentelle. La rotation de la cle de chiffrement est verifiee de bout en bout |
| 26 | IP des votants dans le journal applicatif | Fermee | `access_log off` cote Nginx ne coupait que Nginx : uvicorn journalisait en parallele l'IP reelle des votants sur les routes de vote. Corrige par `--no-access-log` ; journal vide apres trafic verifie |

**Bilan : 22 portes fermees avec preuve, 4 limites assumees (5, 6, 12, et 4/13
qui partagent la meme cause).**

---

## 5. Deux points analyses, sans correctif

### Distinction 403 / 409 sur le depot de vote

L'endpoint distingue « signature invalide » (403) de « secret deja consomme »
(409). En theorie, cela permet de sonder si un secret a deja servi.

Ce canal n'est pas empruntable. La verification de signature precede le test du
registre anti-rejeu : pour obtenir un 409 il faut presenter un secret accompagne
d'une signature VALIDE sur ce secret. Or ce secret fait 32 octets tires par
`crypto.getRandomValues` dans le navigateur du votant — ni devinable, ni
derivable du jeton d'autorisation. Posseder le couple signifie donc etre le
votant, ou lui avoir vole son lien ; dans les deux cas, apprendre « ce secret a
vote » n'apprend rien de nouveau.

Uniformiser aurait un cout reel : le votant legitime qui rejoue apres une
coupure reseau ne saurait plus si son vote est passe.

Le meme raisonnement vaut pour l'ecart de timing entre les deux chemins : il
existe, il est noye dans la variance reseau, et il n'apprend a l'attaquant que
ce qu'il sait deja puisque c'est lui qui a forge la requete.

### Ordre d'insertion en base

L'ordre des votes ne fuit plus : la table anti-rejeu est en `WITHOUT ROWID`,
donc ordonnee par empreinte SHA-256 pseudo-aleatoire et non par insertion.

La table des jetons d'autorisation, elle, conserve un ordre — mais celui de la
GENERATION par le RH, pas de la consommation. Le passage a l'etat « utilise »
ne reordonne rien. Il est donc impossible d'apparier « n-ieme jeton consomme »
et « n-ieme vote insere ».

---

## 6. Ce que ce document ne prouve pas

- Que le code est exempt de bugs non identifies
- Que les limites assumees sont negligeables dans tous les contextes
- Que la qualification CNIL est acquise
- Qu'un expert humain en cryptographie ne trouverait rien de nouveau
- Que l'integrite du scrutin est garantie — seul l'anonymat l'est

---

## 7. Documents lies

- `README.md` — presentation et perimetre
- `LIMITS.md` — limites detaillees, sections 13 (integrite) et 14 (composition)
- `VERA_AUDIT_REFERENCE.md` — synthese des portes et parametres
- `AMELIORATIONS_FUTURES.md` — ce qui reste ouvert
- `vera_blind_sig/README.md` — primitive cryptographique et procedure de
  verification
