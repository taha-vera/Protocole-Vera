# VERA Consultation

*Agrégation à confidentialité différentielle, non-persistante.*

VERA publie un résultat collectif (sondage sensible, consultation interne)
sans jamais rendre lisible la contribution d'un individu.

> **Vous participez à une consultation ?** Le lien que vous avez reçu suffit,
> vous n'avez rien à faire ici. Cette page s'adresse à ceux qui évaluent ou
> vérifient VERA.
>
> **Vous envisagez d'utiliser VERA dans votre organisation ?** Commencez par
> la [présentation](https://taha-vera.github.io/projet-vera-consultations-/),
> puis le [guide de déploiement](GUIDE_DEPLOIEMENT.md) — il contient les
> conditions d'usage, la notice RGPD à joindre aux invitations, et ce qui
> reste de votre responsabilité.
>
> **Vous êtes DPO, responsable informatique ou auditeur ?** Le détail se trouve
> dans [LIMITS.md](LIMITS.md) et le [modèle de menace](VERA_THREAT_MODEL_COMPLETE.md).
> Le code est intégralement lisible, primitive cryptographique comprise
> ([vera_blind_sig/](vera_blind_sig/)), et vous pouvez vérifier en deux
> commandes que le serveur sert bien ce code
> ([VERIFICATION_CLIENT.md](VERIFICATION_CLIENT.md)).

**Ce que VERA garantit.** Aucune réponse ne peut être reliée à une personne par
l'organisateur de la consultation, ni par un tiers, ni par un administrateur qui
lirait la base. Cette propriété est **structurelle** (signature aveugle RSABSSA,
registres disjoints) : le serveur ne stocke jamais le lien entre une identité et
un vote.

Face à un opérateur d'infrastructure qui chercherait **activement** à contourner
le système — en servant un client modifié ou en corrélant ses propres journaux —
la garantie ne tient plus : c'est pourquoi l'hébergement doit être assuré par un
tiers distinct de l'organisation qui consulte. Détail :
[modèle de menace](VERA_THREAT_MODEL_COMPLETE.md), section 1. Les garanties statistiques sur les résultats publiés
(confidentialité différentielle, ε=0.5) reposent sur des hypothèses documentées
dans [LIMITS.md](LIMITS.md).

**Ce qui reste de la responsabilité de l'organisation.** VERA ne connaît pas la
liste de vos membres : c'est ce qui protège leur anonymat. La contrepartie est
que VERA ne peut vérifier ni que les invitations sont parties aux bonnes
personnes, ni qu'elles ne sont parties qu'à elles. La fiabilité des résultats
repose donc sur l'intégrité de la liste de diffusion, qui est de votre ressort.
Pour une consultation informelle, publier le nombre d'invitations envoyées et
faire vérifier la liste par une seconde personne suffit généralement. Pour un
scrutin contraignant ou juridiquement opposable, cette garantie manquante est
rédhibitoire : VERA n'est pas conçu pour cet usage. Détail technique :
[LIMITS.md §13](LIMITS.md).

**Règle d'usage.** Le budget de confidentialité (ε=0.5) s'applique **par
consultation**, et non par cohorte : il est remis à zéro à chaque clôture.
Reposer une question à la même population k fois coûte ε = 0.5 × k sur ces
personnes. VERA ne peut pas l'empêcher techniquement — suivre l'exposition
d'un individu supposerait de l'identifier, ce que l'anonymat interdit, et le
nom de département reste modifiable par l'organisateur. La protection est donc
une règle d'usage : **pas plus de 4 consultations par période de 12 mois
glissants sur la même population** (ε cumulé = 2.0, dernier palier
défendable). Barème complet et justification : [LIMITS.md §14](LIMITS.md).

- *Modèle de menace complet (26 portes)* : [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)
- *Mécanisme de bruit en production* : [vera_dp_noise.py](vera_dp_noise.py) (OpenDP, Δ=2, scale=4, ε=0.5, bounds=(0,10000))
- *Persistance chiffrée de l'état (Portes 11, 14)* : [vera_persistance.py](vera_persistance.py) (SQLite WAL, Fernet/AES-128)
- *Porte 7 (signature aveugle, production)* : [vera_signature_manager.py](vera_signature_manager.py) et [vera_blind_sig/](vera_blind_sig/) — primitive RSABSSA RFC 9474. L'aveuglement et la finalisation ont lieu dans le navigateur du votant : le serveur ne voit ni le secret ni la signature finale.

## Antériorité (DOI Zenodo)

- v1.0 (2026-06-12) : https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) : https://doi.org/10.5281/zenodo.20671969

## État des portes

Le modèle de menace couvre **26 portes** : 22 fermées avec preuve reproductible
sur le serveur de production, 4 limites assumées et documentées.

