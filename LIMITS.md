# VERA — Limites assumees

Ce document enonce ce que VERA NE protege PAS, ou protege seulement sous
certaines conditions. Un modele de menace qui cache ses limites n'a aucune
valeur.

## 1. Le contenu des reponses est protege ; la participation ne l'est pas toujours

VERA garantit qu'on ne peut pas apprendre COMMENT un individu a repondu (bruit
differentiel, eps=0.5). Il ne garantit PAS, en toute generalite, qu'on ne puisse
pas apprendre QU'UN individu a participe.

**Un cache en memoire, pendant une heure.**

L'idempotence de la signature conserve, en memoire de processus et jamais sur
disque, le couple (empreinte du jeton, empreinte du message aveugle) avec la
signature emise. C'est exactement le lien que ce protocole existe pour ne pas
conserver — il permet a un votant dont la finalisation a echoue de rouvrir son
lien et de retrouver sa signature au lieu de perdre sa voix.

Retention : une heure, purge physique a chaque lecture et a chaque ecriture,
vidage complet a la cloture. Il ne survit pas a un redemarrage du service.

Le risque est faible mais il n'est pas nul : un vidage de memoire ou une image
de machine virtuelle prise pendant cette heure contiendrait ce lien. Nous le
mentionnons parce que cette section inventorie ce que le systeme conserve, et
qu'une structure gardant precisement ce qu'on promet de ne pas garder merite sa
ligne.

**Deux traces de participation, a connaitre.**

