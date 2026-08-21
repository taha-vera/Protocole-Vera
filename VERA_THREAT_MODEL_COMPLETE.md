# VERA Consultation — Modele de menace

**Auteur :** Taha Houari · tahahouari@hotmail.fr
**Depot :** https://github.com/taha-vera/projet-vera-consultations-
**Production :** https://vera-consultation.duckdns.org

Ce document decrit l'etat actuel du systeme. Il n'est pas un journal : chaque
enonce porte sur ce que le code fait aujourd'hui.

**Methode.** Un statut n'est marque « ferme » que s'il a ete verifie sur le
serveur de production, avec une preuve reproductible. Une porte fermee peut
etre rouverte par une fonctionnalite ajoutee plus tard : c'est arrive deux fois
sur ce projet, dont une fois sans etre detecte pendant quatorze jours. Toute
modification touchant les mecanismes d'une porte fermee doit donc s'accompagner
d'une re-verification de celle-ci.

*Cette consigne s'adresse a qui modifie le code. Elle n'implique aucune
verification de la part de l'organisation qui utilise VERA.*

**A qui s'adresse ce document.** Il est destine a un auditeur, un delegue a la
protection des donnees, ou un responsable informatique charge d'evaluer VERA.
Une organisation qui souhaite simplement savoir ce que l'outil garantit peut
s'en tenir au README. Un participant a une consultation n'a rien a lire ici :
le lien qu'il a recu suffit.

---

## 1. Modele d'adversaire

Toutes les garanties se lisent relativement a un adversaire. VERA distingue
deux niveaux et ne pretend a la garantie forte que contre le premier.

### Niveau 1 — tiers et operateur honnete-mais-curieux

**Garantie forte.** Contre un tiers (lecteur des resultats publies, observateur
reseau, attaquant externe) et contre un operateur qui administre le serveur
sans chercher a falsifier le logiciel, VERA garantit qu'aucune reponse ne peut
etre reliee a une personne.

Le serveur ne stocke jamais le lien identite ↔ vote. Deux registres disjoints
coexistent — les jetons d'autorisation d'un cote, les empreintes des secrets
consommes de l'autre — et la reponse n'existe que dans un compteur agrege par
(departement, reponse). Une lecture PONCTUELLE de la base, meme complete, ne
permet donc aucune attribution.

**Mais cette garantie est procedurale autant que structurelle, et il faut le
dire.** L'invariant tient dans le schema ; il ne tient pas dans le temps.

Un adversaire qui lit la base EN CONTINU pendant la consultation — sans rien
modifier, sans toucher au logiciel, ce qui est exactement le profil de ce
niveau — observe la sequence suivante :

    jeton X passe a utilise=1        (consommation, requete de signature)
    compteur « oui » +1              (quelques secondes plus tard, depot)

L'appariement est direct. Reproduit empiriquement le 13/08 : trois votants,
trois appariements sans ambiguite. La signature aveugle supprime le lien
ALGEBRIQUE entre le jeton et le vote ; elle ne supprime pas le lien TEMPOREL
entre les deux ecritures.

**Ce qui empeche l'attaque aujourd'hui.** Elle exige DEUX choses : l'acces a la
base, et la liste (personne -> jeton). L'operateur detient la premiere,
l'organisation consultante la seconde. Aucun des deux ne peut seul. C'est cette
separation des roles qui protege, pas une impossibilite technique — et c'est
pourquoi l'hebergement par un tiers distinct de l'organisation qui consulte
n'est pas une precaution supplementaire mais la condition de la garantie.

**Ce qui la fermerait techniquement, et pourquoi ce n'est pas fait.**

Deux constructions ont ete examinees le 13/08.

