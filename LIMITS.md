# VERA — Limites assumées

Ce document énonce ce que VERA NE protège PAS, ou protège seulement sous
certaines conditions. Un modèle de menace qui cache ses limites n'a aucune
valeur.

## 0. Ce que VERA delivre, en un chiffre

**Quatre questions par an et par population**, à trois options chacune (oui /
non / abstention). C'est le fait le plus decisif pour evaluer ce système, et il
ne se deduit d'aucune section prise isolement : il resulte de trois contraintes
traitees separement plus bas, que cette section reunit.

Il resulte de trois contraintes, chacune justifiee ailleurs dans ce document :

- **une consultation porte UNE question**, avec trois options fixes (oui / non /
  abstention). Ce n'est pas une limite d'interface : toute la calibration
  suppose trois cases (Delta1 = 2, K_MIN = 240 mesure sur trois options) ;
- **une publication par groupe et par consultation**, epsilon = 0,5 consomme ;
- **quatre consultations au maximum par periode de douze mois glissants** sur la
  même population (section 14).

**Ce que cela exclut.** Un barometre social classique compte vingt a soixante
items, croises par service, par anciennete, par statut. VERA ne peut pas en
produire un. Il produit quatre referendums d'entreprise par an.

**Ce a quoi cela convient.** Une question dont la réponse est assez sensible
pour justifier le dispositif : « estimez-vous votre charge de travail
soutenable », « faites-vous confiance a la direction », « avez-vous observe des
faits de harcelement ». Ce sont des questions qu'aucun formulaire nominatif ne
peut poser honnetement.

**Ces trois exemples ont un point commun genant : le commanditaire a un interet
au resultat.** C'est ce qui rend la question digne d'être posee anonymement, et
c'est aussi ce qui rend l'organisateur tentable. Les deux vont ensemble ; VERA
n'a pas d'usage ou ils se separent.

C'est pourquoi l'attestation de l'effectif par un tiers n'est pas une
recommandation mais une condition d'ouverture -- et **elle protège le votant, pas
seulement la sincerite du chiffre.** La section 14 le montre : un organisateur
qui genere 240 invitations pour quinze personnes reelles, en conserve 225 et vote
lui-même, soustrait ensuite ses propres reponses et lit le profil des quinze
autres. Le seuil de 240 ne les protège plus du tout ; seule la borne epsilon
subsiste. Sans tiers qui compare les invitations emises a l'effectif reel, VERA
ne mesure que ce que l'organisateur veut bien laisser mesurer -- et ne protège
que ceux qu'il veut bien laisser repondre.

Si votre besoin est un questionnaire, VERA n'est pas l'outil.

### Les cinq conditions du dispositif

Aucune n'est optionnelle, et aucune n'est tenue par le code seul.

| Condition | Ce qu'elle protège | Ce qui arrive sans elle |
|---|---|---|
| **240 réponses par groupe** | la dilution d'une réponse individuelle | rien n'est publié -- VERA refuse |
| **Hebergement par un tiers distinct** | la non-liaison identite/réponse | l'organisation détient la liste ET la base : elle peut apparier |
| **Attestation de l'effectif par un tiers mandate** | la sincérité du resultat | l'organisation peut fabriquer une partie des réponses, sans que rien ne le montre (section 13) |
| **Groupes sans recoupement** | l'exactitude du barème d'exposition | une personne presente dans deux groupes publiés subit L1 = 4, donc epsilon = 1,0 en une seule consultation (section 11bis) |
| **Transporteur independant de l'hebergeur** | la separation des demi-secrets | transporteur + hebergeur reunis reconstituent personne -> reponse (section 12bis) |

### Quatre natures de garantie, a ne pas confondre

Ce document melange, par necessite, des affirmations qui n'ont pas le même
statut. Les distinguer evite deux erreurs symetriques : croire qu'une regle
procedurale est tenue par le code, et croire qu'une garantie formelle depend de
la bonne volonte de quelqu'un.

| Nature | Exemples | Ce qui la tient |
|---|---|---|
| **Garantie formelle** | epsilon = 0,5 par publication, barème de la section 14 | une demonstration, independante des donnees |
| **Invariant logiciel** | anti-rejeu, registres disjoints, refus sous K_MIN, destruction des cles a 7 jours | le code, verifie par la suite de tests |
| **Condition d'exploitation** | hebergeur tiers, journaux desactives, absence de lecture repetee du fichier | le deploiement -- aucun test ne la voit |
| **Regle procedurale** | 4 consultations / 12 mois, attestation de l'effectif, groupes disjoints, transporteur independant | des humains -- VERA ne peut ni la verifier ni l'imposer |

**Les cinq conditions ci-dessus relèvent toutes des deux dernieres lignes.**
C'est le fait le plus important de ce document : ce qui protège reellement les
participants n'est pas garanti par le code, et ne peut pas l'être.

Les deux premieres sont connues. **Les trois dernieres le sont moins, et elles
sont de même rang.** Sans tiers qui compare le nombre d'invitations émises a
l'effectif réel, la section 13 reste entierement ouverte. Et un decoupage qui
croise deux criteres -- service et statut, site et metier -- fait silencieusement
payer le double a ceux qui se trouvent a l'intersection, sans que rien dans les
chiffres publiés ne le signale. Et un transporteur appartenant au même groupe
que l'hebergeur reunit a lui seul les deux moities que toute l'architecture
separe.

## 1. Le contenu des réponses est protège ; la participation ne l'est pas toujours

**Formulation exacte de la garantie, parce que la version courte est trompeuse.**
VERA fournit une garantie differentielle (eps = 0,5) **sur les sorties
publiées**, dans son modèle de menace et sous le respect de ses conditions
d'exploitation. Ce n'est pas la même chose que « personne ne peut apprendre
comment un individu a répondu ».

La difference n'est pas rhetorique. L'epsilon-DP borne ce qui se deduit d'une
SORTIE du mécanisme. Elle ne borne rien de ce qui est observable AUTOUR du
mécanisme : l'état interne pendant l'execution, le trafic reseau, le tableau de
bord, le comportement d'un operateur actif. Chacun de ces canaux est traite dans
les sections suivantes, et aucun n'est couvert par le bruit.

Il ne garantit PAS, en toute generalite, qu'on ne puisse pas apprendre QU'UN
individu a participe.

**Un cache en memoire, pendant une heure.**

L'idempotence de la signature conserve, en memoire de processus et jamais sur
disque, le couple (empreinte du jeton, empreinte du message aveugle) avec la
signature aveugle émise.

**Ce que ce cache revele exactement, et ce n'est pas ce qu'on croit d'abord.**
Il retient (empreinte du jeton -> empreinte du message AVEUGLE -> signature
aveugle). Le facteur d'aveuglement `r` ne quitte jamais le navigateur du votant :
sans lui, aucune de ces valeurs ne se raccroche au dépôt, qui porte `hash(K)` et
la signature finalisee. Le cache prouve donc seulement **qu'un jeton a obtenu une
signature** -- information que `jetons_autorisation.utilise = 1` publié déjà en
base, sans limite de retention. L'apport marginal est proche de zero.

Il permet a un votant dont la finalisation a echoue de rouvrir son lien et de
retrouver sa signature au lieu de perdre sa voix.

Retention : une heure, purge physique a chaque lecture et a chaque ecriture,
vidage complet a la clôture. Il ne survit pas a un redemarrage du service.

**La garantie du README promettait plus que le modele ne demontre.** Elle disait
« aucune reponse ne peut etre reliee a une personne par l'organisateur, ni par un
tiers, ni par quiconque lirait la base a un instant donne ». La reserve « a un
instant donne » ne qualifiait que le TROISIEME terme : « ni par un tiers »
restait absolu, alors qu'un operateur actif servant un client modifie est
precisement un tiers, et que la section suivante du meme document le reconnait.

Un relecteur precedent avait cru y voir une contradiction pure et s'etait
trompe -- la reserve existait bien. Un autre, le 03/09/2026, a vu ce qu'elle ne
couvrait pas. Reformule : **aucune des parties legitimes, prise isolement, ne
dispose de quoi relier une reponse a une personne**. La collusion et l'operateur
actif en sortent explicitement.

**Et les 62,25 % pouvaient se lire comme un taux de reidentification.** Les trois
hypotheses etaient enoncees, mais un lecteur presse retient le chiffre. Le README
dit desormais ce que ce n'est PAS avant de dire ce que c'est.

**Un commentaire qui exagere un risque en fabrique un.** Jusqu'au 26/08,
`vera_persistance.py` decrivait ce cache comme « exactement ce que le protocole
existe pour ne pas conserver » -- formulation plus alarmante que l'analyse
ci-dessus ne le justifie. Un relecteur externe l'a citee telle quelle pour
conclure a une violation de la garantie centrale. Le commentaire a ete aligne
sur cette section. Une surestimation ecrite dans le code produit de fausses
alertes aussi surement qu'une sous-estimation en cache de vraies.

Le risque est faible mais il n'est pas nul : un vidage de memoire ou une image
de machine virtuelle prise pendant cette heure contiendrait ce lien. Nous le
mentionnons parce que cette section inventorie ce que le système conserve, et
qu'une structure gardant précisément ce qu'on promet de ne pas garder merite sa
ligne.

**Quatre traces de participation, a connaitre.**

