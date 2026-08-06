# Vérifier que le serveur sert bien le code publié

Ce document permet de vérifier, sans autorisation ni compte, que le code servi
par le serveur correspond exactement à celui publié dans ce dépôt.

En pratique, cette vérification ne sera pas faite par les participants — elle
demande deux commandes en ligne de commande. Elle s'adresse à un délégué du
personnel, un délégué à la protection des données, un service informatique ou un
auditeur externe : quelqu'un qui contrôle *pour* les participants. C'est cette
possibilité de contrôle par un tiers qui a de la valeur, pas son exercice par
chacun.

## Pourquoi cette vérification est la plus importante

Le protocole repose sur une propriété : le secret d'un votant est aveuglé
**dans son navigateur**, avant d'être envoyé au serveur. Le serveur signe sans
jamais voir ce qu'il signe.

Un serveur malveillant n'aurait donc pas besoin de casser la cryptographie. Il
lui suffirait de servir un JavaScript modifié qui recopie le secret avant
l'aveuglement — et le lien entre une personne et sa réponse serait rétabli à la
source, sans qu'aucune analyse du serveur ne le révèle.

C'est le scénario le plus grave contre lequel VERA doit se protéger, et c'est
précisément celui que ces empreintes ferment.

## Empreintes de référence

Version du 5 août 2026 :

```
44fcdbf6db3c16bde05447f4650e94e1f36d68e4bcbb8a6cc8acf71e02c79cfc  static/vote.html
08e678cc5d64e9996cfe3cf54eb1220a1bb032c54d0c4351651f8aee057baa66  static/blindrsa-bundle.js
```

## Procédure

Deux commandes suffisent. Elles n'exigent aucun accès particulier.

```bash
curl -s https://vera-consultation.duckdns.org/vote | sha256sum
curl -s https://vera-consultation.duckdns.org/static/blindrsa-bundle.js | sha256sum
```

Comparez avec les empreintes ci-dessus, et avec celles que vous obtenez en
calculant vous-même sur le dépôt :

```bash
git clone https://github.com/taha-vera/projet-vera-consultations-.git
cd projet-vera-consultations-
sha256sum static/vote.html static/blindrsa-bundle.js
```

**Les trois séries doivent être identiques** : ce que le serveur envoie, ce que
le dépôt contient, ce qui est annoncé ici.

Si une seule diffère, ne votez pas et signalez-le (voir `SECURITY.md`).

## Ce que cette vérification établit

- Le code exécuté dans le navigateur du votant est celui qui a été publié et
  qui peut être audité.
- Aucun intermédiaire — hébergeur, réseau, opérateur — ne l'a modifié en
  transit.
- Le mécanisme d'aveuglement est bien celui décrit dans le modèle de menace.

## Ce qu'elle n'établit pas

**Ce qu'a reçu un autre visiteur.** La vérification établit ce que ce serveur a
servi *à vous, à cet instant, depuis votre connexion*. Un serveur malveillant
pourrait servir le code publié à qui vérifie et un code modifié aux navigateurs
mobiles pendant la fenêtre de vote. Rien dans cette procédure ne l'exclut.

**Que le serveur exécute le code Python publié.** Le code serveur n'est pas
transmis au visiteur : il n'y a donc rien à comparer. Aucune empreinte ne peut
le prouver.

Établir cette seconde moitié exigerait de l'attestation matérielle — une mesure
du code en cours d'exécution, signée par le processeur (SEV-SNP, TDX ou
équivalent). VERA ne dispose pas de ce dispositif aujourd'hui. Nous le disons
plutôt que de laisser croire que la vérification est complète.

**Ce que cela change en pratique : un vecteur sur trois.** Vérifier le client
ferme la voie la plus directe — un JavaScript modifié qui recopierait le secret
avant l'aveuglement. C'est réel, et c'est le vecteur le plus simple à exploiter.

Ce n'est pas le seul. Deux autres restent ouverts à un opérateur malveillant,
avec un client parfaitement conforme aux empreintes ci-dessus :

- **La corrélation entre les deux requêtes du parcours.** La demande de
  signature porte le jeton d'invitation, donc l'identité via la liste de
  l'organisation. Le dépôt du vote porte la réponse. Les deux partent du même
  appareil à quelques secondes d'intervalle. Un opérateur qui journalise leur
  source relie les deux sans toucher au JavaScript ni à la cryptographie.
- **La substitution de clé par votant.** L'empreinte `#k=` du lien est calculée
  par le serveur lui-même. Un serveur modifié peut générer une clé distincte
  par jeton et l'empreinte correspondante : le contrôle côté client passe, et
  le serveur retrouve ensuite quel votant a produit quelle signature en
  essayant ses clés. Un engagement n'a de valeur que s'il est émis par une
  partie distincte de celle qu'il contraint ; ce n'est pas le cas ici.

Ces deux vecteurs relèvent du Niveau 2 du modèle d'adversaire — un opérateur qui
cherche activement à contourner le système — et sont documentés comme hors
garantie. Aucune vérification côté client ne les ferme.

## Après chaque mise à jour

Les empreintes changent à chaque modification du client. Elles sont mises à
jour dans ce document au même commit que le déploiement, de sorte que la
version publiée et la version servie ne divergent jamais.

Pour retrouver les empreintes d'une version antérieure :

```bash
git log --oneline -- VERIFICATION_CLIENT.md
git show <commit>:VERIFICATION_CLIENT.md
```
