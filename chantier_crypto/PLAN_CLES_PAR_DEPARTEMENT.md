# Plan : refactor Modele B + cles par departement

> ## ⚠️ DOCUMENT DE TRAVAIL PERIME — NE PAS S'EN SERVIR COMME REFERENCE
>
> Notes de chantier du **20/07/2026**, pendant le refactor Modele B. Le refactor
> est termine depuis le 23/07 : ce document decrit un etat intermediaire.
>
> Il se presente par endroits comme une reference (« Reference qui marche : … »)
> et renvoie a des fichiers qui **n'existent plus** -- `brique5_test_client.mjs`,
> `test_bundle.html`, `test_couche2.py`, `test_couche3.py`, `test_api_c4.py`.
> Un auditeur externe l'a releve le 28/08/2026 : dans un depot dont l'argument
> central est que la documentation ne ment pas, un document de travail versionne
> qui se donne pour une reference est un defaut, meme sans consequence
> technique.
>
> **Ce qui fait foi :** `VERA_THREAT_MODEL_COMPLETE.md` pour le modele de
> menace, `LIMITS.md` pour les limites, le code pour les parametres. Ce fichier
> n'est conserve que comme trace du chantier.


## ETAT AU 20/07 (matinee) -- 4 COUCHES SERVEUR FINIES, REPRENDRE AUX BRIQUES CLIENT

Les 4 couches SERVEUR du Modele B multi-departement sont faites, testees sur
base/instance isolee, commitees (jusqu-a 6803087). NON deployees (prod sur
ancien Modele A stable).
- Couche 1 schema + migration auto (ab4788e/b550fb5)
- Couche 2 persistance chiffree par departement (b550fb5)
- Couche 3 gestionnaire dict de cles, generation a la volee, destruction
  groupee (54e2c45), test_couche3.py OK
- Couche 4 API 3 endpoints routent par departement, ancien monde en 410
  (6803087), test_api_c4.py OK

MARCHE cote serveur : cle par departement a la volee ; empreinte de la BONNE
cle dans le lien SMS ; signer_aveugle signe avec la cle du departement issu du
JETON (porte "departement auto-declare" de Fable 5 FERMEE) ;
/api/cle_publique?departement=X ; ancien Modele A (generer_tokens, repondre) en 410.

DECISION CHEMIN 2 : Modele B pur, plus de vote fonctionnel jusqu-a la fin,
portage prod en UNE fois a la toute fin.

RESTE A FAIRE (briques CLIENT) :
- Brique 5b : crypto client dans static/vote.html. Lire ?a=JETON#k=EMPREINTE,
  generer K (128 bits), aveugler K, POST signer_aveugle, finaliser -> (K, sig(K)).
  Reference qui marche : chantier_crypto/brique5_test_client.mjs (adapter :
  signer K opaque ; cle via /api/cle_publique?departement=X ; le departement
  vient de la reponse de signer_aveugle).
- Brique 6 : verif empreinte cle client. Comparer empreinte cle recue au #k= du
  lien (fragment jamais envoye au serveur). Different -> refuser.
- Brique 7 : reecrire /api/repondre Modele B. Recoit (K, sig(K), reponse). UNE
  SEULE TRANSACTION SQLite (bug double-commit a NE PAS recreer) : verifier
  sig(K) sous cle publique du departement -> H(K) absent registre 2 (dedup
  SHA-384(K)) -> reponse valide -> _incrementer_compteur + inserer H(K).
  Invalide -> 400, jeton survit. + cache idempotence sur signer_aveugle.
- Brique 8 : test bout-en-bout client<->serveur + BASCULE prod.

NETTOYAGE en attente (cosmetique) : code mort apres raise 410 dans
generer_tokens et repondre. Fichiers test_*.py du bac a sable a ranger.

RAPPELS : bac a sable /root/vera_test, base isolee VERA_DB_PATH ; lancer avec
VERA_DB_KEY + venv /root/vera_blind_sig/.venv/bin/python3 ; node dans
/root/crypto_test ; mobile = petits blocs avec LIGNE REPERE, git SANS apostrophes.

## (archive) ETAT AU 20/07 (soir) -- REPRENDRE ICI
Couches 1-2 FAITES, testees sur base isolee, commitees (b550fb5) mais PAS
portees en prod (incompatibles avec gestionnaire encore mono-cle).
- Couche 1 : schema cle_rsa_active departement PRIMARY KEY + migration auto
  idempotente (_migrer_schema_cles dans initialiser()). VALIDE bout-en-bout.
