# VERA Consultation -- Document de reference pour audit de securite

**Version :** 2.0 -- 31/07/2026
**Depot :** https://github.com/taha-vera/projet-vera-consultations-
**Contact :** tahahouari@hotmail.fr
**URL production :** https://vera-consultation.duckdns.org

**Note sur cette version.** La version 1.0 (09/07/2026) pointait par erreur vers
un autre depot (Protocole-Vera, celui d'ANCRE) et n'integrait pas trois semaines
de travail : la fermeture des Portes 18-19, une reouverture de Porte non
detectee, la purge complete d'un audit de securite externe (16 constats), et la
rotation de trois secrets exposes. Cette version corrige les deux et fusionne
l'ensemble en un seul document a jour.

---

## 1. Description du systeme

VERA Consultation est un protocole open source de sondage anonyme pour
organisations (RH, associations, syndicats). Il publie un resultat
collectif bruite sans jamais exposer la contribution individuelle,
et le prouve mathematiquement -- au prix d'une limite assumee et documentee :
il ne prouve PAS l'integrite du scrutin (cf. section 9).

**Flux nominal :**
1. Un compte RH ouvre une consultation et genere N jetons anonymes
2. Chaque participant recoit un jeton, vote une fois, le jeton est detruit
3. Les votes sont agreges, bruites par Laplace discret (OpenDP)
4. Le compte RH declenche EXPLICITEMENT la publication (POST /api/rh/publier
   ou cloture) -- la lecture du tableau de bord ne publie plus rien (Porte 20)
5. Le resultat bruite est fige a la premiere publication ; relire ne re-tire
   jamais de bruit

**Invariants garantis par le code :**
- La donnee brute n'est jamais exposee au votant ni a un tiers
- Les sorties publiees sont des agregats statistiques bruites, irreversibles
- Budget epsilon plafonne et borne PAR CONSULTATION (limite documentee en
  section 9 : ne survit pas a la cloture)
- Un jeton anonyme par individu et par consultation (anti double-reponse)
- A la cloture, l'etat brut de la consultation est efface (compteurs,
  effectifs, jetons, cle de signature) -- verifiable, teste 10 -> 0
- Limites documentees, pas dissimulees

---

## 2. Architecture technique

| Composant | Detail |
|---|---|
| Runtime | Python 3.14, FastAPI, uvicorn (1 worker, GIL) |
| Transport | HTTPS (Nginx + Let's Encrypt, vera-consultation.duckdns.org) |
| Persistance | SQLite WAL, write-through, /root/vera_state.db |
| Serveur | Hetzner Cloud, 2 vCPU AMD EPYC, 4GB RAM, Ubuntu 26.04 LTS |
| Supervision | systemd (Restart=on-failure), reboot complet teste |
| DNS | DuckDNS (service tiers gratuit) |
| Certificat | Let's Encrypt, renouvellement automatique Certbot |
| Rate-limit | Nginx limit_req, 5r/s + rafale 50, sur les 4 routes de vote (Porte 22) |
| En-tetes securite | CSP, HSTS, X-Frame-Options, Referrer-Policy no-referrer (Porte 23) |

**Modules principaux :**
- vera_dp_noise.py -- bruit Laplace discret (OpenDP)
- vera_signature_manager.py -- signature aveugle RSABSSA (RFC 9474)
- vera_persistance.py -- SQLite, chiffrement partiel (cle RSA uniquement)
- vera_epsilon_budget.py -- budget epsilon par population, PAR CONSULTATION
- vera_consultation_api.py -- API FastAPI
- vera_admin_auth.py -- comptes RH, PBKDF2, EN MEMOIRE (non persiste, cf. section 6)

---

## 3. Parametres de confidentialite differentielle

| Parametre | Valeur | Justification |
|---|---|---|
| Mecanisme | Laplace discret (OpenDP) | Bibliotheque auditee, garantie analytique |
| Delta_1 | 2 | Sensibilite L1 de l'histogramme. Sous adjacence par SUBSTITUTION, un individu qui change d'avis modifie DEUX cases (-1 sur une, +1 sur une autre) -> Delta_1 = 2. Mecanisme = Laplace VECTORIEL sur R^3. Ce n'est PAS de la composition parallele (celle-ci exigerait qu'un individu n'affecte qu'une case). |
| Scale | 4 | scale = Delta_1 / epsilon = 2 / 0.5 = 4 |
| epsilon par publication | 0.5 | Calcule analytiquement par meas.map() |
| Bounds | (0, 10000) | Plafond effectif d'un departement |
| Budget PAR CONSULTATION | epsilon_total = 0.5 | UNE publication par population PAR CONSULTATION (resultat fige, pas de re-publication). NE SURVIT PAS a la cloture -- voir section 9, limite structurelle et non corrigeable |
| Indexation budget | Par departement (population), pas par question | A l'interieur d'une consultation uniquement |
| K_MIN | 240 | Seuil MESURE (14/07/2026), pas suppose. Sous ce seuil : REFUS de publier (pas de version degradee, rien). A eps=0.5 avec projection, l'erreur max sur les 3 options reste sous 5% de l'effectif dans 95% des publications a partir de n=240. En dessous : n=200 -> 6%, n=150 -> 8%, n=100 -> 12%. |

