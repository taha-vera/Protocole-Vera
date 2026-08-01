# Ameliorations futures

**Derniere revision : 01/08/2026.** Ce document a ete integralement revu a cette
date : la majeure partie de son contenu decrivait un etat du projet anterieur au
23/07 et annoncait comme « a faire » des chantiers depuis acheves. Ce qui reste
ouvert est en tete ; ce qui a ete fait est conserve en fin de document, en
historique, parce qu'un projet qui efface ses chantiers passes rend son propre
modele de menace illisible.

Rien de ce qui suit ne menace la production. Ce sont des renforcements de tests
et deux points de conception a specifier.

---

## Ouvert -- tests a ajouter

**Anti-rejeu persistant -- priorite haute.** `test_persistance.py` ne teste pas
`persister_token_consomme` / `charger_tokens_consommes`. C'est pourtant le
scenario cle de la Porte 14 : apres un redemarrage, un token deja consomme ne
doit pas pouvoir etre rejoue. Ajouter un test unitaire (persister une empreinte,
recharger, verifier sa presence) puis un test d'integration sur base temporaire
qui consomme un token, detruit l'instance du gestionnaire, en recree une, et
verifie que le rejeu est refuse.

**Chiffrement au repos.** Aucun test ne verifie ce qui est reellement lisible
dans le fichier `.db`. Test simple : lire les octets bruts et verifier ce qui
apparait en clair. NB : par conception, seule la cle RSA est chiffree -- les
compteurs agreges sont en clair, c'est une limite documentee (voir
`VERA_AUDIT_REFERENCE.md` section 9). Le test doit donc verifier ce qui est
attendu, pas supposer que tout est chiffre. Verifier aussi qu'apres
`effacer_etat_consultation()` les lignes supprimees ne subsistent pas dans les
pages liberees ou le WAL (`secure_delete` + `VACUUM`).

**Mauvaise cle de dechiffrement.** Le fail-closed est implemente (lot 11,
01/08) et verifie manuellement sur 7 cles reelles, mais aucun test automatise ne
le couvre. Ajouter : persister une cle, changer `VERA_DB_KEY`, verifier que
`charger_toutes_cles_chiffrees` leve bien plutot que de renvoyer un dict vide.

**Tests de concurrence.** Aucun test d'acces simultane, alors que le code est
verrouille partout. Deux cas prioritaires : `verifier_et_consommer` appele par
deux threads sur le meme token (double vote possible en theorie, fortement
attenue par le worker unique impose), et `persister_publication_atomique`
interrompu entre deux ecritures.

**Aucun test n'exerce la couche HTTP cote Python.** Constat d'audit externe du
01/08 : les invariants d'API les plus sensibles ne sont couverts par aucune
non-regression Python. En particulier, **rien n'assert que `GET
/api/rh/resultats` laisse `nombre_publications` inchange** -- alors que c'est le
correctif le plus critique de la semaine (Porte 20). Recommandation : un test
`TestClient` avec un stub `vera_blind_sig`, verifiant le budget avant/apres le
GET, plus un test que la publication en GET renvoie 405. NB : les tests HTTP
existent en JavaScript dans `chantier_crypto/` (7 fichiers `.mjs`) ; le trou est
cote Python.

**Raffinements `test_precision_kmin`.** Verifier d'abord si `np.random.seed` a
un effet reel (le RNG d'OpenDP n'est probablement pas seedable). Puis resserrer
les tolerances : calculer l'erreur-type Monte-Carlo par bootstrap sur les 3000
erreurs et fixer `tol = max(3*SE, 0.25)` au lieu du forfait +/-0.8, pour
detecter une derive fine et pas seulement une catastrophe. Monter N_SIM a 10000,
ajouter un test de biais (moyenne des erreurs ~ 0) et de forme (KS ou chi2).

**Isolation de test plus robuste.** Remplacer le patch de `builtins.import` dans
`test_signature_production` par une variable d'environnement lue par le module
(`VERA_SANS_PERSISTANCE=1`) -- plus propre sous pytest.

---

## Ouvert -- points de conception a specifier

**Anti-rejeu des jetons dependant de la cloture.** La protection anti-rejeu des
jetons d'autorisation repose sur le fait que la cloture a lieu :
`effacer_etat_consultation()` vide la table. Un jeton NON consomme, entre deux
consultations sans cloture explicite (redemarrage, reouverture), resterait
valide. Comportement a specifier explicitement, puis tester.

**Cycle de vie de la cle apres destruction de la partie privee.** Apres
expiration et `_detruire_cle_privee()`, la cle publique reste en memoire.
`verifier_et_consommer` peut-il encore accepter des tokens ? Comportement a
specifier, puis tester.

**Clamp DP a `BOUNDS = (0, 10000)`.** Constat d'audit externe du 01/08 :
`appliquer_bruit_dp` borne chaque compteur a 10 000 avant bruitage. Le clamp ne
casse pas la garantie DP (c'est un pre-traitement qui reduit la sensibilite),
mais si une option depassait 10 000 votes, le resultat publie serait fausse par
troncature. Peu probable a l'echelle visee. A documenter, ou porter la borne
au-dela du plus grand effectif realiste.

**Angles morts d'audit declares.** L'auditeur externe du 01/08 a signale n'avoir
lu ni `static/blindrsa-bundle.js` (le pendant CLIENT de la crypto, present dans
le depot et donc auditable) ni les tests `.mjs` de `chantier_crypto/`. Ce sont
les deux zones a faire regarder en priorite au prochain audit.

**Lien mort dans le README.** Le README renvoie vers `archive/test_porte7.py`,
or `archive/` a ete retire du suivi git le 01/08. Corriger la reference.

---

## Historique -- chantiers acheves

Conserves pour que le modele de menace reste lisible : savoir QUAND une garantie
a ete obtenue importe autant que de savoir qu'elle existe.

**Chantier crypto -- unlinkability du votant. ACHEVE (refactor Modele B, 23/07).**
Le probleme identifie le 18/07 etait reel et grave : `generer_token_signe()`
executait les trois etapes (aveugler, signer, finaliser) cote serveur, le client
ne faisait aucune crypto. Le serveur produisait donc le token complet et
connaissait l'empreinte qui serait consommee -- il pouvait relier identite et
acte de vote. La signature aveugle ne produisait aucune unlinkability.
Aujourd'hui : l'aveuglement et la finalisation ont lieu dans le navigateur
(`static/vote.html`, `@cloudflare/blindrsa-ts` auto-hebergee, meme variante
RFC 9474 que la lib Rust serveur). `generer_token_signe` n'a plus aucun
appelant. Le serveur n'execute que `generer_cles`, `signer_aveugle` et
`verifier_signature`.

**Exigence 1 -- engagement de cle publique. ACHEVE.** L'attaque visee (un
serveur signant chaque votant avec une cle differente, puis testant au
depouillement quelle cle valide quel token) est fermee : l'empreinte de la cle
voyage dans le fragment `#k=` du lien, jamais transmise au serveur, et le client
verifie sa signature contre cette empreinte engagee. Durci le 01/08 en
fail-closed : si le fragment est absent, le vote est refuse au lieu de sauter
silencieusement la verification.