- Couche 2 : persistance chiffree par departement (persister/charger_cle_rsa_
  chiffree(departement,...), charger_toutes_cles_chiffrees(), effacer_cle_rsa
  efface tout). Vestiges morts supprimes. Test test_couche2.py OK.
- DB_PATH configurable via VERA_DB_PATH (isolation bac a sable posee, ne PAS
  perdre : sans ca un DROP de test toucherait la base de prod).
PROCHAINE ETAPE = COUCHE 3 : le gestionnaire (vera_signature_manager.py).
  self._cle_privee_der scalaire -> dict {departement: (priv,pub)}. Generation
  a la volee (1ere demande d'un departement). UN timer de destruction groupee
  a ouverture+DUREE_VIE (decision actee). Rechargement au boot via
  charger_toutes_cles_chiffrees(). ATTENTION : etat memoire + threads + timer,
  concentration requise, faire en session fraiche.
Rappel test : lancer avec VERA_DB_KEY (depuis systemd) + VERA_DB_PATH isole +
  /root/vera_blind_sig/.venv/bin/python3. Bac a sable = /root/vera_test.
Rappel mobile : heredocs cassent, PREFERER fichiers .py + python3 fichier.py.


## Contexte
Suite du refactor crypto d'unlinkability. Le tour multi-IA (Copilot, ChatGPT,
Gemini, Mistral, Fable 5) a tranche DEUX decisions structurantes qui rendent
caduque une partie des briques 5-8 initialement prevues.

## Decision 1 : MODELE B (jeton de vote opaque), pas Modele A
3 IA disaient A, Fable 5 disait B. Verdict le plus dur retenu.
Raison decisive (Fable 5) : en Modele A, le votant finit avec (M, signature) ou
M contient sa reponse EN CLAIR + signature verifiable par tous = RECU DE VOTE
transferable. Un RH coercitif peut exiger "montre ton bulletin signe oui".
Le Modele A FABRIQUE l'outil de coercition. Adversaire n1 de VERA = le RH => B.

Flux Modele B :
- Temps 1 (fait, briques 1-4) : RH distribue jetons d'autorisation par SMS.
- Temps 2 (emargement) : client genere un secret K aleatoire (128 bits),
  l'aveugle, presente (jeton_autorisation, K_aveugle). Serveur consomme le
  jeton (registre 1, atomique), signe K_aveugle AVEC LA CLE DU DEPARTEMENT,
  renvoie la signature aveugle. Client finalise -> detient (K, signature(K)).
  K ne dit RIEN du vote.
- Temps 3 (vote) : client envoie (K, signature(K), reponse) sur /api/repondre.
  Serveur, EN UNE SEULE TRANSACTION : verifie signature(K) sous la cle publique
  du departement -> verifie H(K) absent du registre 2 -> valide reponse dans la
  liste autorisee -> enregistre (reponse, departement) + insere H(K) registre 2
  -> UN SEUL COMMIT. Reponse invalide -> 400, jeton de vote survit, retry OK.

## Decision 2 : UNE PAIRE DE CLES PAR DEPARTEMENT (trouvaille du tour)
Ferme la porte "departement auto-declare" (Fable 5) : si le departement etait
un champ ecrit par le votant, il serait usurpable (pollution de cohortes,
manip K_MIN, reouverture partielle Porte 7 differencing). Solution : le
departement n'est PAS dans le message ; il est PROUVE PAR LA CLE. Le serveur
signe avec la cle du departement porte par le jeton d'autorisation (registre 1,
que le serveur controle). Au comptage, la signature ne verifie que sous la
bonne cle publique => appartenance prouvee sans identite.
Cout en anonymat : l'ensemble d'anonymat = le departement. C'est deja la
granularite de cohorte et de K_MIN => AUCUN recul reel.

## Decision 3 : departements CREES AU FIL DE L'EAU (tranche ce jour)
Pas de declaration a l'ouverture. Le champ departement de generer_autorisations
est deja un texte libre (brique 4). La cle d'un departement est creee la
PREMIERE FOIS que le RH genere des autorisations pour ce departement (dans la
brique 4), puis reutilisee. A trancher a froid : destruction groupee a
ouverture+DUREE_VIE (probable, plus simple) vs duree de vie par cle.

## Les 4 obligations de Fable 5 (Modele B)
1. Cle dediee par consultation ET par departement (jamais partagee ailleurs).
2. Deduplication registre 2 sur H(K) [= H(M) en modele B, K est le message].
   PAS H(signature) : RSA-PSS Randomized est probabiliste, plusieurs signatures
   valides pour un meme K.
