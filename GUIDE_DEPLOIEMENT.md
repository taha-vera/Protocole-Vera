# Guide de déploiement

Ce document s'adresse à l'organisation qui souhaite consulter ses membres avec
VERA : direction, service RH, bureau d'association, représentants du personnel.

Il ne demande aucune compétence technique. Les questions techniques sont
traitées ailleurs — `VERA_THREAT_MODEL_COMPLETE.md` pour un responsable
informatique, `LIMITS.md` pour un délégué à la protection des données.

---

## Avant de commencer : ce qui relève de vous

VERA protège les réponses. Il ne connaît ni vos membres, ni votre organisation,
ni votre question. Trois choses restent donc entièrement sous votre
responsabilité.

**La liste des personnes invitées.** VERA génère des liens anonymes ; c'est vous
qui décidez à qui les envoyer. La fiabilité du résultat dépend entièrement de
cette liste.

**La destruction de cette liste.** Le fichier associant chaque personne à son
lien est une donnée personnelle. Il doit être détruit dès l'envoi terminé — pas
à la clôture, dès l'envoi. Tant qu'il existe, il constitue le seul document
capable de relier une personne à une invitation.

**L'information des participants.** Le RGPD vous impose de leur dire qui les
consulte, pourquoi, et quels sont leurs droits. Un modèle est fourni plus bas.

---

## Les six étapes

### 1. Préparer la question

Une seule question, trois réponses possibles : oui, non, je m'abstiens.

La question se fige dès la génération du premier lien et ne peut plus être
modifiée. C'est volontaire : la changer en cours de route permettrait de
mélanger des réponses portant sur deux questions différentes.

Formulez-la donc soigneusement, et faites-la relire — idéalement par un
représentant du personnel, qui verra ce que vous ne voyez plus.

### 2. Vérifier la taille du groupe

**Faites ce calcul avant tout le reste.** Il détermine si votre consultation est
possible, et il en écarte beaucoup.

Il faut 240 réponses par groupe pour qu'un résultat soit publié. Avec un taux de
participation réaliste de 50 à 60 %, cela demande **au moins 450 à 500 invités
par groupe**.

Conséquence directe : une entreprise de 600 salariés ne peut publier qu'**un
seul résultat d'ensemble**. Découper par service — atelier, administratif,
direction — produirait des groupes de 150 ou 200 personnes dont aucun
n'atteindrait le seuil : vous auriez envoyé 600 SMS pour n'obtenir aucun
chiffre.

Ce n'est pas une limite qu'on peut contourner en abaissant le seuil. Sur un
groupe de 40 personnes, un résultat publié en dit trop sur chacune — c'est
précisément ce que le seuil empêche.

**Si vous voulez des résultats par service, il vous faut des services de 450
personnes.** Sinon, consultez en un seul groupe, ou renoncez.


**Aucun résultat n'est publié sous 240 réponses.** Ce n'est pas un réglage, c'est
une protection : en dessous, une réponse individuelle redeviendrait devinable.

Conséquence pratique : ne découpez pas votre organisation en petits services.
Un groupe de 50 personnes ne produira jamais de résultat, et vous ne
l'apprendrez qu'à la fin. Le tableau de bord vous avertit dès la génération si
un groupe est trop petit — tenez-en compte.

Prévoyez large : 240 est le nombre de **réponses**, pas d'invitations. À 60 % de
participation, il faut inviter 400 personnes.

### 2bis. Faire attester votre effectif par vos représentants du personnel

**C'est une condition, pas une formalité.** VERA ne connaît pas vos membres —
c'est ce qui protège leur anonymat. Il ne peut donc pas vérifier que vos
invitations partent à de vraies personnes, ni qu'elles ne partent qu'à elles.

Sans contrôle extérieur, rien n'empêcherait une organisation de générer 240
invitations pour quinze personnes réelles, d'en conserver 225, et de fabriquer
un résultat. C'est écrit en clair dans `LIMITS.md` §13, et vos représentants du
personnel le liront.

**Ce qu'il faut faire, et c'est simple.** Avant d'ouvrir les dépôts,
communiquez-leur deux chiffres par groupe :

