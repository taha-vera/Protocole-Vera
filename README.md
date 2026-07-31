# VERA Consultation

*Agrégation à confidentialité différentielle, non-persistante.*

VERA publie un résultat collectif (sondage sensible, consultation interne)
sans jamais rendre lisible la contribution d'un individu — et le prouve.

**Périmètre de la garantie.** VERA garantit l'**anonymat**, pas l'**intégrité du
scrutin**. Le système ne dispose d'aucune liste de référence des personnes
invitées — c'est ce qui protège l'anonymat — et ne peut donc pas attester que
les jetons émis correspondent à de vraies personnes distinctes, ni qu'aucun n'a
été utilisé par l'organisateur. Il n'y a ni reçu votant, ni urne publique, ni
recomptage possible : la vérifiabilité de bout en bout exige un décompte exact,
incompatible avec le décompte bruité qu'impose la confidentialité
différentielle. VERA convient à une consultation d'opinion, pas à un scrutin
contraignant ou juridiquement opposable. Détail complet : [LIMITS.md §13](LIMITS.md).

**Règle d'usage.** Le budget de confidentialité (ε=0.5) s'applique **par
consultation**, et non par cohorte : il est remis à zéro à chaque clôture.
Reposer une question à la même population k fois coûte ε = 0.5 × k sur ces
personnes. VERA ne peut pas l'empêcher techniquement — suivre l'exposition
d'un individu supposerait de l'identifier, ce que l'anonymat interdit, et le
nom de département reste modifiable par l'organisateur. La protection est donc
une règle d'usage : **pas plus de 4 consultations par période de 12 mois
glissants sur la même population** (ε cumulé = 2.0, dernier palier
défendable). Barème complet et justification : [LIMITS.md §14](LIMITS.md).

- *Modèle de menace complet (17 portes)* : [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)
- *Mécanisme de bruit en production* : [vera_dp_noise.py](vera_dp_noise.py) (OpenDP, Δ=2, scale=4, ε=0.5, bounds=(0,10000))
- *Persistance chiffrée de l'état (Portes 11, 14)* : [vera_persistance.py](vera_persistance.py) (SQLite WAL, Fernet/AES-128)
- *Porte 7 (signature aveugle, production)* : [vera_signature_manager.py](vera_signature_manager.py) — primitive RSABSSA RFC 9474 (standard audite). La *logique* de partition (un token par individu/epoque, anti-rejeu, blocage 49/1) est validee sur un prototype dans [archive/test_porte7.py](archive/test_porte7.py) ; ce prototype (archive/vera_token.py) n'est PAS la primitive de production et n'est pas utilise par le serveur.

## Antériorité (DOI Zenodo)

- v1.0 (2026-06-12) : https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) : https://doi.org/10.5281/zenodo.20671969

## État des portes (résumé, 1-17 -- table complète à 26 portes dans [VERA_AUDIT_REFERENCE.md](VERA_AUDIT_REFERENCE.md))

> Ce tableau n'a pas suivi toutes les mises à jour de sécurité. Pour l'état
> complet et à jour (26 portes, dont 9 fermées après le 13/07/2026), se référer
> à [VERA_AUDIT_REFERENCE.md](VERA_AUDIT_REFERENCE.md), tenu dans le dépôt et
> poussé avec le code à chaque déploiement.

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | Fermée — Δ=2, scale=4, ε=0.5 vérifié |
| 2. MIA générale | Fermée — AUC=0.6209, IC95% [0.6185, 0.6232], borne théorique 0.6225 incluse (N=100 000, bootstrap) |
| 3. Canal temporel | Fermée — fuite sub-microseconde (0.209µs), inexploitable via réseau |
| 4. Composition séquentielle | Réouverte 17/07, limite assumée — le budget est remis à zéro à CHAQUE clôture (non par cohorte). Détail et règle d'usage : [LIMITS.md §14](LIMITS.md) |
| 5. Observateur réseau | Hors-périmètre, assumé (VPN/Tor au choix utilisateur) |
| 6. Coercition | Hors-périmètre, limite partagée par tout système de vote |
| 7. Différenciation « 49/1 » | Fermée — primitive RSABSSA RFC 9474 + unlinkability EFFECTIVE depuis le refactor Modèle B (23/07/2026). L'aveuglement et la finalisation ont lieu dans le navigateur du votant (static/vote.html, lib auto-hébergée) : le serveur ne voit jamais le secret K ni la signature finale, et ne peut relier ni le jeton d'autorisation au vote, ni l'identité à la réponse. Une clé RSA par département, empreinte engagée dans le lien de participation et vérifiée côté client (parade substitution de clé). Vérifié bout-en-bout : chantier_crypto/test_vote_complet.mjs, test_brique7.mjs. LIMITE : garantie valable contre un tiers et un opérateur honnête-mais-curieux (Niveau 1 du modèle d'adversaire) ; contre un opérateur activement malveillant qui sert le JS et détient les clés, un hébergement tiers est nécessaire — voir la section Modèle d'adversaire du threat model. |
| 8. Inférence outlier | Fermée — AUC=0.6209, IC95% [0.6185, 0.6232] (même mesure que Porte 2) |
| 9. Collusion émetteur/agrégateur | Fermée — secret admin distinct, comptes séparés |
| 10. Sondage binaire K_MIN | Fermée — effectif/fiable retirés de l'API |
| 11. Accès direct SQLite / clé RSA | Fermée — chiffrement Fernet/AES-128, salt PBKDF2 aléatoire, crash-testée |
| 12. Secret admin visible /proc | Limite assumée (contexte solo-root) |
| 13. Soustraction d'agrégats | Limite irréductible DP, atténuée par budget ε PAR CONSULTATION uniquement (même réserve que Porte 4) |
| 14. Non-persistance de l'état | Fermée — SQLite WAL, crash-testée (kill -9 réel) |
| 15. Trafic en clair (HTTP) | Fermée — HTTPS via Nginx + Let's Encrypt, redirection automatique verifiee |
| 16. Retention des logs applicatifs | Fermée — purge manuelle a cloture + logrotate 3 jours en filet de securite |
| 17. Correlation temporelle (horodatage_unix) | Limite assumee — protection reelle via K_MIN=240, pas via masquage du timing |

## Corrections suite à audit de code (13/07/2026)

Un audit du code réel (pas seulement de la documentation) a révélé et permis de corriger cinq points, tous vérifiés empiriquement :

- **Bug critique corrigé** : le résultat bruité est désormais figé après la première publication (table resultats_publies). Auparavant, chaque appel à /api/rh/resultats re-tirait du bruit, ce qui aurait permis de moyenner plusieurs tirages et de contourner la garantie ε. Vérifié : 5 appels successifs renvoient un résultat identique.
- **Garde worker unique** : le service refuse de démarrer avec plusieurs workers (l'état DP en mémoire n'est pas partagé entre processus). Protège la composition ε (Porte 4) par construction.
- Endpoints de test retirés de la production (ne consomment plus de tokens réels).
- Anti-bruteforce corrigé pour lire l'IP réelle derrière le reverse proxy.
- Schéma SQLite complété pour un déploiement propre from scratch.

Détail complet et preuves dans VERA_THREAT_MODEL_COMPLETE.md et VERA_CHALLENGE_REGISTER.md.

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