*Sur l'appareil du votant.* La page de vote inscrit un marqueur local
(`vera_vote:` suivi de l'empreinte du jeton) pour reconnaitre un double clic ou
un rechargement. Il persiste après la fermeture du navigateur. Une organisation
qui détient le jeton peut en calculer l'empreinte : sur un poste ou un telephone
qu'elle administre, elle peut donc etablir qu'une personne nommee a participe --
pas ce qu'elle a répondu. C'est la seule trace qui survit sur l'appareil, et
elle n'est pas effacable par VERA.

*Dans la taille des requêtes.* Le parcours de vote est bourré à longueur
constante. **Les trois etapes sont bourrees ; les chiffres qui figuraient ici
etaient faux ou incomparables** (constat d'un audit externe, 29/08/2026).

Ce qui est vrai : la taille ne varie pas avec le nom du groupe, ce qui est la
propriete recherchee. Ce qui etait faux : « depot (490 octets) » -- la requete
mesuree fait environ 1180 octets, le 490 designant la seule portion bourree avec
son echafaudage JSON, sans que rien ne le dise, tandis que le 1035 de l'URL
comptait l'URL entiere. Deux chiffres calcules sur deux bases differentes dans
la meme phrase.

Le cout n'etait pas theorique : un service informatique qui mesure une requete
sur le reseau lisait 1180 la ou le document annoncait 490, et concluait a une
divergence entre code publie et code servi -- le signal meme que tout le
dispositif de verification existe pour emettre.

**Et ces memes chiffres ont survecu cinq jours ailleurs.** Retires d'ici le
29/08, ils sont restes dans `VERA_THREAT_MODEL_COMPLETE.md` -- section 3 et
porte 21 -- jusqu'au 03/09, releves par un audit externe. Le correctif qui
denoncait un cas ferme au lieu d'une classe en avait ferme un. **Troisieme
occurrence de ce motif en deux semaines.** Une garde interdit desormais de
recopier ces totaux dans n'importe quel document.

**Et la sequestre de la cle etait traitee honnetement, mais invisible.** Le
modele de menace la nomme « la principale dependance non technique du systeme »
et decrit precisement ce qui arrive sans elle : sept jours d'arret detruisent une
consultation en cours. Le guide de deploiement y renvoyait une fois, en fin de
document. Le README n'en disait rien -- or c'est la deuxieme question d'un DPO,
apres « qui heberge ». Un audit externe l'a releve le 03/09/2026 comme le seul de
ses constats qui change ce qu'une organisation devrait exiger avant de signer.
C'est desormais en tete du README, avec l'exigence a formuler : depot de la cle
chez un tiers et procedure de reprise ecrite.

Le meme tableau ne decrivait que DEUX des trois etapes bourrees : la reponse de
`/api/signer_aveugle`, corrigee le 29/08, n'y figurait pas. Et la porte 21
datait la correction octets/caracteres du 21/08, sans dire qu'elle ne portait
alors que sur le client -- le serveur a attendu huit jours de plus.

Les valeurs cibles vivent dans le code, ou une garde les controle
(`tests/test_bourrage_client_serveur.py`) : `LONGUEUR_CIBLE_FIXE` pour le corps
du depot, `LONGUEUR_PAD_REPONSE` pour la reponse de signature, et la cible de
l'URL de cle publique. Les tailles totales en dependent et ne sont pas recopiees
ici -- une valeur derivee recopiee derive.

Le bourrage sert a ce qu'un observateur du réseau ne déduise pas le groupe de la
taille du paquet.

**Le correctif de 2021/08 n'avait ferme que le client.** Le 29/08/2026, un audit
externe a constate que le SERVEUR calculait encore son bourrage en caracteres :
`pad = "x" * max(0, LONGUEUR_PAD_REPONSE - len(departement))`. La reponse de
`/api/signer_aveugle` variait donc de 691 a 791 octets selon le nom du groupe --
« Operations » 691, accentue 692, « Securite generale » 695, « 日本支社 » 699.

C'est **la seule requete du parcours qui porte le jeton d'invitation**, donc
l'identite. Un observateur passif du trafic TLS partitionnait les demandes de
signature par service sans rien dechiffrer, et « Securite », « Operations »,
« Developpement » sont des noms de service ordinaires en France.

La garde `test_bourrage_client_serveur.py` ne controlait que `vote.html` : elle
a enterine le correctif partiel. **Sixieme occurrence du motif.** Corrige, la
cible portee de 120 a 400 octets -- `max_length=100` borne des CARACTERES, qui
valent jusqu'a quatre octets chacun -- et la garde couvre desormais les deux
cotes.

**Deux précisions qui ont coûté deux correctifs.** Le bourrage se calcule en
**octets UTF-8**, pas en caractères : un nom de 100 caractères accentués occupe
200 à 400 octets une fois encodé, et une première version comptant les
caractères laissait le bourrage retomber à zéro — le canal se rouvrait en
silence, précisément pour les noms les plus distinctifs. Corrigé le 21/08 sur
l'URL et sur le corps.

Et cela reste une **propriété du client** : un client modifié ne bourrerait pas.

*Par le nombre d'invitations.* `/api/engagement_cles` expose publiquement le
nombre d'invitations émises par groupe — c'est voulu, cela permet à un tiers de
le comparer à l'effectif réel (§13). Mais c'est aussi un **majorant public de
l'effectif** : un groupe de 12 invitations est un groupe de 12 personnes au
plus. La mitigation annoncée plus haut — « l'effectif exact des cohortes sous
K_MIN n'est pas exposé » — ne vaut donc que pour l'effectif *ayant répondu*, pas
pour la taille du groupe. Nommez vos groupes et dimensionnez-les en
conséquence.

*Sur le serveur.* L'endpoint `/api/engagement_cles` est public et non
authentifie : il expose la liste des groupes consultés a quiconque connait
l'adresse du service, sans avoir recu de lien. C'est le prix de la
verifiabilite -- un tiers doit pouvoir controler l'engagement de clés sans
compte -- mais cela signifie que les noms de vos groupes ne sont pas
confidentiels. Nommez-les en conséquence.

L'effectif total N d'un departement est publié exact. Cela repose sur un modèle
d'adjacence par SUBSTITUTION : sous ce modèle N est invariant, le publier ne
coute rien.

**Precision sur ce modèle, a ne pas laisser implicite.** La substitution
remplace un répondant par un autre DU MEME GROUPE. L'appartenance au groupe est
traitee comme une donnée publique et fixe : elle est etablie par l'organisation
avant la consultation, et VERA ne la choisit pas.

Cette hypothese n'est pas decorative. Si la substitution pouvait deplacer une
personne d'un groupe a l'autre, l'effectif de chaque groupe cesserait d'être
invariant -- un groupe perdrait une réponse, l'autre en gagnerait une. Le seuil
de publication K_MIN deviendrait alors une branche dependante des données :
deux bases voisines publieraient des ensembles de groupes differents, ce qui
fuit un bit. La sensibilite L1 resterait 2, donc le bruit resterait correctement
calibre, mais la DECISION de publier ne le serait plus.

Sous l'hypothese posee ici, ce problème n'existe pas.

**En revanche, sous un modèle d'AJOUT/RETRAIT**, publier N exact revele la
participation. Si le simple fait d'avoir répondu est sensible dans votre
contexte, VERA sous sa forme actuelle ne protège pas cette information.

Mitigation partielle : l'effectif exact des cohortes sous le seuil K_MIN n'est
pas expose (message de refus et tableau de bord). Au-dessus du seuil, N est
publié exact.

## 2. Precision limitée sur les petites cohortes

**Le bruit est ABSOLU, pas proportionnel.** L'erreur publiée vaut environ
**12 voix au 95e centile**, quel que soit l'effectif. Les pourcentages n'en sont
que la traduction :

    n =  240  ->  12 voix  =   5 %
    n =  500  ->  12 voix  =  2,4 %
    n = 1000  ->  12 voix  =  1,2 %
    n = 5000  ->  12 voix  =  0,24 %

**Ce chiffre est celui de la valeur PUBLIÉE, projection comprise.** VERA n'ajoute
pas seulement du bruit de Laplace : il projette ensuite le vecteur bruité sur le
simplexe {x >= 0, somme = N}, ce qui est du post-traitement — gratuit en epsilon,
et qui réduit l'erreur.

Mesure sur 20 000 tirages à n = 240, erreur maximale sur les trois cases :

| | 95e centile |
|---|---|
| Bruit de Laplace seul | 16,1 voix |
| **Après projection — valeur publiée** | **12,0 voix** |

**L'invariance en N a ete mesuree, pas supposee** (26/08/2026). Une lecture
attentive a souleve un doute legitime : la composante Laplace est invariante par
construction, mais le GAIN de la projection ne l'est pas evidemment -- la part
qui vient de la contrainte `x >= 0` pourrait dependre de la proximite des
compteurs a zero. La mesure ci-dessus ne portait que sur n = 240. Reprise a
quatre effectifs, 20 000 tirages chacun, avec la projection reellement
implementee :

| n | Laplace seul | Publie, apres projection |
|---|---|---|
| 240 | 16,4 | **12,0** |
| 500 | 16,4 | **12,0** |
| 1 000 | 16,1 | **12,0** |
| 5 000 | 16,4 | **12,0** |

L'invariance tient. La raison est analytique et confirme la mesure : loin de
zero, la contrainte `x >= 0` ne mord jamais, et la projection se reduit alors a
retrancher la moyenne du bruit -- une operation lineaire, independante de N. Sur
une repartition concentree (100 % sur une option), le clipping mord au contraire
et l'erreur DESCEND a 9,0 voix. Elle ne remonte dans aucun cas mesure.

*(Une version antérieure de cette section présentait les 12 voix comme le bruit
brut, et affirmait qu'un adversaire pouvait gagner un tiers de variance en
reprojetant lui-même sur la contrainte « somme = N ». C'était faux : VERA
applique déjà cette projection avant de publier. L'adversaire ne peut rien en
tirer de plus. La correction va dans le sens de la prudence — l'erreur réelle
n'est pas meilleure que 12 voix, elle l'est exactement.)*

VERA refuse de publier sous 240 **réponses**. C'est le prix de l'anonymat à ce
niveau de garantie.

**240 réponses, pas 240 personnes** — la confusion est facile et elle décide de
la faisabilité. L'effectif minimal d'un groupe vaut

    240 / taux de participation attendu

| Taux de participation | Effectif minimal du groupe |
|---|---|
| 60 % | 400 personnes |
| 40 % | **600 personnes** |
| 25 % | 960 personnes |
| 20 % | 1 200 personnes |

**Ce taux n'a jamais été mesuré sur VERA.** C'est l'inconnue principale du
projet, et la raison d'être du premier déploiement réel : tant qu'elle n'est pas
levée, l'effectif minimal reste une estimation. Dimensionner sur 40 % est
prudent sans être pessimiste ; descendre à 25 % double presque l'exigence.

VERA n'est donc adapté qu'aux organisations dont les groupes consultés dépassent
plusieurs centaines de personnes — l'ordre de grandeur, pas 240.

## 3. VERA donne une tendance, pas un decompte exact

Le resultat publié est une estimation bruitée. Il distingue une majorite claire
d'une minorite. Il ne tranche pas un vote serre a quelques points AU VOISINAGE
DU SEUIL : à n = 240, un écart 52/48 fait 10 voix contre ± 12 voix d'erreur
publiée (§2).

Sur une grande cohorte, en revanche, il le tranche très bien : a n = 5000, le
même ecart représente 200 voix contre les mêmes +/- 12. Le bruit etant absolu
(section 2), la capacite a trancher croit avec l'effectif.

## 4. Observateur reseau et metadonnees

VERA ne protège pas contre un observateur du réseau (qui vote, quand). **K_MIN
ne protège pas de cela** : le seuil porte sur la publication, pas sur
l'observation du parcours, et l'appariement décrit au §9 ne dépend pas de la
taille de la cohorte. Ce qui protège ici est la séparation des rôles, pas un
masquage du timing ni le seuil. L'utilisateur soucieux de cet aspect doit utiliser un canal
anonymisant (VPN/Tor).

## 5. Coercition

Comme tout système de vote, VERA ne protège pas contre la coercition physique
directe. Limite partagee par l'ensemble des systèmes de ce type.

## 6. Confiance dans l'organisateur au moment de l'émission

L'organisateur (RH) connait, au moment d'émettre les jetons, la correspondance
entre chaque jeton et la personne a qui il l'envoie -- c'est lui qui distribue
les liens. VERA empeche que cette information se propage dans le traitement des
réponses, mais ne l'efface pas cote organisateur. La cryptographie ne peut pas
retirer cette connaissance initiale.

RESOLU le 23/07/2026 (refactor Modele B) pour la partie serveur. Cette section
decrivait auparavant une limite architecturale supplementaire : le serveur
executait l'integralite du protocole RSABSSA (aveuglement ET finalisation),
produisait le token complet, et pouvait donc relier identite et acte de vote.
Ce n'est plus le cas.

### Ce qui protège du client modifie, et jusqu'ou

Le serveur sert la page de vote, donc le code qui aveugle. Un operateur qui
voudrait activement contourner le système pourrait servir un JavaScript
different. Voici l'état exact des parades.

**Ce qui existe.** La page declare l'empreinte SHA-384 du module cryptographique
(attribut `integrity`) : le navigateur refuse de l'executer si le fichier a
change en transit ou sur le serveur. Et `VERIFICATION_CLIENT.md` publié les
empreintes SHA-256 des deux fichiers servis, verifiables en deux commandes par
un tiers.

**Le build du bundle est reproductible, verifie le 23/08.** Le `package.json`
des tests cryptographiques et son `package-lock.json` vivaient hors du depot,
dans `/root/crypto_test`. Le depot publiait donc sept fichiers `.mjs` sans le
manifeste disant de quoi ils dependent, et la version de
`@cloudflare/blindrsa-ts` -- la bibliotheque qui realise l'aveuglement dans le
navigateur -- n'etait figee nulle part.

Une fois le verrou versionne, la reconstruction a ete tentee : sur une autre
machine, avec un Node de version differente, `esbuild` redonne le bundle publie
**au bit pres** -- meme SHA-256 `08e678cc...baa66`, meme empreinte SHA-384 que
l'attribut `integrity` de la page de vote. Deux builds successifs sont
identiques.

Rien n'introduit de variation ici : le bundle n'est pas minifie, esbuild ordonne
les modules par le graphe d'imports et non par le systeme de fichiers, et
n'insere ni horodatage ni chemin absolu. La commande, qui n'etait ecrite nulle
part, figure desormais dans le script `build` du manifeste. `npm ci` installe
exactement ce que le verrou decrit.

`test_bundle_reconstructible.py` reconstruit le bundle a chaque passage de la
suite et echoue s'il differe du fichier servi -- ou si deux reconstructions
successives different entre elles.

**Ce qui n'existe pas, et qu'il ne faut pas laisser croire.** La verification
detecte une divergence entre le code PUBLIE et le code SERVI. Depuis le 23/08
elle etablit aussi que le bundle publie derive de son code source, puisqu'il se
reconstruit a l'identique -- c'est la chaine qui manquait, et une version
anterieure de cette section affirmait a tort qu'elle etait hors de portee.

Mais elle ne protège toujours pas d'un serveur qui servirait une page
differente a un jeton cible : qui sert la page sert aussi l'attribut qui la
certifie. Et la reconstruction se verifie sur ce que le depot publie, pas sur ce
qu'un navigateur a reellement recu.

**Conclusion.** Contre un operateur actif, aucune vérification executee dans un
navigateur ne protège. Ce que ces mécanismes produisent est une trace : un ecart
constate serait opposable. C'est la séparation des roles qui protège, pas le
code.

Etat actuel : l'aveuglement et la finalisation ont lieu dans le NAVIGATEUR du
votant (static/vote.html, bibliotheque auto-hebergee). Le serveur ne recoit
qu'un message déjà aveugle, ne voit jamais le secret K ni la signature finale,
et les deux registres (jetons d'autorisation, empreintes de votes consommes)
sont disjoints, sans horodatage, sans ordre d'insertion. Verifie bout-en-bout :
chantier_crypto/test_pont_complet.mjs et test_brique7_v2.mjs.

CE QUI SUBSISTE, et qui est la vraie limite : cette garantie vaut contre un
tiers et contre un operateur honnete-mais-curieux -- Niveau 1 du modèle
d'adversaire (voir VERA_THREAT_MODEL_COMPLETE.md). Contre un operateur
ACTIVEMENT MALVEILLANT, elle ne tient pas : celui qui sert le JavaScript au
votant peut le pieger pour exfiltrer K avant l'aveuglement, celui qui détient
les clés privees peut fabriquer des votes, celui qui lit le trafic en clair
après terminaison TLS peut corréler. Aucune cryptographie ne protège contre
l'entite qui controle le code execute et l'infrastructure.

CONSEQUENCE PRATIQUE : pour qu'une organisation ne puisse pas désanonymiser ses
propres membres, VERA doit être héberge par un TIERS distinct de l'organisation
consultante. (La vérification independante du client est traitee ci-dessus :
elle detecte une divergence, elle ne remplace pas cette séparation.) Si l'organisation héberge elle-même, elle
est dans la base de confiance : VERA rend alors la désanonymisation PASSIVE
impossible (rien en base ne relie identite et réponse), mais ne remplace pas la
confiance envers l'hébergeur face a un adversaire actif.

## 7. Perimetre : consultation d'opinion, pas données de sante

VERA agrège des OPINIONS. Il n'est PAS concu pour des données de sante de
patients au sens RGPD article 9 (HDS, AIPD, MR-004 non couverts). Il peut servir
a des consultations de climat social en etablissement de sante, pas a traiter
des données cliniques individuelles.

## 8. Canal temporel du tableau de bord RH

Le tableau de bord (`/api/rh/etat_departements`) est un compteur live. Un
organisateur qui le consulte de façon répétée peut observer, au-dessus du
seuil K_MIN, l'arrivée des votes en temps réel (chaque vote incrémente le
compteur). Cela révèle le *rythme* de participation et l'instant de chaque
vote, mais jamais le *contenu* d'une réponse.

Sous le seuil K_MIN, l'effectif exact n'est de toute façon pas exposé (voir §1).
Pour un contexte où le timing de participation serait lui-même sensible, il
faudrait un rafraîchissement différé ou un arrondi du compteur — non implémenté
à ce jour, documenté ici comme limite assumée.

**Ce canal n'est pas isolé.** Il appartient à une classe de quatre canaux
temporels qui se composent entre eux — réseau, tableau de bord, état de la base,
journaux du serveur.
Ils sont traités ensemble au §9, sous « Les canaux temporels forment une classe »,
parce que leur danger vient de leur composition et non de chacun pris à part.

## 9. Ce que révèle le fichier de base de données au repos

La clé RSA privée est chiffrée au repos (Fernet/AES-128, Porte 11) : voler le
fichier `.db` sans la clé `VERA_DB_KEY` ne donne pas accès à la clé de
signature. En revanche, les données **agrégées** sont stockées en clair : noms
des départements, libellés des réponses, et compteurs cumulés par option.

Ce qui reste protégé : **aucun vote individuel n'existe en base.** Les votes
sont agrégés à l'écriture (compteur `département → réponse → total`), jamais
stockés ligne par ligne. Un accès **ponctuel** au fichier révélerait donc « le
département X a 45 oui / 30 non », mais pas qui a voté quoi.

**L'état interne est une sortie du mécanisme, et il n'est pas bruité.** C'est la
formulation qui rend cette section importante : la confidentialité différentielle
protège ce que le système **publie**. Elle ne protège pas ce qu'il laisse
observer pendant qu'il fonctionne.

Les compteurs en base sont exacts, non bruités, modifiés à chaque vote. Qui peut
les lire régulièrement obtient une sortie que le mécanisme DP n'a jamais
couverte — et cette sortie contourne entièrement la protection, quel que soit ε.

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

### Les canaux temporels forment une classe, pas quatre problèmes séparés

Quatre observations différentes livrent la même chose — l'instant de chaque
participation — et se composent entre elles :

| Canal | Ce qu'il livre | Qui y accède |
|---|---|---|
| Réseau | qui se connecte, et quand | observateur du réseau de l'organisation |
| Tableau de bord | évolution de la participation en direct | l'organisation elle-même |
| État de la base | évolution exacte des compteurs | qui lit le fichier de façon répétée |
| Journaux du serveur | IP et horodatage de chaque requête du parcours de vote | l'hébergeur |

Le deuxième mérite d'être souligné : **le système fournit lui-même ce canal à
l'organisation**. `/api/rh/etat_departements` affiche le nombre de réponses en
temps réel, ce qui, interrogé régulièrement, donne l'instant de chaque vote. Ce
n'est pas une fuite accidentelle, c'est une fonctionnalité — et elle est entre
les mains de celui dont les participants se méfient.

**Le quatrième mérite une précision, parce qu'il n'est fermé que par
configuration.** Les journaux nginx et uvicorn enregistreraient par défaut
l'adresse IP et l'horodatage de chaque requête du parcours de vote. Ils sont
désactivés sur ces routes précises — `access_log off` sur chacune, et
`error_log crit` pour que la limitation de débit n'y réinscrive pas les IP.

C'est une **condition d'exploitation, pas une propriété du code** : une
configuration nginx modifiée, un proxy en amont, un pare-feu applicatif ou un
agent de supervision rétabliraient ce canal sans qu'aucun test ne le voie. Un
test mécanique (`test_routes_non_journalisees.py`) vérifie que la configuration
du dépôt couvre toutes les requêtes de la page de vote — il ne vérifie pas la
configuration réellement servie.

Aucun de ces canaux n'est couvert par le bruit différentiel, pour la raison
donnée plus haut : ils portent sur l'état, pas sur la sortie publiée.

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

**L'outil du tiers verificateur echouait en s'ouvrant.** Constat du meme audit.
Les controles de `verifier_engagement.py` sur le seuil, l'epsilon et les
invitations etaient conditionnels : un serveur qui OMETTAIT ces champs ne
declenchait rien, et le script concluait « Aucune anomalie detectee ». Il
n'avait alors verifie aucun des trois parametres que le README lui attribue. Un
serveur sans cle sortait de meme en code 0 sans dire que l'empreinte fournie par
`--attendu` n'avait pas ete comparee, et un champ manquant faisait planter
l'outil sur une trace Python.

Le delegue du personnel a qui le guide demande de lancer ce script ne pouvait
pas distinguer « rien a signaler » de « le controle n'a pas eu lieu ».

`static/vote.html` documente pourtant avoir corrige exactement ce defaut : « une
defense de securite doit echouer en se fermant, pas en s'ouvrant ». Le client
avait ete mis au fail-closed, l'outil du tiers etait reste au fail-open. Corrige
le 29/08 : un champ absent est desormais une anomalie, pas un silence.

Un adversaire disposant de l'une de ces sources temporelles **et** d'une lecture
répétée du fichier reconstitue des votes individuels. Chiffrer les compteurs n'y
changerait rien : c'est la modification d'une ligne qui porte l'information, pas
son contenu.

*(Une version anterieure ajoutait ici que « le journal d'ecriture conserve chaque
version successive ». C'était vrai en `journal_mode=WAL`, abandonne le 13/08. En
`journal_mode=DELETE`, le journal de rollback ne contient que l'image d'avant
pendant la transaction et disparait au commit : il n'y a plus d'historique
persistant. La lecture répétée du fichier `.db` lui-même reste le vecteur.)*

**Deux fonctions de dérivation distinctes, à ne pas confondre.** Les mots de
passe d'administration utilisent PBKDF2-HMAC-SHA256 à **200 000** itérations
(`vera_admin_auth.py`). La clé de chiffrement de la base est dérivée de
`VERA_DB_KEY` par PBKDF2 à **100 000** itérations (`vera_persistance.py`). Deux
usages différents, deux paramètres différents — un document qui cite l'un des
deux sans préciser lequel crée une contradiction apparente.

**Une table survit a la clôture** : `historique_consultations`, qui note le nom
de chaque groupe consulté et la date. Elle sert a l'avertissement de frequence
(section 14) et ne contient ni réponse ni identite -- mais cette section se
voulant exhaustive, elle merite d'y figurer.

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

Une consultation VERA a une durée de vie DURE de 7 jours a compter de son
ouverture. Passe ce delai, les clés de signature sont automatiquement detruites
(en memoire et en base) et plus aucun vote n'est accepte : les votants qui
ouvrent leur lien recoivent une erreur "Aucune consultation active".

Ce n'est pas un paramètre de confort : la clé privee ne doit pas exister
indefiniment, et sa destruction automatique garantit qu'une consultation
oubliee ne laisse pas de materiel cryptographique actif sur le serveur.

CONSEQUENCE PRATIQUE POUR L'ORGANISATEUR : la fenetre de participation doit
être planifiee dans ces 7 jours, relances comprises. Combinee au seuil
K_MIN=240, cette contrainte impose de distribuer les liens rapidement et de
relancer tot -- un departement qui n'atteint pas 240 réponses avant
l'expiration ne publiera aucun resultat.

Historique : cette durée était de 48h jusqu'au 24/07/2026, et n'était
documentee nulle part. Elle entrait en contradiction avec K_MIN=240 (reunir 240
réponses en deux jours suppose un taux de participation irrealiste dans une
organisation), au point qu'une consultation risquait de ne jamais rien publier,
le RH ne voyant que "effectif insuffisant" a l'expiration. Portee a 7 jours ; le
gain de sécurité de la valeur precedente était marginal, la clé etant chiffree
au repos et l'operateur capable de la dechiffrer detenant VERA_DB_KEY de toute
facon.

## 11. Une instance VERA = une organisation consultante

VERA permet de creer plusieurs comptes administrateurs (endpoint protège par un
secret d'administration distinct). Cette fonction sert a avoir PLUSIEURS
ADMINISTRATEURS D'UNE MEME ORGANISATION -- séparation des roles, tracabilite de
qui a génère quelles autorisations. Elle ne permet PAS d'heberger plusieurs
organisations distinctes sur une même instance.

Raison : la séparation ne porte que sur l'authentification. Les DONNEES ne sont
pas cloisonnees. Les tables compteurs_votes, cle_rsa_active, budget_epsilon et
jetons_autorisation sont indexees par departement SEUL, jamais par le couple
(compte, departement). Deux organisations creant chacune un departement
"Marketing" partageraient donc :
- la même urne (les votes de l'une compteraient dans les resultats de l'autre) ;
- la même clé de signature ;
- le même budget epsilon (l'une pouvant epuiser celui de l'autre).

INVARIANT DE DEPLOIEMENT : une instance = une organisation. Chaque organisation
consultante doit disposer de sa propre installation, avec sa propre base et sa
propre clé de chiffrement. C'est aussi la configuration la plus sure : le
cloisonnement est obtenu par construction, pas par du code applicatif qui
pourrait être contourne par un bug.

Un vrai multi-tenant exigerait de re-cler ces quatre tables par (compte,
departement), avec la migration correspondante. Ce n'est pas fait, et ce n'est
pas nécessaire tant que chaque organisation dispose de son instance.

## 11bis. Les groupes ne doivent pas se recouper -- et VERA ne le vérifie pas

**C'est un invariant que l'organisation doit tenir, pas une propriété du code.**

Le barème de la section 14 suppose qu'une personne n'apparaît que dans UN groupe
publié. Si l'organisation définit « Marketing » et « Cadres », ou « Site Lyon »
et « Techniciens », quelqu'un peut appartenir aux deux -- et recevoir deux
invitations.

**Ce que cela coûte.** Lorsque les deux groupes qui se recoupent sont publiés
dans la **même consultation**, une substitution modifie les compteurs des deux
sorties : la sensibilite globale du mecanisme passe a L1 = 4 au lieu de 2.
Publiés dans deux consultations distinctes, chacune coûte epsilon = 0,5
separement et le barème classe alors la personne en ligne 2, ce qui est exact --
le problème est specifique a la publication simultanee. Cette personne subit epsilon = 1,0 dans une SEULE
consultation, alors que le barème la classe en ligne 1 à epsilon = 0,5. Sa
protection réelle correspond à deux consultations, pas une.

**Pourquoi VERA ne peut pas l'empêcher.** L'anti-rejeu porte sur le secret K,
pas sur la personne : deux invitations donnent deux secrets valides, donc deux
votes légitimes. Et VERA ne connaît pas la liste des membres -- c'est ce qui
protège leur anonymat, et c'est aussi ce qui l'empêche de détecter un doublon.

**Règle à tenir par l'organisation :** les groupes déclarés doivent former une
partition de la population -- chaque personne dans un groupe, un seul. Un
découpage par service convient ; un découpage croisant service et statut ne
convient pas.

Si un chevauchement est inévitable, ne publier qu'un seul des groupes qui se
recoupent. Le barème redevient alors exact.

## 12. Les comptes administrateurs ne survivent pas a un redemarrage

Les comptes RH sont stockes en memoire du processus (dictionnaire
_comptes_rh dans vera_admin_auth.py), sans aucune persistance. Un compte cree
via /api/rh/creer_compte disparait donc au prochain redemarrage du service.

Seul le compte principal survit : il est recree a chaque demarrage a partir de
variables d'environnement definies dans l'unite systemd, par
`vera_admin_auth.amorcer_compte_principal()`.

**Une seule variante depuis le 23/08/2026.** `VERA_ADMIN_HASH` porte une
empreinte `sel$hash` calculee hors ligne (PBKDF2-HMAC-SHA256, 200 000
iterations) : le mot de passe n'apparait nulle part sur le serveur. C'est la
variante en production depuis le 12/08.

**Le repli `VERA_ADMIN_PASS` a ete retire.** Il portait le mot de passe en clair,
qui vivait alors en permanence dans l'unite systemd -- lisible par
`systemctl cat` et recopie dans toute sauvegarde de configuration. C'est le
chemin par lequel des secrets ont fuite le 31/07/2026.

Il a survecu longtemps pour une raison mecanique, qui merite d'etre notee :
`run_tests.sh` l'exportait, donc toute la suite l'empruntait et le retirer
cassait les tests -- tandis que la voie reellement en service n'etait exercee par
rien. La suite a d'abord ete basculee sur `VERA_ADMIN_HASH` le 23/08, ce qui a
rendu le retrait possible le meme jour.

**Le refus est franc.** Si `VERA_ADMIN_PASS` figure encore dans une unite sans
`VERA_ADMIN_HASH`, le service ne demarre pas et le message indique la migration.
Ignorer la variable en silence demarrerait un service sans aucun compte
d'administration -- ce que l'organisateur ne decouvrirait qu'au moment de se
connecter, consultation ouverte. Verifie dans les deux sens par
`test_repli_admin_retire.py`.

**Et le retrait a lui-meme entrouvert une porte, la cinquieme fois que cela
arrive sur ce projet.** La garde ecrite le meme jour ne verifiait que
`run_tests.sh`, nommement : elle fermait le cas, pas la classe. Quatre scripts
shell utilisaient le repli. Deux sont restes casses sans que rien ne le dise --
`chantier_crypto/crash_test.sh`, que la suite presente pourtant comme son test
le plus complet, et `charge_paliers.sh`, qui extrayait en outre le mot de passe
de l'unite systemd par un `grep`. Les deux ont ete corriges le 23/08 et la
garde porte desormais sur tous les fichiers `.sh`, presents et futurs.

Le motif merite d'etre retenu tel quel : une garde nommant un fichier ferme un
cas. Une garde parcourant une classe de fichiers ferme une classe.

**Et la preuve formelle certifiait un autre mecanisme que celui en service.**
Constat d'un audit externe du 27/08/2026. `validation_opendp.py` redeclarait les
parametres du mecanisme, annotes « = prod », et affirmait certifier
« EXACTEMENT le mecanisme execute par le serveur ». Sa borne superieure de
domaine y valait 10 000 alors que la production applique 10 000 000 depuis la
recalibration du 04/07 -- un facteur mille, reste huit semaines dans le fichier
qui tient lieu de preuve.

La consequence numerique etait nulle : epsilon = Delta_1 / scale ne depend pas
des bornes, et le 0,5 certifie restait vrai. Mais la preuve portait sur un
mecanisme qui, s'il etait deploye, aurait la branche dependante des donnees que
l'elargissement des bornes a precisement supprimee. **Une preuve qui certifie
autre chose que ce qui tourne ne prouve rien**, meme lorsque le resultat
coincide.

Les parametres sont desormais IMPORTES depuis `vera_dp_noise.py` au lieu d'etre
recopies, et une garde interdit qu'un autre fichier les redeclare.

**Le meme audit a trouve la meme faute dans un commentaire.** Celui qui justifie
K_MIN au lecteur du code annoncait « n=100 : 9% ». Mesure : 12 % -- les 9 %
correspondent a une repartition CONCENTREE, c'est-a-dire au cas le plus
favorable. Le commentaire qui justifie le seuil sous-estimait donc l'erreur, en
citant le meilleur cas la ou il faut le pire.

Il derive desormais de l'invariant des 12 voix (12 / 240 = 5 %, 12 / 100 = 12 %)
au lieu de recopier une table. Une valeur deduite ne peut pas deriver.

Et la garde `test_parametres_documentes.py`, qui ne lisait que les fichiers
Markdown, examine desormais aussi les COMMENTAIRES Python : un commentaire
pouvait contredire la constante situee trois lignes plus bas sans que rien ne le
voie.

**Le troisieme constat du meme audit portait sur une garantie de securite qui
ne se declenchait pas.** `vera_consultation_api.py` annonce un fail-closed --
« le serveur refuse de demarrer sans signature aveugle RSABSSA (Porte 7) » --
repris par le README et `requirements.txt`.

`vera_blind_sig/` est un REPERTOIRE du depot. Depuis la PEP 420, Python le
resout comme paquet d'espace de noms : l'import reussit sur un simple clone,
sans qu'une ligne de Rust ait ete compilee, et `ouvrir_consultation()` ne touche
jamais le module. Le `except` n'etait donc jamais atteint. Le serveur demarrait,
et l'echec ne survenait qu'a la premiere generation de cle -- consultation deja
ouverte, organisateur devant ses liens.

Ce n'etait pas exploitable pour desanonymiser : sans cle, aucun lien n'est emis,
donc aucun vote. Mais l'affirmation etait fausse, et un commentaire situe quinze
lignes au-dessus du `raise` disait exactement l'inverse de celui-ci.

La verification vit desormais dans `vera_signature_manager.py`, au moment de
l'import : elle controle que le module EXPOSE `generer_cles()` et
`signer_aveugle()`. `tests/test_porte7_failclosed.py` reproduit le scenario avec
un faux module vide et echoue si l'import passe. **Un import qui reussit ne
prouve pas qu'un module fonctionne.**

**Quatrieme constat : une seconde porte reposait sur une mesure introuvable.**
La Porte 2 -- inference d'appartenance -- affichait « AUC = 0.6209, IC95 %
[0.6185, 0.6232], N=100 000, bootstrap », et figurait parmi les portes fermees
« avec preuve reproductible ». Aucun script du depot ne produisait ces chiffres.
`validation_opendp.py` calcule une AUC ANALYTIQUE de pire cas (0.621311), qui
n'est ni la meme valeur, ni la meme nature, ni assortie d'un intervalle.

Mesure rapatriee dans `tests/test_porte2_mia.py` : **AUC = 0.6205, IC95 %
[0.6181, 0.6229]**, sous la borne 0.6225. Les deux intervalles se recouvrent --
la mesure d'origine etait juste, elle n'etait simplement pas verifiable.

**Et ce test a revele que rien ne gardait epsilon.** Dans sa premiere version,
diviser SCALE par deux portait epsilon a 1,0 et le test passait toujours : il
recalculait la borne depuis la calibration degradee et concluait a la
conformite. Il confronte desormais la calibration a l'ENGAGEMENT -- 0,5, ce que
VERA promet a ses participants -- et non a elle-meme. **Une garde qui s'adapte
au defaut ne garde rien.**

**Cinquieme constat : la suite de tests ne demarrait pas ailleurs que chez le
mainteneur.** `run_tests.sh` pointait `/root/vera_blind_sig/.venv/bin/python3`
en dur, et la variable qui permettait d'en changer n'etait documentee nulle
part. Un tiers qui clonait le depot et suivait la procedure du README executait
ZERO test. Tout ce que ce depot rend reproductible -- la mesure MIA, le canal
temporel, le bundle -- lui restait donc inaccessible.

Le script cherche desormais l'interpreteur : variable explicite, puis `.venv/`
du depot, puis le `python3` du PATH ; et il refuse de continuer, en donnant la
commande a lancer, si aucun ne dispose des dependances.

**Il exportait aussi VERA_DB_KEY, extraite de l'unite systemd.** C'est la cle de
PRODUCTION, celle qui rend la base lisible. Les tests travaillent sur des bases
temporaires : ils n'en ont aucun besoin, et l'exporter la faisait vivre dans
l'environnement de chaque processus de test, donc lisible dans `/proc`. Une cle
jetable est desormais tiree a chaque execution.

Et la garde qui interdit aux scripts d'extraire des valeurs de l'unite ne voyait
pas ce cas : le nom du fichier vivait dans une variable, deux lignes au-dessus
du `grep`. **Une garde contournable par indirection ne garde pas.** Elle a ete
elargie.

### Le motif qui revient, et ce qu'il coute

Un second audit externe, le 27/08 egalement, a montre que **le correctif de la
veille avait lui-meme ferme un cas au lieu d'une classe** -- dans le commit qui
denoncait precisement ce defaut.

La phrase « exactement ce que le protocole existe pour ne pas conserver » avait
ete retiree de `vera_persistance.py` comme exageree. Elle etait aussi dans
`vera_consultation_api.py`, mot pour mot. Personne ne l'y avait cherchee. Le
meme fichier affirmait par ailleurs, cinquante lignes sous l'appel qui memorise
la signature, qu'« aucun lien jeton<->signature n'est stocke », et decrivait le
cache comme une « table » -- alors que c'est un dictionnaire en memoire, jamais
ecrit sur disque. Le mot laissait croire au canal ferme le 13/08.

**Et la garde des parametres documentes etait contournable par un marqueur que
nous avions ajoute la veille.** « depuis le » figurait dans la liste des
formulations excusant une mention historique. Or c'est un marqueur de PRESENT.
Une phrase affirmant que la base tourne encore dans l'ancien mode de
journalisation -- fausse, et portant sur le canal le plus grave que ce projet
ait ferme -- passait la garde sans broncher, du seul fait qu'elle contenait ces
deux mots. Verifie en la cassant.

Trois consequences retenues :

1. **Un marqueur d'exemption est une faille en puissance.** « depuis le » est
   retire ; chacun de ceux qui restent doit designer sans ambiguite le passe.
2. **Retirer une formulation ne suffit pas : il faut la chercher partout.** Une
   garde inventorie desormais les formulations retirees et echoue si l'une
   reapparait, quel que soit le fichier.
2bis. **Un troisieme audit, le 28/08, a montre que la garde ne voyait pas le
   chiffre le plus visible du projet.** Elle exige le nom litteral du parametre
   sur la ligne. Or le README ecrit « **240** <- seuil de publication » et le
   present document « 240 reponses par groupe » sans jamais ecrire `K_MIN` :
   aucun de ces deux passages n'etait controle. Elle ignorait aussi `SCALE` et
   `DELTA_INT`, et son motif etait sensible a la casse, alors que la
   documentation ecrit « scale = 4 » en minuscules -- saborder `SCALE` de 4 a 8,
   donc porter epsilon a 0,25 pendant que tout le depot annonce 0,5, laissait la
   garde afficher « OK ». Le rattrapage venait d'un autre test, par repartition
   heureuse plutot que par conception.

   Corrige : les deux constantes ajoutees, motif insensible a la casse, et un
   controle du seuil cite SANS son nom. **Une garde qui exige d'etre nommee ne
   voit pas ce qui compte le plus.**

   Le meme audit a trouve deux documents cites qui n'existent pas
   (`ATTRIBUTION_FLOW.md`, `RSAPBSSA_EXPLORATION.md`), un renvoi de section faux
   dans le modele de menace, un TPR publie tronque plutot qu'arrondi, et un
   document de travail du 20/07 versionne qui se donne pour une reference en
   renvoyant a cinq fichiers disparus.

   **Et il a relance un constat que deux audits precedents avaient deja fait :**
   le commentaire de `publier_histogramme_dp` annonce que le mecanisme « refuse
   plutot que d'ecreter en silence », quand il ecrete precisement en silence.
   Signale le 27/08, annonce corrige, il ne l'etait pas -- le script de
   correction testait la presence du texte par une condition au lieu d'une
   assertion, et a continue sans rien faire. **Une correction non verifiee n'est
   pas une correction.**

3. Cette garde-la a d'abord souffert du meme defaut -- son exemption acceptait
   un marqueur de citation n'importe ou dans les lignes voisines, ce qui, sur un
   texte en prose, l'annulait toujours. Resserree a la ligne meme. Puis elle
   s'est denoncee elle-meme, son dictionnaire contenant les formulations
   interdites. **Une garde se teste contre elle-meme avant d'etre gardee.**

Le chiffre de l'AUC illustre le meme motif : corrige dans le modele de menace et
dans la section 9, il restait a 0,6209 dans la section 14 du present document,
qualifie de « a peine mieux que le hasard » -- une minimisation que le test
produisant la mesure contredit explicitement. Corrige.

**Un controle de sante qui ne controle rien.** Le crash test verifiait son
demarrage par `curl /api/health`. Un serveur fantome d'un essai precedent --
detenteur du verrou, donc empechant precisement le nouveau de demarrer --
repondait 200 et le controle passait. Le test echouait ensuite beaucoup plus
loin, sur une erreur d'authentification sans rapport, contre une instance
amorcee avec d'autres comptes. Il verifie desormais que SON processus est
vivant (`kill -0` sur le PID) avant d'interroger le port. Un port qui repond ne
prouve pas que c'est le bon serveur qui repond.

**Retour a la non-persistance des comptes**, dont le
motif merite d'être donne exactement. Ce n'est pas un oubli -- une
version anterieure invoquait « rien de sensible au repos », ce qui est faux :
la clé RSA privee EST persistee, chiffree (section 9). La doctrine réelle est
« rien de sensible EN CLAIR au repos ».

Et l'argument de surface d'attaque tient mal : une empreinte PBKDF2 a 200 000
iterations est précisément concue pour resister a une attaque hors ligne,
contrairement a une clé de signature dont la compromission fabrique des votes.
Persister des empreintes serait moins grave que ce qui est déjà persiste.

**Le commentaire du code disait l'inverse de cette section jusqu'au
30/08/2026** : « en memoire pour ce prototype -- a migrer vers une vraie base si
le besoin devient reel ». Un lecteur du code y voyait un raccourci provisoire,
un lecteur d'ici une decision assumee. Un audit externe a note l'absence de
persistance comme un defaut de maturite, ce qui etait la lecture logique du
commentaire. Aligne.

**Et une consequence pratique qui n'etait ecrite nulle part.** Le compte
d'amorcage est recree a chaque demarrage depuis `VERA_ADMIN_HASH` : il survit.
Les comptes crees ensuite via `/api/rh/creer_compte`, non -- ils disparaissent a
chaque redemarrage, donc a chaque deploiement. Un organisateur qui s'en cree un
perd son acces sans avertissement, potentiellement consultation ouverte.

Le vrai motif est la simplicite operationnelle : une table de comptes demande
une gestion de cycle de vie -- creation, revocation, rotation, recuperation --
qu'un mainteneur unique n'assurerait pas de facon fiable. Le choix est assume :
les comptes additionnels sont TEMPORAIRES PAR CONSTRUCTION.

Portee pratique limitée : la creation de comptes n'est pas exposee dans
l'interface d'administration. C'est une operation d'operateur technique,
effectuee en ligne de commande avec le secret d'administration, par quelqu'un
qui connait le système. Un organisateur n'y est jamais confronte.

Si un jour plusieurs administrateurs permanents devenaient necessaires, la voie
propre serait de les declarer dans l'unite systemd au même titre que le compte
principal -- pas de les persister en base.

## 12bis. Le transporteur des invitations est un tiers de confiance non declare

Chaque invitation part par SMS ou par courriel, donc par un prestataire. Ce
prestataire voit passer, pour chaque destinataire, le couple

    (numero de telephone ou adresse)  <->  (lien contenant le jeton)

Il détient donc exactement ce que l'organisation détient : la correspondance
personne -> invitation. Et il détient davantage : le jeton lui-même, en clair,
ce qui lui permettrait de voter a la place du destinataire.

**Ce que cela signifie concretement.** Le modèle de VERA repose sur une
séparation des roles : l'hébergeur a la base sans la liste, l'organisation a la
liste sans la base. Le transporteur, lui, a la liste ET les jetons. Il ne peut
pas relier une réponse a une personne -- il n'a pas la base -- mais il est un
troisieme détenteur d'un demi-secret, et le modèle n'en parlait pas.

**Ce qui limite le risque.** Un prestataire d'envoi n'a aucun intérêt a votre
consultation, il ne sait pas ce que mesure le lien qu'il transporte, et voter a
la place de quelqu'un se verrait : le destinataire legitime recevrait un refus.
Mais c'est un argument de vraisemblance, pas une garantie.

**Ce que l'organisation doit faire.** Choisir un prestataire soumis au RGPD,
l'inscrire au registre de traitement comme sous-traitant, et vérifier sa durée
de retention des messages envoyes -- un historique de SMS conserve six mois
conserve six mois de jetons en clair.

### La clause qui ferme la combinaison transporteur + hebergeur

Le transporteur detient la correspondance (personne → jeton). L'hebergeur
detient la base. **Ces deux moities suffisent a desanonymiser**, exactement
comme organisation + hebergeur -- et rien, aujourd'hui, n'interdit qu'ils soient
la meme entite ou qu'ils appartiennent au meme groupe.

Le contrat d'hebergement ne couvre pas ce cas : il engage l'hebergeur vis-a-vis
de l'organisation, pas vis-a-vis d'un tiers que l'organisation choisit seule et
apres coup.

**A inscrire dans l'accord de consultation :**

> **Article — Independance du transporteur.**
>
> L'organisation designe nommement, avant l'envoi des invitations, le
> prestataire assurant leur acheminement (SMS, courriel ou tout autre canal).
>
> Ce prestataire n'est ni l'hebergeur du service, ni une filiale, ni une
> societe mere, ni un sous-traitant de celui-ci, et n'a avec lui aucun lien
> capitalistique ou contractuel. L'organisation atteste de cette independance
> par ecrit ; l'hebergeur atteste reciproquement n'avoir aucun lien avec le
> prestataire designe.
>
> La designation et les deux attestations sont communiquees aux representants
> du personnel avant l'ouverture des depots, et annexees au proces-verbal.
>
> A defaut d'un transporteur satisfaisant a ces conditions, la consultation
> n'est pas ouverte.

**Le cas particulier a ne pas manquer.** Si l'organisation achemine les
invitations par son propre serveur de courriel, elle est son propre
transporteur. Ce n'est pas un probleme en soi -- elle detient deja cette moitie
du secret -- mais aucun tiers n'est alors introduit la ou le modele en supposait
un. L'attestation doit le dire explicitement plutot que de laisser croire a une
separation qui n'existe pas.

**Ce que VERA pourrait faire et ne fait pas.** Un lien a usage unique perd sa
valeur des qu'il est consomme, ce qui borne la fenetre. Rien de plus n'est
prevu : chiffrer le lien pour le destinataire supposerait une clé par personne,
donc la liste chez l'hébergeur -- exactement ce que la séparation interdit.

### Deux autres tiers de la même classe : le DNS et l'autorite de certification

Qui controle la zone DNS du service peut obtenir un certificat valide pour ce
nom et servir son propre JavaScript aux votants. C'est exactement le scenario
« operateur actif » de la section 6, mais ouvert a un tiers qui n'a jamais été
choisi comme tel.

Le controle SRI de la page de vote ne protège pas de cela : il vérifie la
bibliotheque cryptographique, pas la page qui porte l'attribut. Qui sert la page
sert aussi l'empreinte.

**Ce point etait aggrave par le deploiement, et ne l'est plus.** Jusqu'au
02/09/2026, le service tournait sur un sous-domaine DuckDNS : gratuit, sans
engagement contractuel, sans recours en cas de reprise du nom. La production est
depuis sur **vera-consultation.fr**, detenu en propre chez un bureau
d'enregistrement francais, avec verrouillage du transfert et renouvellement
automatique. L'AFNIC verifie l'identite du titulaire, ce qu'un DPO peut
consulter.

**Ce qui reste a faire sur ce point :** la surveillance des certificats emis
(Certificate Transparency). Sans elle, un certificat obtenu frauduleusement pour
ce nom ne serait pas detecte -- le verrouillage du registrar rend la reprise du
nom difficile, il ne la rend pas impossible.

L'ancien sous-domaine continue d'etre servi par nginx, les deux noms figurant au
meme certificat. Les liens d'invitation portent le nouveau.

**Et le sous-domaine genait deja l'acces, ce qui etait un risque distinct.** Le
26/08, deux outils tiers ont refuse de charger la page de vote en la declarant
« hors ligne ou privee », alors que le service repondait normalement -- verifie
la minute suivante par `curl` depuis le serveur ET depuis un telephone en 4G,
code 200 dans les deux cas. DuckDNS heberge aussi beaucoup de services
ephemeres, et des filtres generalistes le traitent par categorie plutot que par
adresse.

Ces memes listes arment les passerelles de messagerie, les filtres d'entreprise
et les antivirus mobiles. Un lien vers ce sous-domaine, envoye a plusieurs
centaines de salaries, a donc une probabilite non nulle d'etre bloque chez une
partie d'entre eux -- **et cette partie ne serait pas aleatoire** : elle
dependrait de l'operateur et de la politique informatique de l'employeur.

C'est le meme biais que celui decrit en section 12ter pour les connexions
instables : une perte de voix correlee au terrain, invisible dans les chiffres
publies. La difference est qu'ici elle frapperait avant meme l'ouverture du
lien, sans que le destinataire sache qu'il avait quelque chose a ouvrir.

L'ampleur n'a pas ete mesuree et ne peut pas l'etre depuis le serveur. Mais
c'etait le troisieme argument pour un nom de domaine en propre, et le plus
concret : les deux premiers portaient sur ce qu'un adversaire pourrait faire,
celui-ci sur des votants qui n'auraient simplement jamais recu leur lien.

**Cette observation reste a refaire sur le nouveau nom.** Un `.fr` recent, sans
historique, peut lui aussi etre filtre par certaines passerelles -- moins
probablement qu'un sous-domaine dynamique, mais ce n'est pas verifie. A tester
avant le premier envoi reel, depuis plusieurs operateurs.

## 12ter. Une voix peut se perdre en silence, et pas au hasard

Le cache décrit en section 1 rattrape le cas courant -- rechargement de page,
coupure brève. Il ne rattrape pas tout.

Un votant perd sa voix définitivement si son navigateur échoue entre la
signature et le dépôt et qu'il revient **plus d'une heure après**, ou après un
redémarrage du service. Le jeton est consommé, aucun recours automatique : il
faut demander une nouvelle invitation.

**Ce n'est pas neutre pour le résultat.** Cette perte ne frappe pas au hasard :
elle touche les connexions instables, les usages mobiles, les zones mal
couvertes. Elle est donc **corrélée au terrain**, et invisible dans les chiffres
publiés -- un groupe dont les membres travaillent en déplacement sera
sous-représenté sans que rien ne le signale.

Sur un système dont la résolution est de +/- 12 voix (section 2), quelques
dizaines de pertes systématiques suffisent à déplacer un résultat serré.

**Ce que l'organisation peut faire :** indiquer un contact indépendant sur les
liens (paramètre `c=`), pour qu'un participant en difficulté puisse demander un
nouveau lien sans s'adresser à sa hiérarchie. Et relancer les non-répondants, en
sachant qu'une partie d'entre eux a peut-être essayé.

## 13. Integrite du scrutin : VERA garantit l'anonymat, pas la sincérité du resultat

C'est la limite la plus importante de ce document, et la plus facile a mal
comprendre : **VERA prouve que personne ne peut relier une réponse a une
personne. Il ne prouve pas que le resultat publié reflete un vrai scrutin.**

Ce que VERA garantit techniquement, **dans son modèle de menace et sous le
respect de ses conditions d'exploitation** (section 1) :

- rien en base ne relie une réponse a la personne qui l'a émise (signature
  aveugle, registres disjoints, absence d'horodatage). La liaison reste possible
  par les canaux temporels de la section 9, qui ne sont pas couverts par cette
  garantie ;
- un jeton d'autorisation ne peut servir qu'une fois (consommation atomique) ;
- une même signature ne peut déposer qu'un vote (anti-rejeu sur l'empreinte
  du secret K) ;
- aucun resultat n'est publié sous le seuil K_MIN.

Ce que VERA ne garantit PAS :

- que les jetons émis correspondent a de vraies personnes distinctes. Le
  système génère le nombre de jetons qu'on lui demande ; il n'a aucune liste
  de reference, aucun annuaire, aucun moyen de savoir a qui un lien est envoye
  (c'est précisément ce qui protège l'anonymat) ;
- qu'aucun de ces jetons n'a été utilise par l'organisateur lui-même. Un
  organisateur qui génère 240 jetons et vote 240 fois obtient un resultat
  publié entierement fabrique, et rien dans les chiffres ne le trahit ;
- qu'un votant puisse vérifier que sa voix figure dans le total. Il n'y a ni
  recu, ni urne publique, ni recomptage possible.

**Pourquoi ce n'est pas un defaut a corriger, mais un choix impose.** La
verifiabilite de bout en bout -- celle des systèmes de vote type Belenios ou
Helios -- repose sur la publication d'une urne et d'un decompte EXACTS, que
chacun peut recompter. Or VERA publie un décompte BRUITÉ : c'est toute la
garantie de confidentialite differentielle. Les deux propriétés sont en
conflit direct, un total vérifiable trahissant les individus que le bruit
protège. Les concilier exigerait une preuve a divulgation nulle de connaissance
attestant que le bruit a été correctement ajoute a un ensemble de bulletins
publiquement engages. C'est un sujet de recherche, pas une option de
configuration.

VERA a donc choisi l'anonymat prouve plutot que l'intégrité prouvee.

**Consequence pratique.** VERA convient a une consultation d'opinion ou le
commanditaire cherche réellement a savoir ce que pense son organisation.

Attention toutefois a ne pas se rassurer trop vite avec l'argument « un
organisateur qui falsifie son propre sondage se trompe lui-même » : il n'est
vrai que si la consultation sert a INFORMER l'organisateur. Or un barometre
social sert souvent a COMMUNIQUER un resultat -- a une direction, a des
représentants du personnel, a des salaries, a une tutelle. Dans ce cas
l'organisateur ne se trompe pas lui-même, il trompe des tiers, et c'est
précisément le scenario qu'un délégué syndical ou un DPO a en tete.

Ne pas se rassurer non plus avec l'idee que « les participants verraient
l'ecart » : ils ne voient pas la liste de diffusion. Un organisateur qui
ajoute vingt invitations fictives et vote vingt fois n'est detectable par
aucun participant -- c'est exactement ce qu'implique le fait que VERA ne
connaisse pas la liste.

VERA ne convient PAS a un scrutin contraignant, electif ou juridiquement
opposable, ou l'organisateur pourrait avoir intérêt a fabriquer le resultat et
ou la contestation doit pouvoir s'appuyer sur une preuve.

### Ce qui ferme cette porte, et pourquoi ce n'est pas du code

**Aucun code ne peut fermer cette porte.** Verifier qu'une invitation correspond
a une personne réelle supposerait de connaitre les personnes -- exactement ce
que VERA s'interdit, et ce qui protège leur anonymat. Tout mécanisme qui
fermerait cette porte rouvrirait la section 6.

**Ce que le code fait, et c'est tout ce qu'il peut faire :** exposer
publiquement, sur `/api/engagement_cles`, le nombre d'invitations émises par
groupe. Cela ne prouve rien. Cela rend le controle POSSIBLE par quelqu'un qui,
lui, connait l'effectif réel.

**La condition, a inscrire dans l'accord et non a recommander :**

> Avant l'ouverture des dépôts, l'organisation communique aux représentants du
> personnel le nombre d'invitations émises par groupe et l'effectif inscrit au
> registre du personnel pour ce même groupe. L'ecart entre les deux est justifie
> par ecrit et annexe au proces-verbal de la consultation.

Le premier chiffre est vérifiable independamment : il suffit d'interroger
`/api/engagement_cles`. Le second releve du mandat des représentants.

**Ce que cette condition vaut, exactement.** Elle ne tient pas par construction,
contrairement aux portes fermees par le code : elle tient tant que le tiers fait
son travail. S'il atteste sans vérifier, ou s'il n'existe pas dans
l'organisation, la porte se rouvre entierement et personne ne le verra.

Mais c'est un controle qu'un délégué peut REELLEMENT faire -- comparer deux
nombres, sans competence technique et sans dependre de l'employeur. Un controle
effectif vaut mieux qu'une garantie cryptographique que personne ne vérifie.

Cette limite est énoncée au votant sur la page de vote : *"VERA protège votre
réponse. Il ne vérifie pas la liste des personnes invitees : c'est
l'organisateur qui l'etablit."*

## 13bis. L'organisateur peut aussi ne pas publier

La section 13 traite la fabrication d'un résultat. L'omission en est le levier
symétrique, et il est plus facile à actionner : il suffit de ne rien faire.

L'organisateur peut clôturer sans publier, ou publier une partie des groupes
seulement. Comme lui seul détient la liste de diffusion, **les participants ne
peuvent pas distinguer « pas encore publié » de « enterré »** -- ils ne savent
même pas si les autres ont répondu.

**Ce qui limite le problème depuis le 19/08, et jusqu'où.** L'endpoint public
`/api/resultats_publies` rend la publication visible de tous : un résultat publié
ne peut plus être retiré ni modifié **tant que la consultation vit**.

Mais la clôture efface tout, y compris les résultats publiés
(`VERA_THREAT_MODEL_COMPLETE.md`, Porte 14). Un organisateur qui publie puis
clôture fait donc disparaître le chiffre du serveur.
Il reste visible pour qui l'a consulté entre-temps, et rien ne permet de le
reconstruire ensuite.

**Ce que cela impose.** Le résultat doit être sauvegardé avant la clôture — par
l'organisation *et* par les représentants du personnel. Un tiers qui interroge
`/api/resultats_publies` au moment de la publication en garde une copie datée ;
c'est le seul moyen de rendre le chiffre opposable après coup.

Et rien n'oblige à publier.

**Ce que l'organisation doit accepter contractuellement**, si elle veut que le
dispositif soit crédible auprès de ses membres : s'engager sur une date de
publication annoncée à l'avance, et communiquer le résultat aux représentants du
personnel en même temps qu'à elle-même. C'est procédural, VERA ne peut rien y
faire.

## 14. Le budget epsilon ne survit pas a la clôture : règle d'usage sur le nombre de consultations

> **EN CLAIR, sans jargon.**
> La protection de VERA s'use si vous consultez plusieurs fois les MEMES
> personnes. Une ou deux consultations par an sur un groupe : protection
> solide. Quatre : encore correcte. Au-dela de six, la protection cesse d'etre
> defendable : dans le pire cas -- un employeur qui connaitrait deja toutes les
> autres reponses -- il pourrait deviner juste jusqu'a dix-neuf fois sur vingt.
> Un employeur reel fait moins bien. Mais c'est ce plafond que vous annoncez a
> vos membres, et c'est lui qui doit rester tenable.
> **Regle simple : pas plus de quatre consultations par an sur le même groupe.**
> VERA ne peut pas vous en empecher techniquement -- il ne sait pas qui sont
> vos membres, c'est ce qui protège leur anonymat. C'est donc a l'organisation
> de s'y tenir.


**Ce qui est garanti techniquement.** Chaque publication applique exactement
epsilon = 0.5 (Laplace, Delta_1 = 2, scale = 4). A l'intérieur d'une
consultation, un departement ne peut publier qu'une seule fois : republier
renvoie le resultat fige, sans nouveau tirage de bruit -- sinon un appelant
pourrait moyenner N tirages et annuler la protection. Ce verrou fonctionne et
a été vérifie.

**Ce qui n'est pas garanti.** A la clôture, `budget_epsilon.reset()` remet le
compteur a zero. Une nouvelle consultation sur la même population repart donc
avec un budget plein. Le budget est en réalité **par consultation**, pas **par
cohorte** : reposer la même question aux mêmes personnes k fois coute
epsilon = 0.5 * k sur ces personnes, sans que rien ne le BLOQUE. Depuis le
19/08 une table `historique_consultations` compte les consultations closes par
groupe et le tableau de bord avertit des la deuxieme, fermement a partir de la
quatrieme -- mais un groupe renomme repart a zero, et rien n'empeche de passer
outre. C'est un avertissement, pas un verrou.

**Pourquoi ce n'est pas corrigeable techniquement.** La composition
differentielle porte sur les PERSONNES, pas sur les noms de groupes. Or VERA
n'a aucune notion d'identite persistante -- c'est précisément ce qui garantit
l'anonymat. Le seul identifiant disponible est le nom du departement, qui est :

- une approximation imparfaite (les effectifs changent entre deux
  consultations : ce n'est déjà plus la même population) ;
- controle par l'organisateur lui-même, donc contournable en renommant
  "RH" en "RH 2".

Un blocage dur sur un identifiant que l'adversaire choisit librement ne
protège de rien contre un organisateur malveillant, et enfermerait un groupe
legitime après N consultations. Le `reset()` n'est pas un defaut : il corrige
un vrai bug (un departement reutilisant un nom déjà publié devenait
definitivement non publiable). La limite est structurelle.

**La protection est donc une REGLE D'USAGE, pas un verrou.**

### Bareme d'exposition cumulee

| Consultations | epsilon cumule | Borne superieure de decision correcte* |
|---|---|---|
| 1 | 0.5 | 62,25 % |
| 2 | 1.0 | 73,1 % |
| **4** | **2.0** | **88,1 %** |
| 6 | 3.0 | 95,3 % |
| 10 | 5.0 | 99,3 % |
| 20 | 10.0 | 99,995 % |

\* *Probabilite maximale qu'un adversaire devine juste, dans le scenario binaire
pire-cas decrit ci-dessous. Ce n'est ni une mesure, ni ce qu'un adversaire réel
obtient.*

#### D'ou viennent ces pourcentages

Ce ne sont ni des mesures ni une intuition : c'est la borne pire-cas standard
de l'epsilon-DP, et elle se derive en trois lignes.

**Hypotheses**, a poser explicitement car les chiffres n'ont aucun sens sans
elles :

- l'adversaire connait TOUTES les autres réponses -- il ne lui manque que celle
  de la personne visee ;
- son prior sur cette réponse est uniforme, pile ou face ;
- il doit trancher entre deux valeurs possibles (devinette binaire).

**Derivation.** L'epsilon-DP borne le rapport de vraisemblance entre deux bases
voisines : pour toute sortie S,

    P(S | réponse = a) / P(S | réponse = b)  <=  e^epsilon

Avec un prior uniforme, la règle de Bayes donne une probabilite a posteriori de
deviner juste bornee par

    e^epsilon / (1 + e^epsilon)

Soit 62,25 % a epsilon = 0,5 ; 73,11 % a 1 ; 88,08 % a 2 ; 95,26 % a 3.

**Ce que cette borne est, et n'est pas.** C'est un PIRE CAS : un adversaire
omniscient sur tout le reste, avec la strategie optimale. Un adversaire réel
fait moins bien.

**Ne pas comparer cette borne a l'AUC mesuree.** La précision 1 ci-dessous rapporte
AUC = 0,6205 pour une attaque d'appartenance sur VERA. La proximite numerique
avec 62,25 % est une coincidence, pas une confirmation : ce sont deux quantites
differentes.

- La **borne bayesienne** porte sur une decision binaire unique, avec prior
  uniforme et adversaire omniscient. C'est un maximum théorique.
- L'**AUC** mesure la qualite de classement d'un classifieur sur un jeu de
  données, tous seuils confondus. C'est un resultat expérimental, dependant du
  protocole de mesure.

Les rapprocher pour conclure quoi que ce soit sur la calibration serait une
erreur de raisonnement.

Ce n'est PAS une propriété de VERA en particulier : c'est vrai de tout
mécanisme epsilon-DP. Et cela ne borne QUE ce qui se deduit des sorties
publiées -- ni la participation, ni l'horodatage, ni ce qu'un adversaire
apprendrait en observant le serveur pendant la consultation.

#### Lecture

A epsilon = 3, la borne pire-cas atteint 95 % : l'adversaire optimal ne se
tromperait plus qu'une fois sur vingt.

**Ce n'est pas un seuil de significativite statistique.** Le rapprochement avec
p < 0,05 est une coincidence numerique -- les deux quantites n'ont pas le même
objet : l'une borne une croyance a posteriori, l'autre controle un taux d'erreur
de premiere espece. C'est le point ou le plafond devient assez haut pour qu'un
employeur puisse s'en autoriser une decision, et ou la phrase affichee au votant
cesse d'être defendable.

### Regle retenue

**Une organisation ne devrait pas publier plus de 4 consultations par periode
de 12 mois glissants sur la même population** (epsilon cumule = 2.0).

Au-dela, la protection sort de la zone defendable publiquement. VERA ne
l'empeche pas techniquement -- il ne le peut pas -- mais l'organisation qui
depasse ce rythme doit savoir qu'elle dégrade la garantie qu'elle a annoncee
a ses membres.

### Trois précisions, pour ne pas surestimer le risque

1. Les pourcentages ci-dessus sont un **plafond du pire cas théorique** : ils
   supposent un adversaire connaissant déjà toutes les autres réponses sauf
   une, et des questions parfaitement corrélées. L'inference réellement
   mesuree sur VERA est plus basse : AUC = 0.6205 (IC95%
   [0.6181, 0.6229], `tests/test_porte2_mia.py`).

   **Ne pas lire ce chiffre comme « a peine mieux que le hasard ».** Cette
   section l'ecrivait ; c'etait minimiser. Une AUC de 0,62 signifie qu'un
   adversaire omniscient sur tout le reste devine juste 62 fois sur 100 la ou
   le hasard en donne 50. C'est la garantie epsilon = 0,5, ni plus ni moins --
   et elle ne porte que sur les sorties publiees. Formulation corrigee le
   27/08/2026 : le document destine aux organisations disait moins que le test
   qui produit la mesure.
2. **K_MIN = 240 aide en pratique, mais ce n'est pas lui qui porte la
   garantie.** Le seuil compte face a un adversaire ordinaire : plus le groupe
   est grand, plus une réponse s'y fond.

   Il ne tient pas face a l'organisateur lui-même. Rien ne l'empeche de générer
   240 invitations pour un groupe de quinze personnes réelles, d'en conserver
   225 et de voter 225 fois avec des réponses qu'il connait : la publication a
   lieu (240 >= K_MIN), il soustrait ses propres votes, et lit le profil des
   quinze autres. C'est le bourrage decrit en section 13, vu sous l'angle de
   l'anonymat plutot que sous celui de la sincérité.

   **Ce qui survit dans ce cas, c'est la borne epsilon.** Elle est une propriété
   du mécanisme et non des données : même en connaissant 239 réponses sur 240,
   la certitude de l'adversaire sur la derniere reste bornee a environ 62 %
   (barème ci-dessus). C'est la garantie formelle qui porte, pas le seuil.

   Consequence pour la formulation faite aux participants : ne pas promettre
   « vous etes noyes parmi 240 ». Cette phrase suppose que les 239 autres soient
   de vraies personnes, ce que le système ne vérifie pas. La seule contre-mesure
   au bourrage est procedurale : faire attester par un tiers -- comite social,
   délégué du personnel -- que le nombre d'invitations émises correspond a un
   effectif réel (condition redigee en section 13, « Ce qui ferme cette
   porte »).
3. La population evolue entre deux consultations (departs, arrivees), donc
   "la même cohorte sur un an" surestime déjà l'exposition réelle.