Le détail complet — vecteur, statut, preuve — est tenu dans deux documents,
poussés avec le code à chaque déploiement :

- [VERA_AUDIT_REFERENCE.md](VERA_AUDIT_REFERENCE.md) — synthèse et paramètres
- [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md) — modèle de
  menace détaillé, modèle d'adversaire, analyses

## Méthode de vérification

Le code est audité en lecture réelle, pas seulement sur description — plusieurs
correctifs importants n'ont été trouvés que de cette façon, dont un bug qui
invalidait la garantie ε. Chaque porte marquée « fermée » l'a été après
vérification sur le serveur de production, avec une preuve reproductible.

Une porte fermée peut être rouverte par une fonctionnalité ajoutée plus tard.
Ce n'est pas une précaution théorique : c'est arrivé deux fois sur ce projet,
dont une fois sans être détecté pendant quatorze jours. Toute modification
touchant les mécanismes d'une porte fermée doit donc s'accompagner d'une
re-vérification de celle-ci.

*Cette consigne s'adresse à qui modifie le code. Elle n'implique aucune
vérification de la part de l'organisation qui utilise VERA.*

## Précision réelle et seuil de publication (mesuré le 14/07/2026)

VERA publie une **estimation certifiée**, pas un décompte exact. Le bruit est le prix de l'anonymat.

**Seuil de publication : K_MIN = 240.** En dessous, VERA **refuse de publier** — pas de version dégradée, pas de résultat "peu fiable", rien du tout.

Ce seuil n'est pas choisi arbitrairement, il est **mesuré**. À ε=0.5, avec projection sur le simplexe, l'erreur maximale sur les trois options (95e centile, pire répartition, 3000 simulations) :

| Effectif | Erreur max (95e centile) |
|---|---|
| n = 100 | 12 % |
| n = 150 | 8 % |
| n = 200 | 6 % |
| **n = 240** | **5 %** ← seuil de publication |
| n = 300 | 4 % |
| n = 500 | 2,5 % |

**Ce que voit l'organisation** : des comptages entiers qui somment exactement à l'effectif réel (grâce à la projection, post-traitement gratuit en ε). Exemple vérifié en production sur 250 votants réels : vérité 130/80/40 → publié 123/84/43, somme exacte 250, erreur max 2,8 %.

**Pour qui VERA est conçu** : organisations dont les groupes consultés dépassent 240 personnes — grandes entreprises et groupes, fonction publique, hôpitaux, universités, syndicats de branche. Les structures plus petites ne peuvent pas obtenir un résultat à la fois anonyme et suffisamment précis à ε=0.5 : c'est une contrainte mathématique, pas un choix commercial.

**Durée maximale d'une consultation : 7 jours.** Passé ce délai, les clés de signature sont automatiquement détruites et plus aucun vote n'est accepté. Cette limite se combine au seuil : un groupe doit réunir ses 240 réponses **dans la fenêtre d'une semaine**, relances comprises. Distribuez les liens rapidement et relancez tôt — un groupe qui n'atteint pas le seuil avant l'expiration ne publiera aucun résultat. Détail : LIMITS.md §10.

**Sur ε=0.5** : c'est un régime de confidentialité plus strict que les déploiements DP industriels connus (Apple : ε=2–16 ; Google RAPPOR : ε=2–9 ; US Census 2020 : ε≈19,6). L'imprécision sur les petites cohortes n'est pas un défaut d'implémentation — c'est la garantie qui s'exerce.

## Effacement actif et vérifiable (clôture de consultation)

VERA ne se contente pas de ne rien conserver *après coup* : il permet à l'organisateur d'**effacer activement** toutes les données du serveur, et de le prouver.

L'endpoint `POST /api/rh/cloturer` (bouton « Clôturer » dans l'interface) :
1. renvoie les résultats finaux une dernière fois (l'organisateur doit les sauvegarder),
2. efface définitivement **tout l'état brut** : compteurs, effectifs, codes de participation, tokens consommés, budget ε, résultats publiés, et la clé de signature,
3. rouvre une consultation neuve (nouvelle clé) pour un usage ultérieur.

Après clôture, un accès au serveur ne révèle **plus rien** de la consultation passée. C'est la garantie de minimisation des données (RGPD art. 5) rendue opérationnelle et démontrable — pas une promesse, une action testable. Vérifié en conditions réelles : un état de 10 départements est ramené à 0 après clôture.

## Limites assumées

L1 observateur réseau · L2 coercition · L3 petits effectifs (refus de publier
sous seuil) · L4 qualification RGPD anonymisation/pseudonymisation (avis
CNIL/DPO externe requis, non tranché).


## Licence

Voir [LICENSE](LICENSE). Documents : CC-BY 4.0.