- le **nombre d'invitations émises** — qu'ils peuvent vérifier eux-mêmes en
  consultant `https://votre-domaine/api/engagement_cles` ;
- l'**effectif inscrit au registre du personnel** pour ce même groupe.

Tout écart doit être justifié par écrit et annexé au procès-verbal.

**Pourquoi cela vous sert.** Ce contrôle ne vous coûte rien et transforme votre
consultation : vos membres savent qu'un tiers a vérifié, et le résultat devient
opposable. Sans lui, un délégué a raison de considérer les chiffres comme
invérifiables.

### 3. Déclarer les groupes consultés

**En une seule fois, avant tout envoi.** Le tableau de bord vous demande la
liste complète des groupes ; leurs clés sont créées ensemble.

Cette déclaration est **irréversible**. En ajouter un ensuite changerait
l'empreinte de sécurité inscrite dans chaque lien et rendrait inutilisables tous
ceux déjà envoyés. Prenez le temps de vérifier votre liste — un oubli impose de
clôturer et de tout recommencer.

Tant que vous n'avez pas déclaré, la génération de liens est refusée.

### 4. Publier l'empreinte de sécurité, avant d'envoyer quoi que ce soit

Après la déclaration, le tableau de bord affiche une empreinte — une longue
suite de caractères. Chaque lien de participation la porte, identique pour tous
vos membres quel que soit leur groupe.

**Déposez-la à un endroit que vos membres peuvent consulter indépendamment de ce
serveur, et faites-le AVANT le premier envoi.** Concrètement : un courriel daté
au comité social et économique et à votre délégué à la protection des données,
un affichage interne, ou un message aux représentants du personnel.

Pourquoi cela compte : cette empreinte permet de vérifier que le serveur n'a pas
fabriqué une clé différente par personne — ce qui permettrait de retrouver qui a
répondu quoi. Publiée par vous à l'avance, elle devient une preuve datée.
Publiée après coup, ou pas publiée du tout, elle ne vaut rien : le serveur se
comparerait à lui-même.

C'est la seule étape de ce guide qui ne se fait pas dans le tableau de bord, et
c'est l'une des plus importantes.

### 5. Fixer la date d'ouverture, puis envoyer les invitations

**D'abord la date.** Le tableau de bord vous demande à partir de quand les votes
seront acceptés. Choisissez-la **après la fin de vos envois** — si vous étalez
l'envoi des SMS sur deux jours, fixez l'ouverture au troisième.

Pourquoi : sans cette date, chacun vote dans la foulée de sa réception. L'ordre
des votes reproduit alors l'ordre de vos envois, que vous connaissez personne
par personne — dans un petit groupe, cela suffirait à attribuer les réponses.
La date brise ce lien.

Tant qu'elle n'est pas atteinte, les liens sont valables mais inactifs :
personne ne peut voter, et un participant qui essaie voit un message le lui
expliquant, sans que son lien soit consommé.

**Votre prestataire d'envoi doit être indépendant de l'hébergeur.**