*Retarder chaque depot d'un delai aleatoire avant ecriture.* Implemente puis
retire apres mesure : le brouillage ne vaut que si les votes arrivent a un
rythme comparable au delai. Simule sur 200 tirages avec un delai maximal de
60 secondes --

    1 vote / 10 s (pic d'affluence)   : 25 % des votes restent apparies
    1 vote / 60 s                     : 74 %
    1 vote / 5 min (rythme etale)     : 94 %

Or une consultation de 240 reponses sur une semaine, c'est un vote toutes les
quarante minutes en moyenne : le cas le plus a droite. La protection serait
quasi nulle la ou elle compterait, et donnerait l'illusion d'une garantie
technique la ou il n'y en a pas. Allonger le delai a la mesure du probleme --
plusieurs dizaines de minutes -- est inacceptable pour le votant.

*Ecrire les compteurs par lots melanges.* Efficace, mais la voix n'existerait
qu'en memoire entre le depot et l'ecriture : un redemarrage la perdrait. C'est
exactement le defaut ferme le 12/08 par l'idempotence de la signature. Le
remede serait pire que le mal.

**Conclusion assumee.** Le canal reste ouvert et la garantie reste
procedurale : elle tient parce que l'hebergeur n'a pas la liste des invites.
Une limite clairement ecrite vaut mieux qu'une attenuation qui rassure sans
proteger.

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
de confiance de Niveau 2 : l'adversaire dont ses membres se mefient est aussi
celui qui opere le systeme. La garantie ne tient alors que contre un
administrateur qui ne cherche pas activement a la contourner.

**Cette condition est tenue -- par une personne, et il faut le dire ainsi.**
VERA opere l'hebergement : le serveur est administre par le mainteneur du
protocole, distinct de l'organisation qui consulte.

Ecrire « la condition est remplie » serait exact sur le principe et trompeur en
pratique. Ce qui la tient aujourd'hui, c'est un individu : la cle de chiffrement
de la base est detenue par lui seul, sans depot chez un tiers, et le service
tourne sur un sous-domaine gratuit sans engagement contractuel (`LIMITS.md`
§12bis). La separation des roles existe ; sa perennite ne repose sur aucune
structure.

Pour une organisation qui evalue le dispositif, la question n'est donc pas « la
condition est-elle remplie » mais « par quoi est-elle garantie » -- et la
reponse honnete est : par la disponibilite d'une personne. C'est la principale
dependance non technique du systeme, et elle est traitee plus bas.

Ceci pose, l'organisation qui consulte Celle-ci n'a acces ni au serveur, ni a la base, ni aux journaux ;
elle dispose du seul tableau de bord, qui n'expose que des agregats. Elle passe
donc de Niveau 2 a Niveau 1, ou la garantie est forte et prouvee.

Ce deplacement n'est pas technique : aucune ligne de code n'a change. C'est la
separation des roles qui deplace la frontiere. L'organisation qui a un interet
au resultat n'est plus celle qui detient les moyens de le trahir.

**Ce qui protege alors l'organisation de VERA lui-meme.** La question se
retourne legitimement : l'operateur devient a son tour le Niveau 2 potentiel.
Quatre elements y repondent, dont trois sont verifiables sans nous faire
confiance :

- Le code est integralement publie, primitive cryptographique comprise
  (`vera_blind_sig/`, 91 lignes de liaison autour d'une bibliotheque publique).
- `Cargo.lock` fige les dependances : une recompilation produit la meme chaine.
- **Le client servi au votant est verifiable** : ses empreintes SHA-256 sont
  publiees et comparables en deux commandes (`VERIFICATION_CLIENT.md`). Cela
  ferme le vecteur le plus direct -- un JavaScript modifie qui recopierait le
  secret avant l'aveuglement -- mais **pas les deux autres listes plus haut** :
  la correlation entre les requetes de signature et de vote via des journaux
  que l'operateur controle, et la substitution de cle par votant (l'empreinte
  `#k=` etant calculee par le serveur lui-meme, elle ne l'engage pas). Un
  vecteur sur trois, pas la totalite.
- VERA n'a aucun interet dans le resultat d'une consultation, contrairement a
  l'organisation qui la commande. Cet argument-la n'est pas verifiable ; il ne
  vaut que ce que vaut une structure sans enjeu dans le sujet consulte.

**Ce qui reste non prouve.** Que le serveur execute le Python publie. Le code
serveur n'est pas transmis au visiteur, donc rien ne permet de le comparer.
L'etablir exigerait une attestation materielle (SEV-SNP, TDX ou equivalent),
dont VERA ne dispose pas. La consequence est bornee : un serveur modifie
pourrait refuser des votes, en fabriquer ou alterer un resultat -- ce qui
releve de l'integrite du scrutin, deja documentee comme non garantie -- mais il
ne pourrait plus relier une reponse a une personne, le client etant verifiable.

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

Cette lecture donne le QUOI. Reste le QUI -- et c'est ici que ce document
affirmait, a tort, que le probleme etait clos.

**Ce qui etait ecrit, et qui est faux :** « pour desanonymiser, il faut une
source temporelle EXTERNE placant une personne dans la sequence, et ces canaux
sont fermes ». Les canaux externes le sont effectivement -- journaux des routes
de vote coupes, jeton en fragment d'URL jamais transmis, horodatage retire,
table anti-rejeu en `WITHOUT ROWID`.

**Mais la source n'a pas besoin d'etre externe.** La table des jetons
d'autorisation est dans le MEME fichier. La consommation d'un jeton y inscrit
`utilise = 1` au moment de la demande de signature, quelques secondes avant que
le compteur ne s'incremente. Un operateur qui sonde la base observe donc les
deux moities de l'appariement sans rien d'autre a sa disposition :

    empreinte du jeton  ->  utilise = 1
                        ->  compteur « oui » +1

Reproduit empiriquement le 13/08. L'empreinte du jeton identifie la personne
des lors que l'organisation detient la liste (personne -> jeton), ce qui est le
cas par construction.

**Ce qui protege reellement**, et il faut le dire ainsi : l'operateur a la base
sans la liste, l'organisation a la liste sans la base. C'est une separation des
ROLES, pas une fermeture des ancres temporelles. Voir `LIMITS.md` §9, « les
canaux temporels forment une classe ».

Chiffrer ces tables serait illusoire : l'operateur detient `VERA_DB_KEY`, elle
est dans son unite systemd.

**Regle de deploiement :** ne pas decouper une consultation en departements
dont l'effectif attendu approche ou passe sous K_MIN. Non seulement le resultat
ne sera pas publiable, mais les comptes existent en base pendant toute la
consultation.

### Continuite de service : une dependance non technique

La cle de chiffrement de la base (`VERA_DB_KEY`) conditionne tout redemarrage.
Le fail-closed refuse de demarrer sans elle -- comportement voulu, puisqu'il
evite de regenerer des cles et d'invalider silencieusement les liens en
circulation. Consequence : sans cette cle, les donnees persistees sont
definitivement illisibles.

Elle est conservee hors du serveur par le mainteneur. Cela couvre la perte du
serveur ; cela ne couvre pas l'indisponibilite du mainteneur. Si le service
s'arrete pendant une consultation et n'est pas redemarre sous sept jours, les
cles de signature expirent : les liens deviennent inutilisables et les resultats
non publies sont perdus.

**Ce qui manque :** un depot de cette cle chez un tiers, avec une procedure de
reprise ecrite. C'est la principale dependance non technique du systeme, et la
seule facon de rendre la continuite independante d'une personne. Toute
organisation dont la consultation a un enjeu reel devrait l'exiger avant
deploiement (voir `GUIDE_DEPLOIEMENT.md`).

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
| Bornes de clamp | **(0, 10 000 000)** | Descripteur de domaine OpenDP ; `scale` est passe explicitement, la borne n'entre pas dans la calibration. Portee de 10 000 a 10 M le 13/08 : une exception levee au-dela creait une branche dependante des donnees, donc une perte de confidentialite non bornee sur cet evenement |
| K_MIN | 240 | Seuil MESURE : a n=240 l'erreur max reste sous 5 % dans 95 % des publications. En dessous : n=200 → 6 %, n=150 → 8 %, n=100 → 12 % |
| Signature aveugle | RSABSSA-SHA384-PSS-Randomized (RFC 9474) | Modules 2048 bits, `blind-rsa-signatures` 0.17.2 |
| Bourrage constant | 200 octets | > 100 (departement max) + 10 (« abstention ») |
| Chiffrement cle RSA | Fernet + PBKDF2-SHA256 | 100 000 iterations, sel aleatoire par enregistrement (derivation de la CLE DE BASE depuis `VERA_DB_KEY` -- a ne pas confondre avec les 200 000 iterations des mots de passe d'administration, Porte 22) |
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
| 7 | Differenciation « 49/1 » | Fermee | RSABSSA RFC 9474. Aveuglement et finalisation dans le navigateur du votant : le serveur ne voit ni le secret K ni la signature finale. Une cle RSA par departement, ce qui empeche de deplacer une voix d'une urne a l'autre. Le lien porte l'empreinte de l'ENSEMBLE des cles -- identique pour tous les votants, donc comparable entre collegues -- et le client verifie trois choses : concordance avec le lien, unicite de la cle par groupe, appartenance de la cle recue a l'ensemble |
| 8 | Inference sur le repondant atypique | Fermee | Meme mesure que porte 2. TPR@1%FPR = 1.6 % |
| 9 | Collusion emetteur / agregateur | Fermee **au sein d'une organisation** | Secret admin distinct, comptes separes. **Porte sur l'AUTHENTIFICATION, pas sur les donnees** : les tables sont indexees par departement seul, jamais par (compte, departement). Deux organisations distinctes sur une meme instance partageraient urne, cle et budget -- d'ou l'invariant « une instance = une organisation » (`LIMITS.md` §11) |
| 10 | Sondage binaire (seuil) | Fermee | Refus de publier sous K_MIN=240, verifie avant toute consommation de budget. Effectif exact des petites cohortes non expose |
| 11 | Acces direct a la base / cle RSA | Fermee | Chiffrement Fernet, sel aleatoire par enregistrement. Fail-closed : si des cles existent mais qu'aucune ne se dechiffre, le service refuse de demarrer plutot que d'en regenerer |
| 12 | Secret admin visible dans `/proc` | Limite assumee | Contexte solo-root |
| 13 | Soustraction d'agregats | Limite assumee | Limite irreductible de la DP, attenuee par publication unique par consultation — meme reserve que porte 4 |
| 14 | Persistance de l'etat de confidentialite | Fermee | SQLite en `journal_mode=DELETE` (voir Porte 17 : le WAL joignait les deux registres). Verifie par `kill -9` et par reboot systeme complet. Complete par un effacement ACTIF a la cloture : compteurs, effectifs, jetons, budget, resultats publies et cle de signature detruits en une transaction, suivie de `VACUUM`. **Consequence a connaitre** : un resultat publie disparait du serveur a la cloture. Il doit donc etre sauvegarde par l'organisation ET par les representants du personnel avant de cloturer -- `/api/resultats_publies` le sert tant que la consultation vit, pas apres |
| 15 | Trafic en clair | Fermee | HTTPS via Nginx + Let's Encrypt, redirection 301, renouvellement automatique |
| 16 | Retention des journaux | Fermee | Purge manuelle a la cloture + logrotate 3 jours. L'access log applicatif est desactive (voir porte 26) |
| 17 | Correlation temporelle en base | **Fermee au niveau de la table, bornee au niveau du journal** | Horodatage retire, table anti-rejeu en `WITHOUT ROWID` : ordonnee par empreinte SHA-256 pseudo-aleatoire, l'ordre d'insertion n'existe plus DANS LA TABLE. Le fichier journal, lui, est un autre sujet -- voir ci-dessous |
| 18 | Generation de cles a la volee (DoS keygen) | Fermee | Les endpoints publics sont en lecture seule (404 si le departement n'existe pas) ; la creation de cle est reservee au flux RH authentifie |
| 19 | API exposee hors TLS | Fermee | uvicorn ecoute sur `127.0.0.1` ; Nginx est l'unique chemin d'acces |
| 20 | Publication declenchee par une lecture | Fermee | `GET /api/rh/resultats` est en lecture pure ; la publication est un `POST /api/rh/publier` explicite, avec confirmation. Ferme aussi le CSRF (le cookie `SameSite=Lax` laisse passer les GET de navigation) |
| 21 | Longueur de requete revelant le groupe | Fermee | Le nom du groupe transitait dans l'URL de `GET /api/cle_publique`, dont la longueur variait avec lui -- un observateur passif classait les votants par service. Ferme par bourrage de la REQUETE : le client ajoute un parametre `pad=` ignore du serveur, portant toute URL a 355 octets quel que soit le nom. Verifie sur 2, 17 et 44 caracteres. Reste une propriete du client : un client modifie ne bourrerait pas |
| 22 | Saturation du threadpool | Fermee | La connexion RH declenche un PBKDF2 200 000 iterations a chaque appel (mots de passe d'administration ; la cle de base utilise 100 000, voir plus haut) et partage le threadpool avec le depot de vote. Rate-limit Nginx dedie (1 r/s, rafale 5) : verifie en production, 4 requetes passent puis 429 |
| 23 | En-tetes de securite HTTP | Fermee | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy `no-referrer`. `server_tokens off` : la version exacte du serveur n'est pas annoncee dans les reponses |
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

### Le controle d'unicite, garantie peu visible mais decisive

Le client ne se contente pas de comparer l'empreinte de l'ensemble des cles a
celle inscrite dans son lien. Il verifie aussi qu'un groupe n'a **qu'une** cle.

Ce second controle est celui qui compte. Un serveur malveillant pourrait
publier cinq cents couples (Marketing, cle_i) : l'empreinte agregee serait
parfaitement valide, et la desanonymisation aussi -- chaque votant recevrait sa
propre cle, et le depouillement dirait qui a produit quelle signature. C'est le
COMPTAGE qui ferme l'attaque, pas le hachage.

Cette propriete est mentionnee ici parce qu'elle ne se devine pas : l'empreinte
agregee a l'air de suffire, et elle ne suffit pas.

### Correlation entre les deux requetes du parcours, limite assumee

Une date d'ouverture des depots a ete ajoutee. Ce qu'elle ferme et ce qu'elle
ne ferme pas doit etre dit precisement, faute de quoi elle donne un faux
sentiment de securite.

**Ce qu'elle ferme.** L'organisation envoie ses invitations dans un ordre
qu'elle connait, etale sur plusieurs heures ou jours. Sans date d'ouverture,
chacun vote dans la foulee de sa reception : l'ordre des votes reproduit alors
l'ordre des envois, connu de l'organisateur personne par personne. Dans un
petit groupe, cela suffit a attribuer chaque reponse. La date brise ce lien.

**Ce qu'elle ne ferme pas.** Signature et depot s'ouvrent au meme instant. Un
votant qui arrive apres la date obtient son credential puis depose quelques
secondes plus tard. Un operateur qui journalise les deux requetes peut les
rapprocher : la premiere porte le jeton, donc l'identite via la liste de
l'organisation ; la seconde porte la reponse.

**Pourquoi ce canal reste ouvert.** Le fermer exigerait deux visites du votant
-- obtenir son credential, revenir plus tard pour deposer. C'est un cout
d'usage considerable pour une menace qui suppose deja un operateur activement
malveillant, c'est-a-dire le Niveau 2 place hors garantie en section 1. Les
journaux nginx sont par ailleurs coupes sur ces deux routes, ce qui retire le
moyen le plus simple de conserver cette information.

**Consequence pour l'organisation.** Cette limite s'ajoute a celles qui font
que l'hebergement doit etre assure par un tiers distinct de l'organisation qui
consulte.

### Le journal d'ecriture, limite bornee et non fermee

La table ne conserve aucun ordre. Le fichier journal, si -- pendant un temps.

SQLite fonctionnait en mode WAL jusqu'au 13/08 : chaque validation ecrivait une image ordonnee de
la page modifiee. Comme un vote incremente la ligne (departement, reponse) qui
lui correspond, comparer deux images successives revele quelle case a bouge,
donc ce qu'a repondu le n-ieme votant. Verifie empiriquement : sur une sequence
oui/non/oui/abstention/oui/non, le journal restitue l'ordre exact.

`secure_delete=ON` n'y change rien -- il ecrase les octets d'une ligne
supprimee, il ne rembobine pas un journal. Et le `wal_checkpoint(TRUNCATE)` de
la cloture ferme le cas APRES, pas PENDANT : or c'est pendant la consultation
qu'un instantane d'hebergeur ou une copie de diagnostic sont pris.

**Ce qui a ete fait, en deux temps.**

*Premiere mesure (06/08), insuffisante.* Le journal etait tronque toutes les 20
ecritures. Sur 201 votes, sa taille ne dependait plus du nombre de votes mais de
l'intervalle de troncature -- maximum 354 Ko. Mais **au plus 20 votes recents
restaient ordonnes a tout instant** : la fenetre etait bornee, pas supprimee.

*Correctif definitif (13/08) : `journal_mode=DELETE`.* Aucun journal ne persiste
plus entre deux transactions. Le journal de rollback contient l'image d'AVANT
pendant la transaction, et disparait au commit. Il n'y a plus de fenetre.

**Ce qui a decide l'arbitrage.** Un audit a montre que la fenetre de 20 votes ne
livrait pas seulement l'ORDRE des votes, mais leur ATTRIBUTION : la consommation
d'un jeton -- qui porte l'empreinte du jeton, donc l'identite via la liste de
l'organisation -- s'ecrivait dans le meme journal que l'increment du compteur, a
quelques millisecondes d'intervalle. Un lecteur du seul fichier journal
reconstituait

    empreinte du jeton d'ALICE  ->  compteur « oui » +1

Reproduit empiriquement le 13/08. Les deux registres que le protocole tient
disjoints etaient joints au niveau du stockage, et une lecture UNIQUE suffisait.

**Le cout, mesure.** 632 votes/seconde en `DELETE` contre 1450 en WAL sur le
seul chemin de persistance. Le systeme complet plafonne a 42 votes/seconde
(cryptographie et reseau) : le journal n'est pas le goulot.

**Ce qui reste ouvert.** La lecture repetee du fichier `.db` lui-meme. Les
compteurs sont exacts et modifies a chaque vote : deux lectures successives
donnent la reponse du votant intervenu entre les deux. Voir `LIMITS.md` §9 --
c'est une condition d'exploitation, pas une propriete du code.

**Consequence pour l'hebergement, toujours valable.** Un instantane pris PENDANT
une consultation est plus revelateur qu'un instantane pris apres -- non plus a
cause du journal, mais parce que les compteurs vivants y figurent et qu'une
seconde copie permettrait la difference. Le guide de deploiement doit
le dire dans ce sens, et pas seulement mettre en garde contre la survivance
d'une copie anterieure.

### Les acteurs du dispositif, et ce que chacun detient

Le modele decrivait deux detenteurs de demi-secret. Il y en a davantage, et
trois n'etaient pas nommes.

| Acteur | Detient | Ne detient pas |
|---|---|---|
| **Organisation consultante** | la liste (personne -> invitation) | le serveur, la base |
| **Hebergeur (VERA)** | le serveur, la base, la cle | la liste |
| **Tiers attestant** (CSE, DPO) | l'effectif reel de reference | ni l'un ni l'autre |
| **Transporteur** (SMS, courriel) | la liste ET les jetons en clair | la base |
| **DNS / autorite de certification** | le pouvoir de servir un autre client | rien d'autre |

**Le tiers attestant est le seul ajout volontaire.** Il ne protege pas
l'anonymat -- il ne peut rien apprendre -- mais l'INTEGRITE : lui seul peut dire
que 240 invitations correspondent a 240 personnes reelles. Sans lui, la Porte 13
reste entierement ouverte. Voir `LIMITS.md` §0 et §13.

**Les deux derniers sont subis, pas choisis.** Le transporteur voit le couple
(numero, jeton) et pourrait voter a la place du destinataire. Qui controle la
zone DNS peut obtenir un certificat et servir son propre JavaScript -- ce qui
ramene au scenario Niveau 2. Voir `LIMITS.md` §12bis.

### Trois hypotheses sur lesquelles repose Delta_1 = 2

La sensibilite L1 vaut 2 : une substitution retire 1 a une case et en ajoute 1 a
une autre. Ce chiffre commande toute la calibration (scale = 4, eps = 0,5). Il
suppose trois choses, dont aucune n'est verifiee par le code.

**1. Les groupes forment une partition.** Si une personne appartient a deux
groupes publies -- « Marketing » et « Cadres », « Site Lyon » et
« Techniciens » -- une substitution modifie les compteurs des DEUX : L1 = 4, et
cette personne subit eps = 1,0 en une seule consultation. L'anti-rejeu porte sur
le secret, pas sur la personne : deux invitations donnent deux votes legitimes.
Voir `LIMITS.md` §11bis.

**2. La substitution reste dans le meme groupe.** L'appartenance est traitee
comme publique et fixe, etablie par l'organisation avant la consultation. Sans
cette hypothese, l'effectif de chaque groupe cesserait d'etre invariant et le
seuil K_MIN deviendrait une branche dependante des donnees. Voir `LIMITS.md` §1.

**3. Un votant ne repond qu'a une question.** Vrai par construction aujourd'hui
-- une consultation porte une question. Le chantier multi-questions doit
preserver cette propriete : avec q questions par votant, L1 = 2q.

### Deux invariants structurels

Ces deux proprietes ne sont garanties par aucun test, seulement par la
structure du code. Toute modification qui les romprait retablirait la liaison
entre une personne et sa reponse, sans qu'aucune alerte ne se declenche.

**Les deux registres ne sont jamais joints.** Le jeton d'autorisation (emission)
et l'empreinte du secret depense (anti-rejeu) sont deux tables distinctes,
sans cle commune. Les joindre recreerait le lien identite vers vote que tout le
protocole existe pour empecher.

**Un jeton d'autorisation donne droit a une seule signature, dans une seule
epoque.** C'est ce qui empeche un votant d'obtenir plusieurs credentials
valides a partir d'une meme invitation.

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
- `vera_blind_sig/README.md` — primitive cryptographique et procedure de
  verification