3. Cache d'idempotence sur la phase de signature : jeton -> (K_aveugle,
   signature_aveugle) pour permettre retry si crash/reseau apres consommation
   du jeton (sinon electeur brule son jeton sans recevoir sa signature).
   SUR pour l'unlinkability : le serveur ne connait pas le facteur
   d'aveuglement r, ne peut relier signature_aveugle a signature finale.
4. Depense du jeton de vote + enregistrement reponse = UNE SEULE TRANSACTION
   SQLite, UN commit. (= bug historique du double-commit non-atomique. Zone de
   blessure connue. A ne PAS recreer.)

## Invariant reformule (Fable 5)
Ancien : "aucun lien jeton<->signature stocke".
Nouveau : "aucun lien jeton<->signature FINALE". Le lien vers la forme
aveuglee (cache d'idempotence) est inoffensif ET necessaire.

## Les 4 couches a modifier (chantier structurel)
Etat actuel = MONO-CLE par construction :
- Table SQLite cle_rsa_active : PRIMARY KEY fixe id=1 (une seule ligne).
- charger_cle_rsa_chiffree : WHERE id=1.
- ouvrir_consultation : une paire generee, UN timer de destruction.
- gestionnaire : self._cle_privee_der scalaire (pas un dict).

A refactorer :
1. Schema SQLite : cle_rsa_active -> multi-lignes, PRIMARY KEY = departement.
2. Persistance : persister/charger par departement (+ charger_tous au boot).
3. Gestionnaire : dict {departement: (priv, pub, ts)}, generation a la volee,
   destruction de N cles, gestion timer(s).
4. Briques 2/3/4 : signer_aveugle route selon departement du jeton ;
   cle_publique?departement=X expose la bonne cle ; generer_autorisations cree
   la cle du departement si absente.

ATTENTION : couche la plus sensible du systeme (cle privee, VERA_DB_KEY, Fernet,
destruction memoire). Erreur silencieuse possible : cle non detruite, mal
chiffree, ou rechargee pour le mauvais departement. A faire en session FRAICHE.

## Etat des briques (a jour)
Fait et en prod : brique 1 (registre autorisation), 2 (signer_aveugle),
3 (cle_publique), 4 (generer_autorisations), 5 preuve logique client HTTP.
MAIS 2/3/4 sont MONO-CLE => a adapter au multi-departement.
Caduc / a refaire pour Modele B : brique 5b (client fait signer K opaque, pas
le bulletin), 6 (verif empreinte cle), 7 (/api/repondre transactionnel),
8 (bascule).

## Question ouverte pour la prochaine session
- Destruction des cles : groupee (ouverture+DUREE_VIE) ou par cle ? (probable: groupee)
- Un timer global ou N timers ? (probable: un balayage groupe)
- La brique 5 preuve (brique5_test_client.mjs) doit etre refaite version B :
  faire signer K opaque, recuperer cle du departement via /api/cle_publique?departement=X.

## Session 22/07 -- socle crypto client VALIDE
- Fix jetons_autorisation: teste (test_effacement_jetons.py OK) et committe.
- Migration git vers SSH faite (plus de token dans URL). Token GitHub supprime.
- Brique 5b SOCLE: lib @cloudflare/blindrsa-ts bundlee via esbuild ->
  static/blindrsa-bundle.js (86ko, auto-hebergee, zero dependance externe).
  PROUVEE dans navigateur HTTPS (test_bundle.html autonome): window.RSABSSA
  charge, aveuglement 256 octets OK. Bundle dans /root/static/ (prod) mais PAS
  encore dans git ni versionne -> a committer avec la brique 5b complete.
  Le bundle a ete genere depuis /root/crypto_test (esbuild + entree_bundle.js).

## RESTE brique 5b (le vrai flux dans vote.html)
Ecrire dans static/vote.html: charger blindrsa-bundle.js, lire ?a=JETON et
#k=EMPREINTE, generer K, aveugler K, POST /api/signer_aveugle, finaliser.
Reference: chantier_crypto/brique5_test_client.mjs (attention: Buffer=Node,
remplacer par toHex/fromHex navigateur comme dans test_bundle.html).

## POINT DE SEQUENCEMENT A TRANCHER (important)
Pour TESTER le flux vote.html complet, il faut un serveur avec la COUCHE 4
(endpoints Modele B: /api/cle_publique?departement=X, /api/signer_aveugle qui
route par jeton). Or la PROD tourne encore l'ANCIENNE version (refactor pas
deploye, chemin 2 acte). Donc: soit lancer une instance de test avec couche 4
(mais WebCrypto exige HTTPS, pas trivial sur instance http), soit basculer la
couche 4 en prod. A trancher a froid avant d'ecrire vote.html.