**Exigence 2 -- ensemble d'anonymat. ACHEVE (documentation).** L'unlinkability
ne vaut que parmi ceux qui ont effectivement echange leur jeton. Documente ; le
depouillement n'a lieu qu'apres cloture et sous K_MIN = 240.

**Exigence 3 -- correlation par metadonnees reseau. ACHEVE, au-dela du prevu.**
Prevu comme « a documenter, pas a resoudre ». En pratique le canal a ete FERME
le 01/08 : le log applicatif uvicorn journalisait l'IP reelle des votants sur
les routes de vote malgre `access_log off` cote Nginx (52 lignes relevees en
production, dont 4 sur `GET /vote`). Corrige par `--no-access-log`.

**Decision distribution -- Option B. ACHEVE.** Le RH envoie les SMS lui-meme,
VERA ne voit jamais un numero. Complete le 30/07 par un export CSV du lot de
liens, genere cote client, sans numero de telephone, pour permettre l'envoi en
masse via l'outil de l'organisation.

**Code HTTP 422 sur message aveugle invalide. ACHEVE.**

**Effacement de `jetons_autorisation` a la cloture. ACHEVE**, avec
`test_effacement_jetons.py`.

**Budget epsilon : refus des couts <= 0. ACHEVE.**

**Fail-closed sur le dechiffrement des cles RSA. ACHEVE (lot 11, 01/08).** Un
echec de dechiffrement etait avale par un `continue` silencieux : une
`VERA_DB_KEY` erronee faisait regenerer des cles et invalidait tous les liens
deja distribues, sans aucun signal. Le service refuse desormais de demarrer,
avec diagnostic nominatif par departement.

**Remote git en token-dans-URL. ACHEVE.** Migre en SSH.

**Obstacle sjcl -- leve le 18/07.** `@cloudflare/blindrsa-ts` n'utilise `sjcl`
que pour l'arithmetique grands nombres ; aucun appel a `sjcl.ecc` sur le chemin
RSABSSA. La faille GHSA-2w8x-224x-785m (validation de point sur courbe
elliptique) est donc hors perimetre pour cet usage RSA.

**Deux invariants a ne jamais perdre**, rappeles ici parce qu'ils ne sont
garantis par aucun test :

- **Deux registres separes, jamais joints** : le jeton d'autorisation (Temps 1)
  et l'empreinte du token de vote depense (Temps 2) sont deux tables distinctes.
  Les joindre recreerait la liaison identite <-> vote.
- **Un jeton d'autorisation = une epoque = une signature** (parade
  differenciation, Porte 7).