Il verra passer, pour chaque destinataire, le couple (numéro de téléphone,
lien contenant l'invitation). Il détient donc la même moitié du secret que vous.
Si l'hébergeur détenait aussi cette moitié — parce que c'est la même société,
une filiale, ou un sous-traitant — la séparation qui protège vos membres
n'existerait plus.

Avant d'envoyer, communiquez à vos représentants du personnel :

- le **nom du prestataire** retenu ;
- une **attestation écrite** qu'il n'a aucun lien capitalistique ou contractuel
  avec l'hébergeur ;
- l'attestation réciproque de l'hébergeur.

Si vous envoyez depuis votre propre serveur de courriel, dites-le : vous êtes
alors votre propre transporteur. Ce n'est pas un problème — vous détenez déjà
cette information — mais il ne faut pas laisser croire à une séparation qui
n'existe pas.

**Un contact indépendant, à ajouter aux liens.** Si un participant rencontre un
problème — page bloquée, lien qui ne fonctionne pas, doute sur le dispositif —
il ne doit pas avoir à s'adresser à vous. Vous demander de l'aide reviendrait à
vous révéler qu'il a essayé de voter, c'est-à-dire la seule chose que le système
ne protège pas.

Le tableau de bord vous demande donc une **adresse de contact indépendante**
au moment de générer les liens : celle du comité social, d'un délégué du
personnel, ou de votre délégué à la protection des données. Elle est inscrite
dans chaque lien et s'affiche automatiquement en cas de problème.

**Ce ne doit pas être la vôtre.** Un participant qui vous écrit pour signaler
un problème vous révèle qu'il a essayé de voter — la seule chose que le système
ne protège pas.

Ce champ est facultatif. Laissé vide, la page se contente de dire au
participant qu'il peut demander un nouveau lien, sans désigner
d'interlocuteur : c'est acceptable, mais un contact réel vaut mieux.

**Ensuite les envois.** Le tableau de bord génère les liens et propose un export
CSV (groupe, lien, message).

Vous chargez ce fichier dans **votre propre** outil d'envoi de SMS ou de
courriel. VERA n'envoie rien lui-même et ne voit jamais un numéro de téléphone.

Trois précautions :

- Le fichier exporté contient les liens de vote. Quiconque l'obtient peut voter
  à la place de vos membres. Traitez-le comme confidentiel, et **supprimez-le
  après envoi**.
- Chaque lien est personnel et à usage unique. Prévenez les participants de ne
  pas le transférer.
- Joignez la notice d'information (modèle ci-dessous).

### 6. Consulter, puis publier — deux gestes distincts

**Consulter les résultats ne les fige pas.** Vous pouvez ouvrir le tableau de
bord autant que vous voulez pendant la consultation : cela ne consomme rien et
ne déclenche aucune publication.

**Publier est un geste explicite et irréversible.** Le tirage du bruit n'est
fait qu'une fois : le résultat est alors figé, et toute réponse arrivant après
sera refusée. Un participant retardataire verra un message le lui expliquant,
et sa voix ne sera pas comptée.

**N'appuyez donc sur « Publier » qu'après la date de clôture annoncée à vos
membres.** Publier dès que le seuil de 240 est atteint prive de leur voix tous
ceux qui n'avaient pas encore répondu — et ils sont souvent ceux qui hésitaient
le plus.

Si vos représentants du personnel le demandent, faites-les assister à ce geste.

### 6bis. Publier

Le tableau de bord affiche la participation en temps réel, sans jamais montrer
les réponses.

Quand un groupe atteint 240 réponses, un bouton « Publier » apparaît. **La
publication est définitive** : elle fige le résultat sur les réponses reçues à
cet instant, et celles qui arriveraient ensuite ne pourront plus être comptées.
Attendez donc la fin de la période de vote.

La clôture, elle, efface tout : réponses, effectifs, liens, clés. Sauvegardez
les résultats affichés — le serveur ne les conservera pas.

---

## Le résultat publié est approché, volontairement

VERA n'affiche pas le décompte exact. Il y ajoute une perturbation
mathématique calibrée, sans laquelle il serait possible, en comparant deux
publications successives, de déduire la réponse d'une personne.

En pratique, sur 300 répondants, l'écart mesuré entre le décompte réel et le
résultat publié est de l'ordre de **3 %**, et la somme des réponses correspond
toujours exactement à l'effectif. Un résultat annoncé à 54 % là où la réalité
est 55 % conduit à la même décision.

Ce que cela implique : VERA convient aux consultations où une tendance suffit.
Il ne convient pas à un scrutin où un écart d'une voix compte.

---

## Fréquence : pas plus de quatre consultations par an sur le même groupe

Chaque publication révèle une petite quantité d'information sur le groupe.
Interroger plusieurs fois les mêmes personnes accumule cette exposition.

VERA ne peut pas le vérifier à votre place : il ne sait pas qui sont vos
membres, et c'est précisément ce qui protège leur anonymat.

La règle est donc organisationnelle : **quatre consultations maximum par période
de douze mois glissants sur une même population**. Au-delà, la protection que
vous annoncez à vos membres s'affaiblit réellement.

---

## Le message d'invitation

C'est le premier contact, et il décide de tout : une personne qui trouve ce
message suspect ne cliquera pas, ou cliquera pour répondre ce qu'elle croit
qu'on attend d'elle.

**Une contrainte technique d'abord.** Le lien de participation fait à lui seul
environ 155 caractères. Un SMS unique en contient 160 : votre message occupera
donc deux segments, facturés comme deux SMS. Prévoyez-le avec votre prestataire.

**Modèle, à adapter :**

> [Prénom], une consultation anonyme est ouverte sur [sujet en trois mots].
> Votre avis compte, quel qu'il soit. Répondre prend une minute, c'est libre, et
> personne ne saura ce que vous avez répondu. [lien]

**Ce que ce modèle évite, et pourquoi.**

*Pas de nom d'expéditeur hiérarchique.* « La Direction vous invite à » transforme
une consultation en convocation. Si votre outil impose un expéditeur, préférez le
nom du dispositif ou celui du comité social.

*Pas de date limite dans le SMS.* « Avant vendredi » ajoute une pression là où il
faut de la confiance. La date figure dans la notice, cela suffit.

*Pas de « votre participation est importante pour nous ».* Cette formule est celle
des enquêtes commerciales ; elle signale un questionnaire de plus, pas un
dispositif protégé.

*Dire « c'est libre ».* Un message venu de l'employeur se lit par défaut comme
une obligation. Trois mots suffisent à lever cela, et leur absence coûte des
réponses sincères.

**Annoncez la consultation avant d'envoyer les liens.** Un SMS contenant un lien
inconnu ressemble à une tentative d'hameçonnage — c'est même exactement la forme
qu'elles prennent. Une réunion d'équipe, une note de service ou un message du
comité social, quelques jours avant, transforme un lien suspect en lien attendu.
C'est probablement ce qui aura le plus d'effet sur votre taux de réponse.

---

## Notice d'information à joindre aux invitations

À adapter à votre organisation. Les mentions ci-dessous répondent à
l'article 13 du RGPD.

> **Consultation anonyme — information sur le traitement de vos données**
>
> **Qui vous consulte :** [nom de l'organisation], [adresse].
>
> **Pourquoi :** recueillir l'avis des [membres / agents / salariés] sur
> [objet de la consultation]. Le résultat servira à [usage prévu].
>
> **Ce qui est collecté :** votre réponse à une question unique. Aucune donnée
> permettant de vous identifier n'est enregistrée : ni votre nom, ni votre
> adresse, ni votre numéro de téléphone, ni l'heure de votre réponse.
>
> **Comment votre réponse est protégée :** le serveur qui enregistre votre
> réponse ne peut pas savoir de qui elle vient. Votre autorisation à participer
> et votre réponse sont vérifiées séparément, par un procédé cryptographique
> dont le code est public.
>
> Ce serveur n'est pas administré par [nom de l'organisation]. Il l'est par
> [nom du tiers hébergeur], qui ne dispose pas de la liste des personnes
> invitées. [Nom de l'organisation] détient cette liste, mais n'a accès ni au
> serveur ni à sa base de données : elle ne voit que des totaux.
>
> **Ce sur quoi cette protection repose, et comment le vérifier.** Elle tient au
> fait que la liste des invités et le serveur sont entre des mains différentes.
> Ce n'est pas une impossibilité physique, c'est une séparation — et vous
> pouvez la contrôler : le nom de l'hébergeur et son contrat sont communiqués
> à vos représentants du personnel, qui peuvent aussi vérifier eux-mêmes la
> configuration du serveur pendant toute la consultation.
>
> **Ce que ce dispositif protège, et ce qu'il ne cache pas.** Votre réponse est
> protégée dans tous les cas — c'est l'objet même du système. En revanche, il ne
> cache pas le fait que vous ayez participé : [nom de l'organisation] sait qui a
> été invité, et le nombre total de réponses est publié.
>
> Deux choses vous rendent la main là-dessus :
>
> — **Répondez depuis votre téléphone personnel**, sur votre connexion
> personnelle. Un appareil professionnel peut conserver la trace que vous avez
> participé — jamais ce que vous avez répondu. Ce conseil ne coûte rien et
> referme la question.
>
> — **Répondre est libre.** Ne pas répondre n'a aucune conséquence, n'a pas à
> être justifié, et ne peut vous être reproché.
>
> **En cas de doute ou de difficulté :** écrivez à [contact indépendant — comité
> social, délégué du personnel ou délégué à la protection des données]. Vous
> n'avez à justifier ni votre demande, ni ce que vous vouliez répondre.
>
> **Le résultat publié est volontairement approché**, d'environ trois points.
> C'est cette imprécision qui empêche de remonter à une réponse individuelle.
> Aucun résultat n'est publié si moins de 240 personnes de votre groupe
> répondent.
>
> **Combien de temps :** les réponses sont agrégées puis effacées à la clôture
> de la consultation, prévue le [date]. Seul le résultat collectif est
> conservé.
>
> **Vos droits :** vous pouvez refuser de participer, sans avoir à vous
> justifier et sans conséquence. En revanche, une fois votre réponse envoyée,
> nous ne pouvons ni la retrouver, ni la modifier, ni la supprimer à votre
> demande — puisque rien ne permet de savoir laquelle est la vôtre. C'est la
> contrepartie directe de l'anonymat.
>
> **Pour toute question :** [contact du délégué à la protection des données ou
> du responsable de la consultation].

**Deux points de vigilance.**

*Sur les droits.* L'avant-dernier paragraphe n'est pas une clause de style :
certains droits RGPD sont matériellement inapplicables ici. Cette impossibilité
doit être annoncée **avant** la participation, pas découverte après.

*Sur la formulation de la garantie.* Une version antérieure de cette notice
disait « le serveur en est techniquement incapable ». C'était faux, et il faut
comprendre pourquoi avant d'être tenté de le réécrire.

La cryptographie supprime le lien entre l'invitation et la réponse dans ce qui
est ENREGISTRÉ. Elle ne supprime pas le lien dans le TEMPS : qui observerait la
base pendant que la consultation tourne verrait une invitation être consommée,
puis un compteur s'incrémenter quelques secondes plus tard. Il lui manquerait la
correspondance personne → invitation — que vous détenez, et vous seule.

La protection tient donc parce que l'hébergeur n'a pas votre liste, et que vous
n'avez pas son serveur. C'est réel et c'est solide, mais c'est une séparation
des rôles. Un participant qui découvrirait après coup qu'on lui a promis une
impossibilité technique ferait plus de dégâts à votre démarche que n'importe
quelle faille.

---

## À faire figurer dans votre registre de traitement

- **Finalité :** consultation interne anonyme
- **Base légale :** intérêt légitime, ou consentement selon le contexte — à
  déterminer avec votre DPO
- **Catégories de données :** réponses agrégées, sans identifiant
- **Destinataires :** l'organisation ; l'hébergeur du serveur
- **Durée de conservation :** jusqu'à la clôture, puis effacement actif
- **Sous-traitant :** l'hébergeur — un contrat au sens de l'article 28 est
  nécessaire s'il est distinct de votre organisation

---

## Deux questions à trancher avec votre DPO

**Qui héberge le serveur ?** C'est la question la plus importante, et elle est
souvent mal comprise.

Si votre organisation héberge elle-même, l'anonymat tient contre un
administrateur qui ne cherche pas activement à le contourner — pas contre une
organisation qui le voudrait vraiment. Or c'est précisément l'organisation dont
vos membres se méfient. La garantie que vous leur annoncez repose alors sur
votre parole.

**VERA propose l'hébergement.** Le serveur est alors administré par le
mainteneur du protocole, distinct de vous : vous n'avez accès ni au serveur, ni
à la base, ni aux journaux, seulement au tableau de bord qui n'affiche que des
agrégats. Vous ne pouvez pas désanonymiser une réponse, et vos membres peuvent
le vérifier — ce n'est plus une promesse que vous leur faites, c'est une
propriété de l'architecture.

Vos membres, ou leurs représentants, peuvent d'ailleurs vérifier eux-mêmes que
le code exécuté sur leur téléphone est bien celui qui a été publié et audité :
la procédure tient en deux commandes (`VERIFICATION_CLIENT.md`).

Détail complet : `VERA_THREAT_MODEL_COMPLETE.md`, section 1.

**Les sauvegardes.** L'effacement à la clôture porte sur la base active. Si
votre hébergeur réalise des instantanés automatiques, une copie antérieure peut
subsister — vérifiez sa politique de rétention et faites-la coïncider avec
l'engagement pris auprès des participants.

Un point mérite d'être compris, car il est contre-intuitif : **un instantané
pris pendant la consultation est plus sensible qu'un instantané pris après.**
Après clôture, il ne reste que des données effacées.

Pendant, c'est différent. La base ne conserve aucun vote individuel, mais elle
enregistre en direct deux choses : quelles invitations ont été utilisées, et
combien de réponses chaque option a reçues. Qui lirait cette base **plusieurs
fois pendant la consultation** verrait une invitation être utilisée, puis un
compteur augmenter quelques secondes plus tard — et pourrait les rapprocher.

Il lui manquerait la correspondance personne → invitation, que vous détenez et
vous seule. C'est là que se joue la protection : elle tient parce que
l'hébergeur n'a pas votre liste.

**Ce que cela implique concrètement pour vous.** Pendant toute la fenêtre de
consultation, aucune lecture répétée de la base ne doit avoir lieu : pas
d'instantanés d'hyperviseur, pas de sauvegardes incrémentales, pas d'agent de
supervision qui parcourt les fichiers. C'est un point à inscrire dans votre
contrat d'hébergement, pas une simple recommandation technique.

---

## Ce pour quoi VERA n'est pas conçu

- **Un scrutin contraignant ou juridiquement opposable.** Il n'y a ni reçu, ni
  recomptage possible : un décompte vérifiable trahirait les personnes que la
  perturbation protège. Les deux exigences sont incompatibles.
- **Un dispositif d'alerte professionnelle.** VERA agrège des réponses fermées.
  Il n'y a ni suivi individuel, ni échange, ni traitement au cas par cas — ce
  qu'exige un dispositif d'alerte.
- **Des données de santé ou des catégories particulières** au sens de
  l'article 9 du RGPD.

---

## Si le service devient indisponible pendant une consultation

Ce cas doit être anticipé avant qu'il ne survienne, pas découvert au mauvais
moment.

**Ce qui se passe.** Les liens de participation portent une clé de signature
valable sept jours. Si le service ne redémarre pas dans ce délai, ils expirent :
les personnes qui n'avaient pas encore voté ne le peuvent plus, et les réponses
non publiées sont perdues. Il faut alors relancer la consultation avec de
nouveaux liens.

**Ce que cela signifie pour vous.** Sauvegardez les résultats dès qu'un groupe
devient publiable, sans attendre la clôture. Le tableau de bord vous le signale.
Et prévoyez, dans votre communication interne, qu'une consultation puisse être
relancée — plutôt que de l'annoncer comme un événement unique.

**Ce qui rend une reprise possible, et ses limites.** Le service ne peut
redémarrer qu'avec la clé de chiffrement qui protège les clés de signature en
base. Sans elle, les données existantes sont définitivement illisibles — c'est
une protection voulue, pas un défaut : elle garantit qu'une copie volée de la
base ne révèle rien.

Cette clé est aujourd'hui conservée par le mainteneur, hors du serveur. Cela
couvre une panne matérielle ou la perte du serveur. Cela ne couvre pas
l'indisponibilité prolongée du mainteneur lui-même.

**Pour une consultation à enjeu, exigez davantage.** Le dépôt de cette clé chez
un tiers — votre service informatique, un notaire, un séquestre — avec une
procédure de reprise écrite. C'est la seule façon de rendre la continuité
indépendante d'une personne. Tant que ce n'est pas fait, considérez qu'une
consultation interrompue devra être relancée.

**Un point mineur, mais qui surprend.** Un redémarrage du service déconnecte la
session de l'organisateur : les sessions ne sont pas conservées. Il suffit de se
reconnecter, rien n'est perdu.

---

## En cas de problème

Signalement de sécurité : voir `SECURITY.md`.

VERA est développé et maintenu par une seule personne. Pour un déploiement à
fort enjeu, prévoyez un interlocuteur technique de votre côté, capable de lire
le code et de reprendre l'exploitation si nécessaire. Tout est public,
primitive cryptographique comprise, précisément pour rendre cette reprise
possible.
