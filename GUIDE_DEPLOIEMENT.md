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

## Les quatre étapes

### 1. Préparer la question

Une seule question, trois réponses possibles : oui, non, je m'abstiens.

La question se fige dès la génération du premier lien et ne peut plus être
modifiée. C'est volontaire : la changer en cours de route permettrait de
mélanger des réponses portant sur deux questions différentes.

Formulez-la donc soigneusement, et faites-la relire — idéalement par un
représentant du personnel, qui verra ce que vous ne voyez plus.

### 2. Vérifier la taille du groupe

**Aucun résultat n'est publié sous 240 réponses.** Ce n'est pas un réglage, c'est
une protection : en dessous, une réponse individuelle redeviendrait devinable.

Conséquence pratique : ne découpez pas votre organisation en petits services.
Un groupe de 50 personnes ne produira jamais de résultat, et vous ne
l'apprendrez qu'à la fin. Le tableau de bord vous avertit dès la génération si
un groupe est trop petit — tenez-en compte.

Prévoyez large : 240 est le nombre de **réponses**, pas d'invitations. À 60 % de
participation, il faut inviter 400 personnes.

### 3. Envoyer les invitations

Le tableau de bord génère les liens et propose un export CSV
(département, lien, message).

Vous chargez ce fichier dans **votre propre** outil d'envoi de SMS ou de
courriel. VERA n'envoie rien lui-même et ne voit jamais un numéro de téléphone.

Trois précautions :

- Le fichier exporté contient les liens de vote. Quiconque l'obtient peut voter
  à la place de vos membres. Traitez-le comme confidentiel, et **supprimez-le
  après envoi**.
- Chaque lien est personnel et à usage unique. Prévenez les participants de ne
  pas le transférer.
- Joignez la notice d'information (modèle ci-dessous).

### 4. Publier

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
> **Comment votre anonymat est protégé :** le système utilisé ne conserve à
> aucun moment le lien entre une personne et sa réponse. Ce n'est pas un
> engagement de notre part : le serveur en est techniquement incapable. Le
> fonctionnement est public et vérifiable.
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

**Point de vigilance.** L'avant-dernier paragraphe n'est pas une clause de
style : certains droits RGPD sont matériellement inapplicables ici. Cette
impossibilité doit être annoncée **avant** la participation, pas découverte
après.

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
Après clôture, il ne reste que des données effacées. Pendant, le journal
d'écriture de la base conserve la trace des derniers votes enregistrés, dans
l'ordre. VERA le tronque toutes les vingt écritures pour borner cette fenêtre,
mais elle n'est pas nulle. Si votre hébergeur prend des instantanés fréquents,
c'est le moment de la consultation qu'il faut protéger en priorité.

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
