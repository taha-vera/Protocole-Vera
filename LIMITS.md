# VERA — Limites assumees

Ce document enonce ce que VERA NE protege PAS, ou protege seulement sous
certaines conditions. Un modele de menace qui cache ses limites n'a aucune
valeur.

## 1. Le contenu des reponses est protege ; la participation ne l'est pas toujours

VERA garantit qu'on ne peut pas apprendre COMMENT un individu a repondu (bruit
differentiel, eps=0.5). Il ne garantit PAS, en toute generalite, qu'on ne puisse
pas apprendre QU'UN individu a participe.

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
RESOLU le 23/07/2026 (refactor Modele B). Cette section decrivait auparavant
une limite architecturale : le serveur executait l'integralite du protocole
RSABSSA (aveuglement ET finalisation), produisait le token complet, et pouvait
donc relier identite et acte de vote. Ce n'est plus le cas.

Etat actuel : l'aveuglement et la finalisation ont lieu dans le NAVIGATEUR du
votant (static/vote.html, bibliotheque auto-hebergee). Le serveur ne recoit
qu'un message deja aveugle, ne voit jamais le secret K ni la signature finale,
et les deux registres (jetons d'autorisation, empreintes de votes consommes)
sont disjoints, sans horodatage, sans ordre d'insertion. Verifie bout-en-bout :
chantier_crypto/test_vote_complet.mjs et test_brique7.mjs.

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

VERA empeche que cette information se propage dans le
traitement des reponses, mais ne l'efface pas cote organisateur. La cryptographie
ne peut pas retirer cette connaissance initiale.

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

Ce qui reste protégé, et c'est l'essentiel : **aucun vote individuel n'existe
en base.** Les votes sont agrégés à l'écriture (compteur `département → réponse
→ total`), jamais stockés ligne par ligne. Un accès au fichier révélerait donc
« le département X a 45 oui / 30 non », mais jamais qui a voté quoi. L'anonymat
des participants — l'invariant central de VERA — n'est pas affecté.

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