*Sur l'appareil du votant.* La page de vote inscrit un marqueur local
(`vera_vote:` suivi de l'empreinte du jeton) pour reconnaitre un double clic ou
un rechargement. Il persiste apres la fermeture du navigateur. Une organisation
qui detient le jeton peut en calculer l'empreinte : sur un poste ou un telephone
qu'elle administre, elle peut donc etablir qu'une personne nommee a participe --
pas ce qu'elle a repondu. C'est la seule trace qui survit sur l'appareil, et
elle n'est pas effacable par VERA.

*Sur le serveur.* L'endpoint `/api/engagement_cles` est public et non
authentifie : il expose la liste des groupes consultes a quiconque connait
l'adresse du service, sans avoir recu de lien. C'est le prix de la
verifiabilite -- un tiers doit pouvoir controler l'engagement de cles sans
compte -- mais cela signifie que les noms de vos groupes ne sont pas
confidentiels. Nommez-les en consequence.

L'effectif total N d'un departement est publie exact. Cela repose sur un modele
d'adjacence par SUBSTITUTION : sous ce modele N est invariant, le publier ne
coute rien. Mais sous un modele d'AJOUT/RETRAIT, publier N exact revele la
participation. Si le simple fait d'avoir repondu est sensible dans votre
contexte, VERA sous sa forme actuelle ne protege pas cette information.

Mitigation partielle : l'effectif exact des cohortes sous le seuil K_MIN n'est
pas expose (message de refus et tableau de bord). Au-dessus du seuil, N est
publie exact.

## 2. Precision limitee sur les petites cohortes

A eps=0.5, l'erreur sur chaque option est d'environ 12% de l'effectif au 95e
centile pour n=100, et descend sous 5% seulement a partir de n=240. VERA refuse
de publier sous 240 participants. C'est le prix de l'anonymat a ce niveau de
garantie. VERA n'est adapte qu'aux organisations dont les groupes consultes
depassent 240 personnes.

## 3. VERA donne une tendance, pas un decompte exact

Le resultat publie est une estimation bruitee. Il distingue une majorite claire
d'une minorite, mais ne tranche pas un vote serre a quelques points (52/48).

## 4. Observateur reseau et metadonnees

VERA ne protege pas contre un observateur du reseau (qui vote, quand). La
protection contre la correlation temporelle passe par K_MIN, pas par un masquage
du timing. L'utilisateur soucieux de cet aspect doit utiliser un canal
anonymisant (VPN/Tor).

## 5. Coercition

Comme tout systeme de vote, VERA ne protege pas contre la coercition physique
directe. Limite partagee par l'ensemble des systemes de ce type.

## 6. Confiance dans l'organisateur au moment de l'emission

L'organisateur (RH) connait, au moment d'emettre les jetons, la correspondance
entre chaque jeton et la personne a qui il l'envoie -- c'est lui qui distribue
les liens. VERA empeche que cette information se propage dans le traitement des
reponses, mais ne l'efface pas cote organisateur. La cryptographie ne peut pas
retirer cette connaissance initiale.

RESOLU le 23/07/2026 (refactor Modele B) pour la partie serveur. Cette section
decrivait auparavant une limite architecturale supplementaire : le serveur
executait l'integralite du protocole
RSABSSA (aveuglement ET finalisation), produisait le token complet, et pouvait
donc relier identite et acte de vote. Ce n'est plus le cas.

Etat actuel : l'aveuglement et la finalisation ont lieu dans le NAVIGATEUR du
votant (static/vote.html, bibliotheque auto-hebergee). Le serveur ne recoit
qu'un message deja aveugle, ne voit jamais le secret K ni la signature finale,
et les deux registres (jetons d'autorisation, empreintes de votes consommes)
sont disjoints, sans horodatage, sans ordre d'insertion. Verifie bout-en-bout :
chantier_crypto/test_pont_complet.mjs et test_brique7_v2.mjs.

CE QUI SUBSISTE, et qui est la vraie limite : cette garantie vaut contre un
tiers et contre un operateur honnete-mais-curieux -- Niveau 1 du modele
d'adversaire (voir VERA_THREAT_MODEL_COMPLETE.md). Contre un operateur
ACTIVEMENT MALVEILLANT, elle ne tient pas : celui qui sert le JavaScript au
votant peut le pieger pour exfiltrer K avant l'aveuglement, celui qui detient
les cles privees peut fabriquer des votes, celui qui lit le trafic en clair
apres terminaison TLS peut correler. Aucune cryptographie ne protege contre
l'entite qui controle le code execute et l'infrastructure.

CONSEQUENCE PRATIQUE : pour qu'une organisation ne puisse pas desanonymiser ses
propres membres, VERA doit etre heberge par un TIERS distinct de l'organisation
consultante, et/ou le client doit etre verifiable independamment (build
reproductible, empreinte publiee). Si l'organisation heberge elle-meme, elle
est dans la base de confiance : VERA rend alors la desanonymisation PASSIVE
impossible (rien en base ne relie identite et reponse), mais ne remplace pas la
confiance envers l'hebergeur face a un adversaire actif.

## 7. Perimetre : consultation d'opinion, pas donnees de sante

VERA agrege des OPINIONS. Il n'est PAS concu pour des donnees de sante de
patients au sens RGPD article 9 (HDS, AIPD, MR-004 non couverts). Il peut servir
a des consultations de climat social en etablissement de sante, pas a traiter
des donnees cliniques individuelles.

## 8. Canal temporel du tableau de bord RH

Le tableau de bord (`/api/rh/etat_departements`) est un compteur live. Un
organisateur qui le consulte de façon répétée peut observer, au-dessus du
seuil K_MIN, l'arrivée des votes en temps réel (chaque vote incrémente le
compteur). Cela révèle le *rythme* de participation et l'instant de chaque
vote, mais jamais le *contenu* d'une réponse.

C'est la même classe de canal que la Porte 3 (corrélation temporelle) : la
participation et son timing ne sont pas masqués, seule la réponse l'est. Sous
le seuil K_MIN, l'effectif exact n'est de toute façon pas exposé (voir §1).
Pour un contexte où le timing de participation serait lui-même sensible, il
faudrait un rafraîchissement différé ou un arrondi du compteur — non
implémenté à ce jour, documenté ici comme limite assumée.

## 9. Ce que révèle le fichier de base de données au repos

La clé RSA privée est chiffrée au repos (Fernet/AES-128, Porte 11) : voler le
fichier `.db` sans la clé `VERA_DB_KEY` ne donne pas accès à la clé de
signature. En revanche, les données **agrégées** sont stockées en clair : noms
des départements, libellés des réponses, et compteurs cumulés par option.

Ce qui reste protégé : **aucun vote individuel n'existe en base.** Les votes
sont agrégés à l'écriture (compteur `département → réponse → total`), jamais
stockés ligne par ligne. Un accès **ponctuel** au fichier révélerait donc « le
département X a 45 oui / 30 non », mais pas qui a voté quoi.

**Cette sécurité vaut pour une lecture, pas pour deux.** Les compteurs sont
incrémentés en temps réel, un vote à la fois. La différence entre deux lectures
successives donne la réponse exacte du votant intervenu entre les deux. Aucun
bruit ne s'y oppose : le mécanisme de confidentialité différentielle agit à la
publication, pas à l'écriture.

Le risque naît de la **composition** avec deux autres limites de ce document,
chacune acceptable prise isolément :

- §4 admet qu'un observateur réseau voit qui vote et quand ;
- §8 admet que le tableau de bord affiche la participation en temps réel, donc
  l'instant de chaque vote ;
- la présente section décrit des compteurs lisibles et incrémentés en direct.

**Et la source temporelle n'a même pas besoin d'être extérieure.** La table des
jetons d'autorisation est dans le même fichier : la consommation d'un jeton y
inscrit `utilise = 1` au moment de la demande de signature, quelques secondes
avant que le compteur ne s'incrémente. Un adversaire qui lit la base en continu
observe donc les deux moitiés de l'appariement sans rien d'autre à sa
disposition :

    jeton X passe à utilisé        →     compteur « oui » +1

Reproduit empiriquement le 13/08. Il lui manque encore la correspondance
personne → jeton, que détient l'organisation consultante — c'est cette
séparation qui protège, et elle est procédurale. Voir
`VERA_THREAT_MODEL_COMPLETE.md`, section « Niveau 1 ».

Un adversaire disposant de l'une de ces sources temporelles **et** d'une lecture
répétée du fichier reconstitue des votes individuels. Chiffrer les compteurs n'y
changerait rien : c'est la modification d'une ligne qui porte l'information, pas
son contenu — et le journal d'écriture conserve chaque version successive
(voir `VERA_THREAT_MODEL_COMPLETE.md`, section sur le journal).

Le modèle de menace exclut donc non seulement le vol du fichier, mais **toute
lecture répétée** : sauvegardes incrémentales, réplication, instantanés
d'hyperviseur, agent de supervision lisant `/root`. C'est une condition
d'exploitation, pas une propriété du code — elle doit figurer dans les
engagements pris avec l'hébergeur.

Cette exposition des agrégats en clair est acceptable dans le modèle de menace
retenu : le fichier est déjà protégé par le système d'exploitation et l'accès
SSH, et les compteurs agrégés sont de toute façon destinés à être publiés
(sous forme bruitée). Une organisation dont la simple structure de consultation
serait elle-même sensible devrait chiffrer le volume au niveau système
(LUKS/dm-crypt), ce qui sort du périmètre de VERA.

Vérifié par test_chiffrement_repos.py.

## 10. Duree maximale d'une consultation : 7 jours

Une consultation VERA a une duree de vie DURE de 7 jours a compter de son
ouverture. Passe ce delai, les cles de signature sont automatiquement detruites
(en memoire et en base) et plus aucun vote n'est accepte : les votants qui
ouvrent leur lien recoivent une erreur "Aucune consultation active".

Ce n'est pas un parametre de confort : la cle privee ne doit pas exister
indefiniment, et sa destruction automatique garantit qu'une consultation
oubliee ne laisse pas de materiel cryptographique actif sur le serveur.

CONSEQUENCE PRATIQUE POUR L'ORGANISATEUR : la fenetre de participation doit
etre planifiee dans ces 7 jours, relances comprises. Combinee au seuil
K_MIN=240, cette contrainte impose de distribuer les liens rapidement et de
relancer tot -- un departement qui n'atteint pas 240 reponses avant
l'expiration ne publiera aucun resultat.

Historique : cette duree etait de 48h jusqu'au 24/07/2026, et n'etait
documentee nulle part. Elle entrait en contradiction avec K_MIN=240 (reunir 240
reponses en deux jours suppose un taux de participation irrealiste dans une
organisation), au point qu'une consultation risquait de ne jamais rien publier,
le RH ne voyant que "effectif insuffisant" a l'expiration. Portee a 7 jours ; le
gain de securite de la valeur precedente etait marginal, la cle etant chiffree
au repos et l'operateur capable de la dechiffrer detenant VERA_DB_KEY de toute
facon.

## 11. Une instance VERA = une organisation consultante

VERA permet de creer plusieurs comptes administrateurs (endpoint protege par un
secret d'administration distinct). Cette fonction sert a avoir PLUSIEURS
ADMINISTRATEURS D'UNE MEME ORGANISATION -- separation des roles, tracabilite de
qui a genere quelles autorisations. Elle ne permet PAS d'heberger plusieurs
organisations distinctes sur une meme instance.

Raison : la separation ne porte que sur l'authentification. Les DONNEES ne sont
pas cloisonnees. Les tables compteurs_votes, cle_rsa_active, budget_epsilon et
jetons_autorisation sont indexees par departement SEUL, jamais par le couple
(compte, departement). Deux organisations creant chacune un departement
"Marketing" partageraient donc :
- la meme urne (les votes de l'une compteraient dans les resultats de l'autre) ;
- la meme cle de signature ;
- le meme budget epsilon (l'une pouvant epuiser celui de l'autre).

INVARIANT DE DEPLOIEMENT : une instance = une organisation. Chaque organisation
consultante doit disposer de sa propre installation, avec sa propre base et sa
propre cle de chiffrement. C'est aussi la configuration la plus sure : le
cloisonnement est obtenu par construction, pas par du code applicatif qui
pourrait etre contourne par un bug.

Un vrai multi-tenant exigerait de re-cler ces quatre tables par (compte,
departement), avec la migration correspondante. Ce n'est pas fait, et ce n'est
pas necessaire tant que chaque organisation dispose de son instance.

## 12. Les comptes administrateurs ne survivent pas a un redemarrage

Les comptes RH sont stockes en memoire du processus (dictionnaire
_comptes_rh dans vera_admin_auth.py), sans aucune persistance. Un compte cree
via /api/rh/creer_compte disparait donc au prochain redemarrage du service.

Seul le compte principal survit : il est recree a chaque demarrage a partir des
variables d'environnement VERA_ADMIN_USER et VERA_ADMIN_PASS, definies dans
l'unite systemd.

Ce n'est pas un oubli mais une consequence de la doctrine de VERA : rien de
sensible au repos. Persister des empreintes de mots de passe, meme salees,
creerait une cible qu'un vol de disque ou une sauvegarde qui fuite pourrait
exploiter hors ligne. Le choix est assume : les comptes additionnels sont
TEMPORAIRES PAR CONSTRUCTION et doivent etre recrees apres un redemarrage.

Portee pratique limitee : la creation de comptes n'est pas exposee dans
l'interface d'administration. C'est une operation d'operateur technique,
effectuee en ligne de commande avec le secret d'administration, par quelqu'un
qui connait le systeme. Un organisateur n'y est jamais confronte.

Si un jour plusieurs administrateurs permanents devenaient necessaires, la voie
propre serait de les declarer dans l'unite systemd au meme titre que le compte
principal -- pas de les persister en base.

## 13. Integrite du scrutin : VERA garantit l'anonymat, pas la sincerite du resultat

C'est la limite la plus importante de ce document, et la plus facile a mal
comprendre : **VERA prouve que personne ne peut relier une reponse a une
personne. Il ne prouve pas que le resultat publie reflete un vrai scrutin.**

Ce que VERA garantit techniquement :

- une reponse ne peut pas etre reliee a la personne qui l'a emise (signature
  aveugle, registres disjoints, absence d'horodatage) ;
- un jeton d'autorisation ne peut servir qu'une fois (consommation atomique) ;
- une meme signature ne peut deposer qu'un vote (anti-rejeu sur l'empreinte
  du secret K) ;
- aucun resultat n'est publie sous le seuil K_MIN.

Ce que VERA ne garantit PAS :

- que les jetons emis correspondent a de vraies personnes distinctes. Le
  systeme genere le nombre de jetons qu'on lui demande ; il n'a aucune liste
  de reference, aucun annuaire, aucun moyen de savoir a qui un lien est envoye
  (c'est precisement ce qui protege l'anonymat) ;
- qu'aucun de ces jetons n'a ete utilise par l'organisateur lui-meme. Un
  organisateur qui genere 240 jetons et vote 240 fois obtient un resultat
  publie entierement fabrique, et rien dans les chiffres ne le trahit ;
- qu'un votant puisse verifier que sa voix figure dans le total. Il n'y a ni
  recu, ni urne publique, ni recomptage possible.

**Pourquoi ce n'est pas un defaut a corriger, mais un choix impose.** La
verifiabilite de bout en bout -- celle des systemes de vote type Belenios ou
Helios -- repose sur la publication d'une urne et d'un decompte EXACTS, que
chacun peut recompter. Or VERA publie un decompte BRUITE : c'est toute la
garantie de confidentialite differentielle. Les deux proprietes sont en
conflit direct, un total verifiable trahissant les individus que le bruit
protege. Les concilier exigerait une preuve a divulgation nulle de connaissance
attestant que le bruit a ete correctement ajoute a un ensemble de bulletins
publiquement engages. C'est un sujet de recherche, pas une option de
configuration.

VERA a donc choisi l'anonymat prouve plutot que l'integrite prouvee.

**Consequence pratique.** VERA convient a une consultation d'opinion ou le
commanditaire cherche reellement a savoir ce que pense son organisation.

Attention toutefois a ne pas se rassurer trop vite avec l'argument « un
organisateur qui falsifie son propre sondage se trompe lui-meme » : il n'est
vrai que si la consultation sert a INFORMER l'organisateur. Or un barometre
social sert souvent a COMMUNIQUER un resultat -- a une direction, a des
representants du personnel, a des salaries, a une tutelle. Dans ce cas
l'organisateur ne se trompe pas lui-meme, il trompe des tiers, et c'est
precisement le scenario qu'un delegue syndical ou un DPO a en tete.

Ne pas se rassurer non plus avec l'idee que « les participants verraient
l'ecart » : ils ne voient pas la liste de diffusion. Un organisateur qui
ajoute vingt invitations fictives et vote vingt fois n'est detectable par
aucun participant -- c'est exactement ce qu'implique le fait que VERA ne
connaisse pas la liste.

VERA ne convient PAS a un scrutin contraignant, electif ou juridiquement
opposable, ou l'organisateur pourrait avoir interet a fabriquer le resultat et
ou la contestation doit pouvoir s'appuyer sur une preuve.

L'integrite, dans le perimetre de VERA, repose sur des garanties
ORGANISATIONNELLES et non cryptographiques : le nombre d'invitations generees
par groupe est visible dans le tableau de bord et peut etre rapproche d'un
effectif reel connu ; un tiers (representant du personnel, commissaire aux
comptes, huissier) peut attester que la liste de diffusion correspondait a un
annuaire. VERA ne fournit pas ces garanties, il ne les empeche pas.

Cette limite est enoncee au votant sur la page de vote : *"VERA protege votre
reponse. Il ne verifie pas la liste des personnes invitees : c'est
l'organisateur qui l'etablit."*

## 14. Le budget epsilon ne survit pas a la cloture : regle d'usage sur le nombre de consultations

> **EN CLAIR, sans jargon.**
> La protection de VERA s'use si vous consultez plusieurs fois les MEMES
> personnes. Une ou deux consultations par an sur un groupe : protection
> solide. Quatre : encore correcte. Au-dela de six, un employeur curieux
> pourrait deviner qui a repondu quoi une fois sur vingt.
> **Regle simple : pas plus de quatre consultations par an sur le meme groupe.**
> VERA ne peut pas vous en empecher techniquement -- il ne sait pas qui sont
> vos membres, c'est ce qui protege leur anonymat. C'est donc a l'organisation
> de s'y tenir.


**Ce qui est garanti techniquement.** Chaque publication applique exactement
epsilon = 0.5 (Laplace, Delta_1 = 2, scale = 4). A l'interieur d'une
consultation, un departement ne peut publier qu'une seule fois : republier
renvoie le resultat fige, sans nouveau tirage de bruit -- sinon un appelant
pourrait moyenner N tirages et annuler la protection. Ce verrou fonctionne et
a ete verifie.

**Ce qui n'est pas garanti.** A la cloture, `budget_epsilon.reset()` remet le
compteur a zero. Une nouvelle consultation sur la meme population repart donc
avec un budget plein. Le budget est en realite **par consultation**, pas **par
cohorte** : reposer la meme question aux memes personnes k fois coute
epsilon = 0.5 * k sur ces personnes, sans que rien ne le mesure ni ne le
signale.

**Pourquoi ce n'est pas corrigeable techniquement.** La composition
differentielle porte sur les PERSONNES, pas sur les noms de groupes. Or VERA
n'a aucune notion d'identite persistante -- c'est precisement ce qui garantit
l'anonymat. Le seul identifiant disponible est le nom du departement, qui est :

- une approximation imparfaite (les effectifs changent entre deux
  consultations : ce n'est deja plus la meme population) ;
- controle par l'organisateur lui-meme, donc contournable en renommant
  "RH" en "RH 2".

Un blocage dur sur un identifiant que l'adversaire choisit librement ne
protege de rien contre un organisateur malveillant, et enfermerait un groupe
legitime apres N consultations. Le `reset()` n'est pas un defaut : il corrige
un vrai bug (un departement reutilisant un nom deja publie devenait
definitivement non publiable). La limite est structurelle.

**La protection est donc une REGLE D'USAGE, pas un verrou.**

### Bareme d'exposition cumulee

| Consultations | epsilon cumule | Protection | L'adversaire trouve juste | Verdict |
|---|---|---|---|---|
| 1 | 0.5 | ***** | 62 % | Forte |
| 2 | 1.0 | ****- | 73 % | Forte |
| **4** | **2.0** | ***-- | **88 %** | **Modere -- seuil recommande** |
| 6 | 3.0 | **--- | 95 % | Limite haute a ne pas franchir |
| 10 | 5.0 | *---- | 99 % | Faible |
| 20 | 10.0 | ----- | 99.99 % | La garantie ne veut plus rien dire |

Lecture de la colonne "l'adversaire trouve juste" : un observateur qui, avant
publication, hesite a pile ou face sur la reponse d'une personne, peut apres
publication atteindre ce niveau de certitude. A epsilon = 3, il se trompe une
fois sur vingt seulement -- c'est le seuil conventionnel de la certitude
statistique, celui a partir duquel un employeur pourrait agir. Au-dela, la
phrase affichee au votant ("personne ne peut savoir ce que vous avez
repondu") cesse d'etre defendable.

### Regle retenue

**Une organisation ne devrait pas publier plus de 4 consultations par periode
de 12 mois glissants sur la meme population** (epsilon cumule = 2.0).

Au-dela, la protection sort de la zone defendable publiquement. VERA ne
l'empeche pas techniquement -- il ne le peut pas -- mais l'organisation qui
depasse ce rythme doit savoir qu'elle degrade la garantie qu'elle a annoncee
a ses membres.

### Trois precisions, pour ne pas surestimer le risque

1. Les pourcentages ci-dessus sont un **plafond du pire cas theorique** : ils
   supposent un adversaire connaissant deja toutes les autres reponses sauf
   une, et des questions parfaitement correlees. L'inference reellement
   mesuree sur VERA est tres inferieure : AUC = 0.6209 (IC95%
   [0.6185, 0.6232]), a peine mieux que le hasard.
2. **K_MIN = 240 aide en pratique, mais ce n'est pas lui qui porte la
   garantie.** Le seuil compte face a un adversaire ordinaire : plus le groupe
   est grand, plus une reponse s'y fond.

   Il ne tient pas face a l'organisateur lui-meme. Rien ne l'empeche de generer
   240 invitations pour un groupe de quinze personnes reelles, d'en conserver
   225 et de voter 225 fois avec des reponses qu'il connait : la publication a
   lieu (240 >= K_MIN), il soustrait ses propres votes, et lit le profil des
   quinze autres. C'est le bourrage decrit en section 13, vu sous l'angle de
   l'anonymat plutot que sous celui de la sincerite.

   **Ce qui survit dans ce cas, c'est la borne epsilon.** Elle est une propriete
   du mecanisme et non des donnees : meme en connaissant 239 reponses sur 240,
   la certitude de l'adversaire sur la derniere reste bornee a environ 62 %
   (bareme ci-dessus). C'est la garantie formelle qui porte, pas le seuil.

   Consequence pour la formulation faite aux participants : ne pas promettre
   « vous etes noyes parmi 240 ». Cette phrase suppose que les 239 autres soient
   de vraies personnes, ce que le systeme ne verifie pas. La seule contre-mesure
   au bourrage est procedurale : faire attester par un tiers -- comite social,
   delegue du personnel -- que le nombre d'invitations emises correspond a un
   effectif reel.
3. La population evolue entre deux consultations (departs, arrivees), donc
   "la meme cohorte sur un an" surestime deja l'exposition reelle.