**Verifications empiriques :**
- AUC MIA = 0.6209 (test 50 vs 52, Delta=2, N=100000, IC95%=[0.6185,0.6232])
- Borne theorique pire cas : 0.6225 -- AUC dans IC confirme (True)
- Canal temporel : Spearman rho=-0.14 p=0.76 (N=10000, 7 valeurs testees), inexploitable via reseau (latence 50-100ms)
- Budget robuste sous 10 requetes concurrentes (verrou threading.Lock)
- Publication figee verifiee : 2 appels POST /api/rh/publier successifs renvoient un resultat identique, epsilon_consomme et nombre_publications inchanges (31/07/2026, preuve fonctionnelle sur departement fictif 250 votants)

---

## 4. Cryptographie

| Element | Detail |
|---|---|
| Signature aveugle | RSABSSA-SHA384-PSS-Randomized (RFC 9474), module Rust/PyO3 |
| Rotation cle RSA | Par consultation (48h ou cloture explicite), threading.Timer |
| Persistance cle privee | Fernet/AES-128 + PBKDF2-SHA256 (100 000 iterations, salt aleatoire 16 bytes, os.urandom) |
| Secret de derivation | VERA_DB_KEY (variable d'environnement systemd, permissions 600). ROTE le 31/07/2026 (Porte 25) |
| Anti-rejeu | Empreinte SHA-256 du jeton. Table tokens_consommes en WITHOUT ROWID depuis le 23/07 (Porte 17 durcie) -- l'ordre d'insertion ne fuit plus, seule l'empreinte (pseudo-aleatoire) ordonne la table |
| Transport | TLS via Nginx + Let's Encrypt, redirection HTTP->HTTPS 301 |
| Fail-closed | Si vera_blind_sig ne charge pas : RuntimeError, refus de demarrer |
| Anti-bruteforce | /api/rh/connexion et /api/resoudre_code : 5 echecs max par IP (lue via X-Real-IP/X-Forwarded-For depuis le 22/07), blocage 5 minutes. Protection en memoire (perdue au redemarrage -- limite assumee) |
| Padding constant (P-A) | LONGUEUR_CIBLE_FIXE = 200 (porte de 96 le 31/07 -- Porte 21 : a 96, un departement de 87+ caracteres faisait fuiter la distinction oui/abstention par taille de paquet TLS) |

---

## 5. Modele de menace -- 26 portes

| # | Vecteur | Statut | Preuve / Note |
|---|---|---|---|
| 1 | Mecanisme de bruit | Fermee | OpenDP, Delta=2, scale=4, epsilon=0.5 exact |
| 2 | MIA generale | Fermee | AUC=0.6209, IC95%=[0.6185,0.6232], borne theorique 0.6225 incluse |
| 3 | Canal temporel | Fermee | Spearman rho=-0.14 p=0.76 (7 valeurs, N=10000), inexploitable via reseau |
| 4 | Composition sequentielle | REOUVERTE 17/07, LIMITE ASSUMEE 31/07 | Voir section 9. Budget PAR CONSULTATION, pas PAR COHORTE : la cloture du 17/07 (Porte 24) vide budget_epsilon a chaque fois. La note du 05/07 affirmant que le budget s'accumule entre consultations est INVALIDEE par cette fonctionnalite posterieure. Regle d'usage : 4 consultations/an max sur la meme population |
| 5 | Observateur reseau | Assumee | Hors-perimetre, delegue VPN/Tor |
| 6 | Coercition | Assumee | Limite partagee par tout systeme de vote |
| 7 | Differentiation 49/1 | Fermee | RSABSSA RFC 9474, fail-closed teste dans les deux sens |
| 8 | Inference outlier | Fermee | AUC=0.6209, TPR@1%FPR=1.6% |
| 9 | Collusion emetteur/agregateur | Fermee | Secret admin distinct, isolation testee |
| 10 | Sondage binaire K_MIN | Fermee | K_MIN=240 verifie avant consommation de budget |
| 11 | Acces SQLite / cle RSA | Fermee | Fernet/AES-128, salt PBKDF2 aleatoire, crash-teste + reboot |
| 12 | Secret admin visible /proc | Assumee | Solo-root : acces root couvre deja Porte 11 |
| 13 | Soustraction d'agregats | Assumee, meme reserve que Porte 4 | Attenuee par publication unique PAR CONSULTATION |
| 14 | Non-persistance de l'etat | Fermee | SQLite WAL, teste crash process ET reboot complet |
| 15 | Trafic HTTP en clair | Fermee | HTTPS Nginx + Let's Encrypt, redirection 301 |
| 16 | Retention logs applicatifs | Incomplete au 09/07, completee 31/07 | Volet retention fait ; volet fuite manquant -- voir Porte 26 |
| 17 | Correlation temporelle horodatage_unix | Fermee (durcie 23/07) | horodatage retire, table en WITHOUT ROWID |
| 18 | Generation de cles RSA a la volee | Fermee (22/07) | Endpoints publics en lecture seule, creation reservee au flux RH |
| 19 | Uvicorn expose hors TLS | Fermee (22/07) | --host 127.0.0.1, Nginx seul chemin d'acces |
| 20 | GET /api/rh/resultats mutant | Fermee (31/07) | Lecture pure ; publication deplacee vers POST /api/rh/publier |
| 21 | Bourrage P-A sature | Fermee (31/07) | LONGUEUR_CIBLE_FIXE 96 -> 200 |
| 22 | Absence de rate-limit routes de vote | Fermee (31/07) | Nginx limit_req 5r/s + rafale 50 |
| 23 | Absence d'en-tetes de securite HTTP | Fermee (31/07) | CSP, HSTS, X-Frame-Options, Referrer-Policy |
| 24 | Vote accepte puis efface pendant cloture | Fermee (31/07) | Publication et effacement dans le meme verrou |
| 25 | Secrets exposes en clair | Fermee (31/07) | 3 secrets rotes, rotation VERA_DB_KEY validee de bout en bout |
| 26 | Log uvicorn journalisant l'IP reelle | Fermee (31/07) | --no-access-log, log vide apres trafic verifie |

Resume : 22 portes fermees avec preuve empirique, 3 limites assumees avec
justification (5, 6, 12), 1 limite structurelle documentee et non
corrigeable (4/13 -- composition inter-consultations).

---

## 6. Infrastructure et operations

| Aspect | Etat |
|---|---|
| DNS | DuckDNS (service tiers gratuit) -- dependance non redondee |
| Certificat TLS | Let's Encrypt, renouvellement automatique Certbot |
| Supervision | systemd Restart=on-failure, teste kill -9 et reboot complet |
| Logs | IP source + chemin + code retour, uniquement sur routes non sensibles. Purge manuelle a cloture + logrotate 3 jours |
| Base SQLite | Seule la cle RSA est chiffree (Fernet). Budget epsilon, compteurs, effectifs en clair -- limite assumee, attenuee par l'absence de toute identite en base |
| Backup | Aucun backup automatique en continu. Backups ponctuels avant chaque operation a risque |
| Comptes RH | EN MEMOIRE UNIQUEMENT, recrees au demarrage depuis les variables d'environnement. Redemarrage invalide les sessions -- limite UX assumee |
| Compte execution | root (serveur dedie solo) |
| Depot public | Verifie synchrone avec la production a chaque deploiement depuis le 30/07/2026 (avant cette date, ecart corrige) |
| Scalabilite | 1 worker uvicorn, ~45 req/s stable. Generation de jetons en lot (31/07) : gain x167 mesure sur 1000 jetons |

---

## 7. Export et distribution des invitations

Depuis le 30/07/2026, le tableau de bord RH propose un export CSV du lot de
liens generes (colonnes : departement, lien, message), pour permettre l'envoi
en masse via l'outil d'envoi propre a l'organisation.

**Decision de conception justifiee :** VERA n'envoie jamais de SMS lui-meme.

1. Anonymat -- VERA ne voit et ne stocke jamais un numero de telephone. Le
   CSV ne contient aucun numero.
2. Delivrabilite -- un envoi en masse depuis un serveur unique, pour de
   multiples organisations, cumule les signaux de spam.
3. Responsabilite legale -- le demarchage par SMS est encadre ; la
   responsabilite reste chez l'organisation.

Le fichier est genere cote client, sans stockage ni log supplementaire cote
serveur. Il contient les liens de vote et doit etre traite comme confidentiel.

---

## 8. Limites explicitement hors-perimetre

- L1 Observateur reseau (IP, timing en transit) -- delegue VPN/Tor
- L2 Coercition physique ou sociale
- L3 Groupes sous K_MIN=240 -- REFUS de publier
- L4 Qualification juridique CNIL/DPO -- avis externe requis
- L5 Operateur activement malveillant qui s'heberge lui-meme (section 9)

---

## 9. Modele d'adversaire explicite

**Niveau 1 -- Tiers et operateur honnete-mais-curieux (garantie forte,
prouvee).** VERA garantit qu'aucune reponse ne peut etre reliee a une
personne. Garantie structurelle : le serveur ne stocke jamais le lien
identite<->vote. Les registres sont disjoints, la reponse n'existe que dans
un compteur agrege.

**Niveau 2 -- Operateur activement malveillant (hors garantie sans
hebergement tiers).** Un operateur qui controle toute la chaine peut
contourner la cryptographie sans la casser. Pour un anonymat tenant face a
l'organisation elle-meme, VERA doit etre heberge par un tiers de confiance.

**Compteurs bruts lisibles en base (limite de Niveau 1, documentee).** Les
tables compteurs_votes et effectifs sont en clair. K_MIN protege le RESULTAT
PUBLIE, pas la lecture directe de la base. Ce que cette lecture donne : le
QUOI et l'ORDRE. Ce qu'elle ne donne pas : le QUI, ni une ancre temporelle
externe (canaux fermes : Porte 26, fragment d'URL, horodatage retire).

**Integrite du scrutin -- ce que VERA NE garantit PAS.** La limite la plus
importante de ce document. VERA prouve l'anonymat, pas que le resultat
publie reflete un vrai scrutin : aucune liste de reference des personnes
invitees, un organisateur pourrait generer 240 jetons et voter 240 fois
lui-meme, aucun recu votant ni urne publique. Choix impose, pas un defaut :
la verifiabilite de bout en bout exige un decompte EXACT ; VERA publie un
decompte BRUITE, c'est toute la garantie DP. Detail : LIMITS.md section 13.

**Composition inter-consultations -- limite structurelle non corrigeable.**
Le budget epsilon est remis a zero a chaque cloture. Suivre l'exposition
d'un individu supposerait de l'identifier. Regle d'usage : 4 consultations
par 12 mois glissants max sur la meme population. Detail : LIMITS.md section 14.

---

## 10. Ce que ce document ne prouve pas

- Que le code est exempt de bugs non identifies
- Que les limites assumees sont negligeables dans tous les contextes
- Que la qualification CNIL est acquise
- Que le service tiers DuckDNS est fiable a 100%
- Qu'un expert humain en cryptographie ne trouverait rien de nouveau
- Que l'integrite du scrutin est garantie -- seul l'anonymat l'est

---

## Annexe -- Corrections methodologiques anterieures (14/07/2026)

**K_MIN etait une constante morte.** Definie a 100 mais jamais utilisee dans
le chemin de publication. Corrige : refus explicite sous le seuil, K_MIN
releve a 240 (mesure).

**La promesse de precision etait fausse.** Erreur annoncee +/-5% a n>=100 ;
mesure reelle : n=100 -> 12%, n=150 -> 8%, n=200 -> 6%, n=240 -> 5%.

**La preuve de sensibilite etait fausse.** Justifiee par composition
parallele, incompatible avec Delta=2 sous substitution. Corrigee : Laplace
vectoriel sur R^3.

**Projection sur le simplexe.** Post-traitement (Hay et al. 2010) : gratuit
en epsilon, erreur reduite d'environ 25%. Verifie en production (250
votants) : verite 130/80/40 -> publie 123/84/43, somme exacte 250.

---

## Methode de tenue de ce document

Chaque statut n'est marque "ferme" que s'il a ete teste directement sur le
serveur de production, avec preuve reproductible datee. Une porte fermee
peut etre rouverte par une fonctionnalite ou une porte d'infrastructure
ulterieure (cf. Porte 4, rouverte par la Porte 24 sans detection pendant 14
jours) -- les hypotheses des portes fermees doivent etre re-verifiees a
chaque changement touchant les memes mecanismes. Ce document est tenu dans
le depot de code et pousse avec lui, pour eviter la divergence qui a
motive cette version 2.0.
