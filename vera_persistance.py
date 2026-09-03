#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_persistance.py - Persistance SQLite Porte 14."""

import sqlite3
import os
import threading
import time
import hashlib
from pathlib import Path

DB_PATH = Path(os.environ.get("VERA_DB_PATH", "/root/vera_state.db"))

# GARDE-FOU : un test ne doit JAMAIS toucher la base de production. Le chemin
# par defaut est ABSOLU (/root/vera_state.db) ; sans ce garde, tout script de
# test lance sans VERA_DB_PATH ecrit dans la vraie base -- et certains appellent
# effacer_etat_consultation(), qui vide sept tables puis VACUUM. Une
# consultation en cours serait detruite par une simple distraction. Constat du
# 25/07 : AUCUN des quinze tests Python ne definissait VERA_DB_PATH.
import sys as _sys
_script = Path(_sys.argv[0]).name if _sys.argv else ""
if _script.startswith("test_") and "VERA_DB_PATH" not in os.environ:
    raise RuntimeError(
        "REFUS : " + _script + " tente d'utiliser la base de PRODUCTION ("
        + str(DB_PATH) + "). Un test doit definir VERA_DB_PATH vers une base "
        "jetable. Exemple : VERA_DB_PATH=/tmp/test.db python3 " + _script
    )
_verrou_db = threading.Lock()
_conn = None

# --- Historique : la troncature periodique du WAL ---
#
# Ce module a longtemps tourne en journal_mode=WAL avec une troncature tous
# les 20 votes. Le motif : en WAL, chaque validation ecrit l'image des pages
# modifiees dans un journal qui survit entre les transactions, et deux images
# successives d'une meme page se different octet a octet. On y lisait donc
# l'ordre des votes que la table, elle, ne conserve pas.
#
# La troncature bornait la fenetre a 20 votes sans la fermer. Un audit du
# 13/08 a montre que ces 20 votes n'etaient pas seulement ordonnes mais
# NOMINATIFS : la consommation d'un jeton -- qui porte l'empreinte du jeton,
# donc l'identite via la liste de l'organisation -- s'ecrivait dans le meme
# journal que l'increment du compteur de reponses, a quelques millisecondes
# d'intervalle. Les deux registres que le protocole tient disjoints etaient
# joints au niveau du stockage.
#
# D'ou le passage a journal_mode=DELETE (voir _connexion) : aucun journal ne
# persiste entre deux transactions, pour aucune table. La troncature n'a plus
# d'objet et a ete retiree.


_SQL_TABLES = [
    "CREATE TABLE IF NOT EXISTS budget_epsilon (departement TEXT PRIMARY KEY, epsilon_consomme REAL NOT NULL DEFAULT 0.0, nb_publications INTEGER NOT NULL DEFAULT 0)",
    # P-B : PAS d'horodatage ici. Un instant de consommation stocke a cote de
    # l'empreinte permettait, en lisant la base apres coup, de dater chaque vote
    # et de le recouper avec toute autre source temporelle (logs, envoi des
    # liens). Le champ n'etait jamais lu par le code : purement descriptif, mais
    # exploitable par un adversaire. La table ne retient que ce qui est
    # STRICTEMENT necessaire a l'anti-rejeu : l'empreinte.
    # WITHOUT ROWID : sans ce mot-cle, SQLite attribue un rowid implicite et la
    # table conserve l'ORDRE D'INSERTION des votes, lisible par SELECT rowid.
    # Retirer l'horodatage supprimait les instants, pas la sequence. En
    # WITHOUT ROWID la table est un B-tree ordonne par l'empreinte (SHA-384,
    # pseudo-aleatoire) : l'ordre des votes disparait a la racine au lieu de
    # dependre du maintien d'une hypothese d'environnement (aucun log, aucun
    # horodatage ailleurs). Lecon de la Porte 19 : une porte fermee peut etre
    # rouverte par une porte d'infrastructure ulterieure.
    "CREATE TABLE IF NOT EXISTS tokens_consommes (empreinte TEXT PRIMARY KEY) WITHOUT ROWID",
    "CREATE TABLE IF NOT EXISTS compteurs_votes (departement TEXT NOT NULL, reponse TEXT NOT NULL, compte INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (departement, reponse))",
    "CREATE TABLE IF NOT EXISTS effectifs (departement TEXT PRIMARY KEY, effectif INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS resultats_publies (departement TEXT PRIMARY KEY, resultat_json TEXT NOT NULL)",
    # Intitule de la question, fige a l'ouverture de la consultation.
    # Une seule ligne (id=1). Les OPTIONS ne sont pas stockees : elles restent
    # a trois (oui/non/abstention) car toute la calibration DP en depend --
    # DELTA_INT=2 et K_MIN=240 ont ete mesures sur trois options.
    # PRIMARY KEY (groupe, close_unix), et ce qu'elle couvre EXACTEMENT.
    #
    # Un audit externe du 03/09/2026 a signale l'absence de contrainte : une
    # cloture rejouee inserait des doublons, et compter_consultations_recentes
    # surestimait -- or ce compteur alimente l'avertissement de frequence, et un
    # avertissement qui se declenche a tort finit ignore.
    #
    # Le scenario decrit -- double clic, reprise HTTP -- est deja ferme
    # AILLEURS, et mieux : cloturer_consultation constate l'etat vide au second
    # appel (les jetons et effectifs ont ete effacés) et sort en
    # « rien_a_cloturer » sans rien reenregistrer. Verifie.
    #
    # Cette contrainte couvre le cas etroit qui restait : deux appels
    # CONCURRENTS franchissant la garde ensemble, donc avec le meme horodatage.
    # Elle ne remplace pas l'idempotence de l'appelant, elle la complete.
    "CREATE TABLE IF NOT EXISTS historique_consultations (groupe TEXT NOT NULL, close_unix REAL NOT NULL, PRIMARY KEY (groupe, close_unix))",
    "CREATE TABLE IF NOT EXISTS question_active (id INTEGER PRIMARY KEY CHECK (id = 1), intitule TEXT NOT NULL, ouverture_depots_unix REAL, groupes_declares TEXT)",
    "CREATE TABLE IF NOT EXISTS jetons_autorisation (jeton TEXT PRIMARY KEY, departement TEXT NOT NULL, utilise INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS cle_rsa_active (departement TEXT PRIMARY KEY, cle_privee_hex TEXT NOT NULL, cle_publique_hex TEXT NOT NULL, ouverture_unix REAL NOT NULL, salt_hex TEXT)",
]


def _connexion():
    # TIMEOUT EXPLICITE, et non celui de la distribution.
    #
    # Sans ce parametre, SQLite prend la valeur par defaut du binding -- 5
    # secondes le plus souvent, mais rien ne le garantit d'une distribution a
    # l'autre. Si un processus externe pose un verrou sur le fichier (sauvegarde,
    # `sqlite3` en ligne de commande, agent de supervision), une transaction
    # echoue en OperationalError, et ce module n'a aucun mecanisme de reprise :
    # le vote est perdu.
    #
    # Trente secondes couvrent largement une sauvegarde, et restent tres en deca
    # du delai au bout duquel un votant abandonnerait. Constat d'un audit externe
    # du 03/09/2026 : la valeur ne doit pas dependre de l'environnement.
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    # journal_mode=DELETE et non WAL, deliberement.
    #
    # LE PROBLEME QUE CELA FERME
    # En WAL, chaque validation ecrit dans un fichier journal l'image complete
    # des pages modifiees. Ce journal survit entre les transactions, et deux
    # images successives d'une meme page se different octet a octet.
    #
    # Consequence mesuree : la consommation d'un jeton (registre 1, qui porte
    # l'empreinte du jeton, donc l'identite via la liste de l'organisation) et
    # l'increment du compteur de reponses (registre 2) s'ecrivaient dans le
    # MEME journal, a quelques millisecondes d'intervalle. Un lecteur du seul
    # fichier journal reconstituait la suite
    #
    #     jeton d'ALICE consomme  ->  compteur "oui" +1
    #     jeton de BOB consomme   ->  compteur "non" +1
    #
    # Les deux registres que tout le protocole existe pour tenir disjoints
    # etaient joints au niveau du stockage. Une lecture unique suffisait --
    # instantane d'hebergeur, sauvegarde, agent de supervision lisant /root.
    #
    # POURQUOI DELETE PLUTOT QU'UNE SECONDE BASE
    # Attacher une base separee pour les jetons aurait ferme CETTE instance du
    # canal. DELETE ferme la classe : aucun journal ne persiste entre deux
    # transactions, pour aucune table, y compris celles qu'on n'a pas encore
    # identifiees. C'est la lecon d'un correctif precedent, qui avait sorti du
    # WAL une table sur les deux qui portaient une empreinte de jeton.
    #
    # LE COUT, MESURE
    # 632 votes/seconde contre 1450 en WAL sur le seul chemin de persistance.
    # Le systeme complet plafonne a 42 votes/seconde (cryptographie et reseau) :
    # le journal n'est pas le goulot, et ne le devient pas.
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    # secure_delete : ecrase les octets des lignes supprimees au lieu de les
    # marquer libres. Sans lui, un DELETE (effacement de cloture, purge des
    # jetons) laisse les donnees lisibles dans les pages du fichier .db,
    # recuperables forensiquement. La promesse "apres cloture le serveur ne
    # revele plus rien" ne tient au niveau des OCTETS que si ce PRAGMA est
    # actif. Cout : ecritures un peu plus lentes, negligeable a cette echelle.
    conn.execute("PRAGMA secure_delete=ON")
    return conn


def _migrer_schema_cles(conn):
    """Migration idempotente : cle_rsa_active mono-cle (id=1) -> multi-cles
    (departement PRIMARY KEY). Detecte l'ancien schema par la presence de la
    colonne 'id' et, le cas echeant, DROP + recree. SUR : les cles RSA sont
    ephemeres (regenerees a l'ouverture de consultation), aucune donnee
    precieuse perdue. Ne fait rien si la table est absente ou deja migree."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cle_rsa_active'"
    ).fetchall()]
    if not tables:
        return  # table absente : sera creee au bon schema par _SQL_TABLES
    cols = [r[1] for r in conn.execute("PRAGMA table_info(cle_rsa_active)").fetchall()]
    if 'id' in cols:
        conn.execute("DROP TABLE cle_rsa_active")


def _migrer_schema_tokens(conn):
    """Migration idempotente : tokens_consommes (empreinte, horodatage_unix)
    -> (empreinte) seule. L'horodatage de consommation n'etait JAMAIS lu par le
    code (purement descriptif) mais permettait, en lisant la base apres coup,
    de dater chaque vote et de le recouper avec toute autre source temporelle.

    DIFFERENCE CRITIQUE avec _migrer_schema_cles : ici on ne peut PAS faire un
    DROP sec. Cette table EST l'anti-rejeu : la vider autoriserait a revoter
    avec un K deja utilise. On COPIE donc les empreintes dans la nouvelle table
    avant de supprimer l'ancienne, le tout dans une transaction (si le processus
    meurt au milieu, on ne se retrouve jamais sans table anti-rejeu).

    Idempotente : ne fait rien si la colonne horodatage_unix est deja absente.
    Sans ce garde-fou, la table serait recreee a chaque demarrage."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tokens_consommes'"
    ).fetchall()]
    if not tables:
        return  # absente : creee au bon schema par _SQL_TABLES
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tokens_consommes)").fetchall()]
    if 'horodatage_unix' not in cols:
        return  # deja migree
    conn.execute("CREATE TABLE tokens_consommes_v2 (empreinte TEXT PRIMARY KEY) WITHOUT ROWID")
    conn.execute("INSERT INTO tokens_consommes_v2 (empreinte) SELECT empreinte FROM tokens_consommes")
    conn.execute("DROP TABLE tokens_consommes")
    conn.execute("ALTER TABLE tokens_consommes_v2 RENAME TO tokens_consommes")
    conn.commit()
    # VACUUM apres le DROP : sans lui, les anciennes lignes -- horodatages
    # compris -- restent dans les pages LIBEREES du fichier .db et sont
    # recuperables forensiquement. Le DROP nettoie la vue logique, pas les
    # octets. VACUUM reecrit le fichier sans les pages mortes. Hors
    # transaction (SQLite l'exige).
    conn.execute("VACUUM")


def _migrer_jetons_vers_empreintes(conn):
    """Migration idempotente : jetons_autorisation stockait le jeton EN CLAIR.
    Un lecteur de base recuperait les jetons non consommes par un SELECT et les
    rejouait contre /api/signer_aveugle (public) : bourrage et privation de vote
    sans clé privée ni modification du logiciel. On remplace chaque jeton par
    son SHA-256, comme le registre 2 le fait deja pour K.

    Detection : un SHA-256 hexadecimal fait exactement 64 caracteres [0-9a-f].
    Les jetons generes (token_urlsafe) ne respectent pas ce format. On ne
    hache donc que les lignes qui n'y ressemblent pas -> rejouer la migration
    ne re-hache pas les empreintes (idempotence).

    Les liens SMS deja distribues continuent de fonctionner : le votant envoie
    le jeton en clair, le serveur le hache et retrouve la ligne."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='jetons_autorisation'"
    ).fetchall()]
    if not tables:
        return
    rows = conn.execute("SELECT jeton FROM jetons_autorisation").fetchall()
    a_migrer = []
    for (j,) in rows:
        deja_hache = (len(j) == 64 and all(ch in "0123456789abcdef" for ch in j))
        if not deja_hache:
            a_migrer.append(j)
    if not a_migrer:
        return
    for j in a_migrer:
        conn.execute(
            "UPDATE jetons_autorisation SET jeton = ? WHERE jeton = ?",
            (hashlib.sha256(j.encode("utf-8")).hexdigest(), j),
        )
    conn.commit()
    conn.execute("VACUUM")


def _migrer_historique_unique(conn):
    """Ajoute PRIMARY KEY (groupe, close_unix) a historique_consultations.

    Idempotente : ne fait rien si la contrainte est deja la. Les doublons
    eventuels d'une base anterieure sont fusionnes au passage -- c'est le
    comportement voulu, l'evenement n'ayant eu lieu qu'une fois.
    """
    ligne = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name='historique_consultations'").fetchone()
    if not ligne or "PRIMARY KEY" in ligne[0].upper():
        return
    conn.execute("CREATE TABLE historique_consultations_v2 "
                 "(groupe TEXT NOT NULL, close_unix REAL NOT NULL, "
                 "PRIMARY KEY (groupe, close_unix))")
    conn.execute("INSERT OR IGNORE INTO historique_consultations_v2 "
                 "SELECT groupe, close_unix FROM historique_consultations")
    conn.execute("DROP TABLE historique_consultations")
    conn.execute("ALTER TABLE historique_consultations_v2 "
                 "RENAME TO historique_consultations")
    conn.commit()


def _migrer_ouverture_depots(conn):
    """Ajoute la date d'ouverture des depots a la question active.

    Separer l'emission des depots ferme une correlation temporelle : sans
    cela, le serveur voit un jeton consomme a 14h02 puis un vote depose a
    14h02:47, et rapproche les deux registres que tout le protocole existe
    pour tenir disjoints. Dans un petit groupe, cela suffit a desanonymiser.

    La date vit dans question_active plutot que dans une table dediee : elle
    suit ainsi le cycle de vie de la consultation et disparait avec elle a la
    cloture, sans ajouter de surface a effacer.

    Migration idempotente : PRAGMA table_info avant ALTER.
    """
    colonnes = [c[1] for c in conn.execute("PRAGMA table_info(question_active)")]
    if "ouverture_depots_unix" not in colonnes:
        conn.execute("ALTER TABLE question_active ADD COLUMN ouverture_depots_unix REAL")
        conn.commit()
        print("Migration : colonne ouverture_depots_unix ajoutee a question_active.")
    if "groupes_declares" not in colonnes:
        conn.execute("ALTER TABLE question_active ADD COLUMN groupes_declares TEXT")
        conn.commit()
        print("Migration : colonne groupes_declares ajoutee a question_active.")


def _migrer_tokens_sans_rowid(conn):
    """Migration idempotente : tokens_consommes AVEC rowid -> WITHOUT ROWID.
    Le rowid implicite restituait l'ordre d'insertion des votes (SELECT rowid
    ... ORDER BY rowid). En WITHOUT ROWID la table est ordonnee par l'empreinte
    SHA-384, donc pseudo-aleatoire : plus aucune sequence temporelle.

    Detection : on lit le CREATE stocke dans sqlite_master et on cherche le
    mot-cle. Comme pour les autres migrations de cette table, on COPIE les
    empreintes avant de supprimer l'ancienne -- c'est l'anti-rejeu, la vider
    autoriserait a revoter avec un K deja utilise."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tokens_consommes'"
    ).fetchone()
    if not row:
        return  # absente : creee au bon schema par _SQL_TABLES
    if "WITHOUT ROWID" in row[0].upper():
        return  # deja migree
    conn.execute("CREATE TABLE tokens_consommes_v3 (empreinte TEXT PRIMARY KEY) WITHOUT ROWID")
    conn.execute("INSERT INTO tokens_consommes_v3 (empreinte) SELECT empreinte FROM tokens_consommes")
    conn.execute("DROP TABLE tokens_consommes")
    conn.execute("ALTER TABLE tokens_consommes_v3 RENAME TO tokens_consommes")
    conn.commit()
    # VACUUM seul depuis le passage en journal_mode=DELETE : il n'y a plus de
    # WAL a tronquer. VACUUM reecrit le fichier, ce qui libere les pages
    # contenant les anciennes lignes.
    conn.execute("VACUUM")


def initialiser():
    """Ouvre la connexion et applique les migrations. Idempotente.

    Un second appel fermait l'ancienne connexion sans la relacher : fuite de
    descripteur de fichier, et verrous SQLite potentiellement conserves par la
    connexion orpheline jusqu'au passage du ramasse-miettes. Le cas se produit
    lors d'un rechargement dynamique ou d'un appelant qui se trompe -- pas en
    exploitation normale, mais un module de persistance ne doit pas dependre de
    la discipline de son appelant. Constat d'un audit externe du 03/09/2026.
    """
    global _conn
    with _verrou_db:
        if _conn is not None:
            # Deja initialise : on ne rejoue ni la connexion ni les migrations.
            return
        _conn = _connexion()
        _migrer_schema_cles(_conn)
        _migrer_schema_tokens(_conn)
        _migrer_jetons_vers_empreintes(_conn)
        _migrer_tokens_sans_rowid(_conn)
        for sql in _SQL_TABLES:
            _conn.execute(sql)
        _conn.commit()
        # APRES la creation des tables : cette migration ajoute une colonne a
        # question_active, qui n'existe pas encore sur une base neuve. Les
        # migrations ci-dessus, elles, transforment des tables preexistantes
        # et doivent donc passer avant.
        _migrer_ouverture_depots(_conn)
        _migrer_historique_unique(_conn)
        # codes_courts : supprimee, pas seulement videe. Elle conservait le
        # jeton EN CLAIR, alors que le reste du systeme etait passe aux
        # empreintes pour qu'un lecteur de base ne puisse pas rejouer un jeton
        # et priver son titulaire de son vote. Aucun endpoint ne l'alimentait
        # plus. La vider a la cloture ne suffisait pas : sur une base
        # anterieure elle subsistait, vide mais prete a resservir.
        _conn.execute("DROP TABLE IF EXISTS codes_courts")
        _conn.commit()


def charger_budget_epsilon():
    with _verrou_db:
        rows = _conn.execute("SELECT departement, epsilon_consomme, nb_publications FROM budget_epsilon").fetchall()
    return {row[0]: {"epsilon_consomme": row[1], "nombre_publications": row[2]} for row in rows}


def persister_budget_epsilon(departement, epsilon_consomme, nb_publications):
    with _verrou_db:
        sql = "INSERT INTO budget_epsilon (departement, epsilon_consomme, nb_publications) VALUES (?, ?, ?) ON CONFLICT(departement) DO UPDATE SET epsilon_consomme = excluded.epsilon_consomme, nb_publications = excluded.nb_publications"
        _conn.execute(sql, (departement, epsilon_consomme, nb_publications))
        _conn.commit()


def charger_tokens_consommes():
    with _verrou_db:
        rows = _conn.execute("SELECT empreinte FROM tokens_consommes").fetchall()
    return {row[0] for row in rows}


def charger_compteurs():
    with _verrou_db:
        rows_comptes = _conn.execute("SELECT departement, reponse, compte FROM compteurs_votes").fetchall()
        rows_effectifs = _conn.execute("SELECT departement, effectif FROM effectifs").fetchall()
    compteurs = {}
    for dep, rep, compte in rows_comptes:
        compteurs.setdefault(dep, {})[rep] = compte
    effectifs = {row[0]: row[1] for row in rows_effectifs}
    return compteurs, effectifs


def persister_vote(departement, reponse, nouveau_compte, nouvel_effectif):
    with _verrou_db:
        sql1 = "INSERT INTO compteurs_votes (departement, reponse, compte) VALUES (?, ?, ?) ON CONFLICT(departement, reponse) DO UPDATE SET compte = excluded.compte"
        _conn.execute(sql1, (departement, reponse, nouveau_compte))
        sql2 = "INSERT INTO effectifs (departement, effectif) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET effectif = excluded.effectif"
        _conn.execute(sql2, (departement, nouvel_effectif))
        _conn.commit()


class DoubleVoteErreur(Exception):
    """Leve quand l'empreinte K est deja dans tokens_consommes. La DB est
    l'AUTORITE anti-rejeu : meme si le cache memoire est incoherent (clear
    partiel, futur multi-worker, restauration de DB), la contrainte PRIMARY
    KEY refuse le doublon. L'endpoint doit convertir en HTTP 409."""


def enregistrer_vote_atomique(departement, reponse, empreinte_k):
    """Modele B : enregistre un vote ET marque le secret K comme consomme dans
    UNE SEULE transaction SQLite. Invariants critiques :
    1. Le compteur et le registre anti-rejeu (tokens_consommes) sont ecrits
       ensemble ou pas du tout. Un seul commit() a la fin. Si le processus
       meurt avant le commit, ni le vote ni la consommation ne sont persistes
       -> pas de double-vote possible, pas de vote fantome.
    2. L'INSERT dans tokens_consommes est STRICT (pas de OR IGNORE) et vient
       EN PREMIER : si l'empreinte existe deja, IntegrityError est levee
       AVANT toute autre ecriture, rollback, et DoubleVoteErreur remonte.
       La DB est l'autorite anti-rejeu, pas le dict memoire.
    Ne PAS remplacer par des appels separes a persister_vote +
    des ecritures separees du compteur et du registre (deux commits = bug
    historique double-commit). Une ancienne fonction persister_token_consomme
    faisait cet INSERT en OR IGNORE hors transaction : supprimee le 23/07 car
    jamais appelee et contournant l'invariant ci-dessus (un doublon y passait
    silencieusement au lieu de lever).
    Ne PAS remettre OR IGNORE (doublon silencieusement compte = bug)."""
    with _verrou_db:
        try:
            _conn.execute(
                "INSERT INTO tokens_consommes (empreinte) VALUES (?)",
                (empreinte_k,),
            )
            # INCREMENT RELATIF (pas de valeur absolue venue de la RAM).
            # Correctif P-D : ecrire "compte = excluded.compte" depuis un
            # compteur memoire permettait, si la RAM etait en retard d'un cran
            # (commit reussi puis exception avant mise a jour memoire), qu'un
            # vote suivant ecrase silencieusement le precedent. Avec
            # "compte = compte + 1" la DB est seule autorite du compteur :
            # l'etat memoire ne peut plus corrompre le total.
            _conn.execute(
                "INSERT INTO compteurs_votes (departement, reponse, compte) VALUES (?, ?, 1) "
                "ON CONFLICT(departement, reponse) DO UPDATE SET compte = compte + 1",
                (departement, reponse),
            )
            _conn.execute(
                "INSERT INTO effectifs (departement, effectif) VALUES (?, 1) "
                "ON CONFLICT(departement) DO UPDATE SET effectif = effectif + 1",
                (departement,),
            )
            # Relire les valeurs VRAIES apres incrementation : l'appelant
            # resynchronise sa memoire dessus au lieu de recalculer.
            compte_reel = _conn.execute(
                "SELECT compte FROM compteurs_votes WHERE departement = ? AND reponse = ?",
                (departement, reponse),
            ).fetchone()[0]
            effectif_reel = _conn.execute(
                "SELECT effectif FROM effectifs WHERE departement = ?",
                (departement,),
            ).fetchone()[0]
            _conn.commit()
            # Le vote est persiste : on peut tronquer le journal sans risque.
            # Apres le commit, jamais avant.
            return compte_reel, effectif_reel
        except sqlite3.IntegrityError:
            _conn.rollback()
            raise DoubleVoteErreur(empreinte_k)
        except Exception:
            _conn.rollback()
            raise


def _empreinte_jeton(jeton):
    """SHA-256 du jeton d'autorisation. La base ne stocke JAMAIS le jeton en
    clair : sinon un lecteur de base (Niveau 1) recupere les jetons non
    consommes par un simple SELECT et les rejoue contre /api/signer_aveugle,
    qui est public. Il obtient des signatures valides sans clé privée et sans
    modifier le logiciel : bourrage, et privation de vote en consommant le
    jeton d'une personne avant elle. Le registre 2 hachait deja K (SHA-384) ;
    cette asymetrie etait la porte. Le jeton en clair n'existe plus que dans
    le lien SMS (cote RH) et dans la requete du votant, jamais au repos."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def persister_jetons_autorisation_lot(jetons, departement):
    """Enregistre les empreintes de PLUSIEURS jetons en UNE transaction.

    L'appel unitaire persister_jeton_autorisation fait un commit par jeton, et
    PRAGMA synchronous=FULL impose un fsync par commit. Generer 1000 jetons
    signifiait donc 1000 fsync -- de une a dix secondes pendant lesquelles
    l'appelant tenait le verrou global de l'API : tous les votes en cours
    partaient en timeout, et sur les 10 000 invitations visees, dix gels
    successifs. C'etait aussi un vecteur d'auto-deni de service trivial, le
    serveur tournant avec un worker unique.

    Ici : un executemany, un commit, un fsync. Le gain est de deux ordres de
    grandeur sur un lot de 1000.
    """
    if not jetons:
        return
    with _verrou_db:
        _conn.executemany(
            "INSERT INTO jetons_autorisation (jeton, departement, utilise) VALUES (?, ?, 0) "
            "ON CONFLICT(jeton) DO NOTHING",
            [(_empreinte_jeton(j), departement) for j in jetons],
        )
        _conn.commit()


def persister_jeton_autorisation(jeton, departement):
    """Enregistre l'EMPREINTE d'un jeton d'autorisation a sa generation.

    Conserve pour les appels unitaires et les tests. Pour un lot, utiliser
    persister_jetons_autorisation_lot (un seul commit au lieu de N).
    """
    with _verrou_db:
        _conn.execute(
            "INSERT INTO jetons_autorisation (jeton, departement, utilise) VALUES (?, ?, 0) "
            "ON CONFLICT(jeton) DO NOTHING",
            (_empreinte_jeton(jeton), departement),
        )
        _conn.commit()


def consommer_jeton_autorisation(jeton):
    """Consomme un jeton d'autorisation de facon ATOMIQUE. Renvoie le
    departement si le jeton existait et n'etait pas encore utilise, sinon None.
    L'atomicite (UPDATE ... WHERE utilise=0 en une seule transaction) empeche
    qu'un meme jeton soit consomme deux fois par deux requetes simultanees
    (protection anti-double-vote a la source)."""
    with _verrou_db:
        emp = _empreinte_jeton(jeton)
        cur = _conn.execute(
            "UPDATE jetons_autorisation SET utilise = 1 WHERE jeton = ? AND utilise = 0",
            (emp,),
        )
        if cur.rowcount != 1:
            _conn.commit()
            return None  # jeton inconnu OU deja utilise
        row = _conn.execute(
            "SELECT departement FROM jetons_autorisation WHERE jeton = ?",
            (emp,),
        ).fetchone()
        _conn.commit()
        return row[0] if row else None


def charger_question():
    """Intitule de la question en cours, ou None si aucun n'a ete defini."""
    with _verrou_db:
        row = _conn.execute("SELECT intitule FROM question_active WHERE id = 1").fetchone()
    return row[0] if row else None


# Duree de conservation des signatures emises, pour l'idempotence.
#
# Ce cache retient le couple (empreinte du jeton -> empreinte du message
# AVEUGLE) avec la signature aveugle emise.
#
# CE QU'IL REVELE EXACTEMENT, ET IL FAUT LE DIRE JUSTE.
# Le facteur d'aveuglement r ne quitte jamais le navigateur du votant. Sans
# lui, aucune de ces valeurs ne se raccroche au depot, qui porte hash(K) et la
# signature FINALISEE. Le cache etablit donc seulement qu'un jeton a obtenu une
# signature -- information que jetons_autorisation.utilise = 1 inscrit deja en
# base, sans limite de retention. L'apport marginal est proche de zero.
#
# Ce n'est PAS le lien identite -> reponse. Une formulation anterieure de ce
# commentaire disait « exactement ce que le protocole existe pour ne pas
# conserver » : c'etait exagere, et le 26/08 un relecteur externe l'a cite tel
# quel pour conclure a une violation de la garantie centrale. Un commentaire
# qui surestime un risque fabrique des fausses alertes, exactement comme un
# commentaire qui le minimise en cache de vraies. Analyse complete :
# LIMITS.md section 1.
#
# On garde neanmoins le minimum : assez pour qu'un votant dont le navigateur a
# echoue puisse recharger sa page et retrouver SA signature, pas davantage.
#
# Une heure couvre un rechargement, un retour en arriere, une perte de reseau.
# Elle ne couvre pas un votant qui reviendrait le lendemain : celui-la devra
# demander un nouveau lien. C'est l'arbitrage retenu -- une voix perdue est
# rattrapable par l'organisation, une donnee de correlation conservee sept
# jours ne l'est pas.
RETENTION_SIGNATURES_SECONDES = 3600


# Cache MEMOIRE des signatures emises. Deliberement pas en base.
#
# POURQUOI PAS EN BASE
# La premiere version persistait ce cache dans une table SQLite. Consequence
# mesuree : ses commits s'intercalaient, dans le MEME fichier journal WAL, avec
# ceux des compteurs de votes. Le journal donnait alors
#
#     empreinte_jeton_d_ALICE  ->  compteur "oui" +1
#     empreinte_jeton_de_BOB   ->  compteur "non" +1
#
# L'empreinte du jeton identifie la personne : l'organisation detient la liste
# (personne -> jeton) et n'a qu'a calculer le SHA-384 de chacun. Un instantane
# du seul fichier journal attribuait donc nommement les dernieres reponses --
# exactement ce que tout le protocole existe pour empecher.
#
# Le compteur de troncature du WAL n'y changeait rien : il ne compte que les
# ecritures de vote, les commits de signature s'intercalaient sans etre comptes.
#
# CE QUE COUTE LE CACHE MEMOIRE
# Un redemarrage du service vide le cache : un votant dont la finalisation a
# echoue juste avant perd sa voix. C'est le mode de defaillance qui existait
# AVANT l'idempotence -- pas de regression face a cet etat-la, mais bien une
# perte face a la version persistee qui a brievement tourne entre les deux.
# L'arbitrage est assume : une voix perdue se rattrape par un nouveau lien, une
# donnee de correlation ecrite sur disque ne se rattrape pas.
# Le cas courant (rechargement de page, coupure reseau breve) reste couvert.
#
# Le service tourne en worker unique par construction (_verifier_worker_unique
# refuse de demarrer autrement), donc un dictionnaire de processus suffit : il
# n'y a pas d'autre processus avec qui partager cet etat.
_signatures_emises = {}


def _horloge_cache():
    """Horloge MONOTONE pour la retention du cache de signatures.

    `time.time()` suit l'horloge murale : un ajustement NTP, un changement
    manuel, un decalage au demarrage font varier la duree de retention reelle.
    Vers l'avant, le cache est purge trop tot -- un votant perd son rattrapage.
    Vers l'arriere, il est conserve PLUS d'une heure : le couple
    (empreinte du jeton -> empreinte du message aveugle) reste en memoire au-dela
    de ce que ce module annonce, sans que rien ne le signale.

    `time.monotonic()` ne recule jamais et ignore les ajustements d'horloge.
    Elle ne survit pas a un redemarrage du processus -- mais ce cache non plus :
    il est en memoire, il meurt avec lui. C'est donc l'horloge exacte pour cet
    usage.

    A NE PAS ETENDRE a historique_consultations : sa fenetre de douze mois
    glissants doit traverser les redemarrages, et exige l'horloge murale.

    Constat d'un audit externe du 03/09/2026.
    """
    return time.monotonic()


def _purger_signatures_expirees(seuil):
    """Efface physiquement les entrees expirees. A appeler SOUS _verrou_db.

    Ignorer une entree expiree ne suffit pas : ses octets restent en memoire
    de processus. Un vidage de memoire, un swap, une image de machine virtuelle
    prise plusieurs jours apres la derniere signature contiendraient encore le
    couple (empreinte du jeton -> empreinte du message aveugle).

    Ce couple n'etablit pas le lien identite -> reponse -- voir le commentaire
    de RETENTION_SIGNATURES_SECONDES ci-dessus. Il n'a pas a trainer pour
    autant : cette section inventorie ce que le systeme conserve, et une
    structure gardant plus longtemps que ce qu'elle annonce merite sa ligne.

    PORTEE EXACTE DE CETTE PURGE
    `del` supprime la reference, il n'ecrase pas la memoire : Python peut
    conserver la chaine jusqu'au passage du ramasse-miettes, et rien ne
    garantit qu'elle ne subsiste pas dans une page liberee. Un vidage de
    memoire ou une image de machine virtuelle pourraient donc encore la
    contenir apres l'heure annoncee.

    Ce n'est donc pas un effacement securise, et le pretendre serait faux. Ce
    que cette purge garantit : la donnee n'est plus atteignable par le code, et
    le cache reste borne. Un effacement reel exigerait de manipuler des
    bytearray et de les zeroiser -- envisageable, non fait a ce jour.
    """
    for cle in [k for k, v in _signatures_emises.items() if v[2] <= seuil]:
        del _signatures_emises[cle]


def signature_deja_emise(empreinte_jeton, empreinte_message):
    """Signature deja emise pour ce couple exact, ou None.

    Le couple porte sur le jeton ET le message aveugle. Un rejeu a l'identique
    retrouve sa signature. Un message DIFFERENT avec le meme jeton ne trouve
    rien : c'est une tentative d'obtenir un second credential, et l'appelant
    la refuse.
    """
    seuil = _horloge_cache() - RETENTION_SIGNATURES_SECONDES
    with _verrou_db:
        _purger_signatures_expirees(seuil)
        entree = _signatures_emises.get((empreinte_jeton, empreinte_message))
        if entree is None:
            return None
        return (entree[0], entree[1])


def jeton_a_deja_signe(empreinte_jeton):
    """True si ce jeton a deja obtenu une signature, quel qu'en soit le message.

    Distingue deux cas que l'echec de consommation confond : un rejeu identique
    (rattrapable) et une tentative de SECOND message aveugle (refus).
    """
    seuil = _horloge_cache() - RETENTION_SIGNATURES_SECONDES
    with _verrou_db:
        _purger_signatures_expirees(seuil)
        for jeton, _msg in _signatures_emises:
            if jeton == empreinte_jeton:
                return True
    return False


def enregistrer_signature_emise(empreinte_jeton, empreinte_message, signature_hex, departement):
    """Memorise une signature pour permettre le rejeu identique.

    Purge les entrees expirees au passage : pas de tache de fond, et le cache
    reste borne par le nombre de signatures d'une heure.
    """
    maintenant = _horloge_cache()
    seuil = maintenant - RETENTION_SIGNATURES_SECONDES
    with _verrou_db:
        _signatures_emises[(empreinte_jeton, empreinte_message)] = (
            signature_hex, departement, maintenant)
        _purger_signatures_expirees(seuil)


def vider_signatures_emises():
    """Vide le cache. Appele a la cloture, avec le reste de l'etat."""
    with _verrou_db:
        _signatures_emises.clear()


def charger_groupes_declares():
    """Liste des groupes declares, ou None si aucune declaration.

    Les groupes sont figes AVANT tout envoi de liens, pour que l'empreinte de
    l'ensemble des cles -- inscrite dans chaque lien -- ne change plus. Sans
    cela, generer un groupe supplementaire modifierait l'empreinte et
    invaliderait tous les liens deja distribues.
    """
    with _verrou_db:
        row = _conn.execute(
            "SELECT groupes_declares FROM question_active WHERE id = 1"
        ).fetchone()
    if not row or not row[0]:
        return None
    import json as _json
    return _json.loads(row[0])


def enregistrer_consultation_close(groupes):
    """Note la date de cloture pour chaque groupe consulte.

    POURQUOI CETTE TABLE SURVIT A LA CLOTURE
    Tout le reste est efface : compteurs, jetons, budget, cles. Cette table ne
    l'est pas, deliberement, parce qu'elle sert precisement a se souvenir
    d'apres.

    Ce qu'elle contient est anodin -- un nom de groupe et une date -- et ne dit
    rien sur les reponses. Mais elle permet d'avertir un organisateur qui
    reconsulte le meme groupe trop souvent : chaque publication apprend un peu
    sur la population, et cette usure ne se voit pas.

    CE QUE CET AVERTISSEMENT NE PEUT PAS FAIRE
    VERA ne connait pas vos membres -- c'est ce qui protege leur anonymat. Il ne
    peut donc pas savoir que le groupe « Atelier 2 » designe les memes personnes
    que « Atelier ». Un organisateur qui renomme ses groupes contourne cet
    avertissement sans le vouloir, ou en le voulant.
    C'est un garde-fou de bonne foi, pas une contrainte. La regle des quatre
    consultations annuelles reste sous la responsabilite de l'organisation.
    """
    maintenant = time.time()
    with _verrou_db:
        for g in groupes:
            # OR IGNORE : la PRIMARY KEY refuse le doublon, on ne veut pas
            # qu'une cloture rejouee leve. L'idempotence est ici la bonne
            # reponse -- l'evenement « ce groupe a ete clos a cet instant » est
            # vrai une fois, pas deux.
            _conn.execute(
                "INSERT OR IGNORE INTO historique_consultations "
                "(groupe, close_unix) VALUES (?, ?)",
                (g, maintenant))
        _conn.commit()


def compter_consultations_recentes(groupe, fenetre_secondes=365 * 24 * 3600):
    """Nombre de consultations closes sur ce groupe dans la fenetre donnee."""
    seuil = time.time() - fenetre_secondes
    with _verrou_db:
        row = _conn.execute(
            "SELECT COUNT(*) FROM historique_consultations "
            "WHERE groupe = ? AND close_unix > ?",
            (groupe, seuil)).fetchone()
    return row[0] if row else 0


def persister_groupes_declares(groupes):
    """Fige la liste des groupes. Ecrit sur la ligne de question_active."""
    import json as _json
    with _verrou_db:
        _conn.execute(
            "INSERT INTO question_active (id, intitule, groupes_declares) "
            "VALUES (1, '', ?) "
            "ON CONFLICT(id) DO UPDATE SET groupes_declares = excluded.groupes_declares",
            (_json.dumps(groupes, ensure_ascii=False),),
        )
        _conn.commit()


def charger_ouverture_depots():
    """Instant a partir duquel les votes sont acceptes, ou None si non fixe.

    None signifie « depots ouverts immediatement » : c'est le comportement
    des consultations creees avant cette fonctionnalite, qu'on ne casse pas
    retroactivement.
    """
    with _verrou_db:
        row = _conn.execute(
            "SELECT ouverture_depots_unix FROM question_active WHERE id = 1"
        ).fetchone()
    return row[0] if row and row[0] is not None else None


def persister_ouverture_depots(instant_unix):
    """Fige l'instant d'ouverture des depots.

    Ecrit sur la ligne de question_active, creee au besoin : le RH peut fixer
    la date avant d'avoir saisi sa question.
    """
    with _verrou_db:
        _conn.execute(
            "INSERT INTO question_active (id, intitule, ouverture_depots_unix) "
            "VALUES (1, '', ?) "
            "ON CONFLICT(id) DO UPDATE SET ouverture_depots_unix = excluded.ouverture_depots_unix",
            (instant_unix,),
        )
        _conn.commit()


def persister_question(intitule):
    """Fige l'intitule de la consultation. Ecrase l'eventuel precedent :
    l'API n'autorise l'appel que tant qu'aucune cle n'existe."""
    with _verrou_db:
        _conn.execute(
            "INSERT INTO question_active (id, intitule) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET intitule = excluded.intitule",
            (intitule,),
        )
        _conn.commit()


def charger_jetons_autorisation():
    """Recharge l'etat des jetons d'autorisation au demarrage.

    Renvoie {EMPREINTE_SHA256: (departement, utilise)} -- PAS le jeton en
    clair, qui n'existe nulle part en base depuis le correctif de la Porte A.
    Un appelant qui chercherait un jeton en clair dans ce dict ne trouverait
    jamais rien : il doit hacher via _empreinte_jeton() au prealable."""
    with _verrou_db:
        rows = _conn.execute(
            "SELECT jeton, departement, utilise FROM jetons_autorisation"
        ).fetchall()
    return {row[0]: (row[1], bool(row[2])) for row in rows}


def compter_jetons_par_departement():
    """Nombre de jetons d'autorisation GENERES par departement (utilises ou
    non). Agregat NON identifiant : c'est la quantite que le RH a lui-meme
    saisie a la generation -- il ne relie aucun votant a rien, aucune reponse
    a personne. Sert au tableau de bord a (1) montrer qu'un departement existe
    des la generation, avant tout vote, sinon le RH croit a un echec et
    regenere en doublant les liens ; (2) avertir qu'un departement dont le
    total d'invitations est deja sous K_MIN ne pourra jamais publier. Lecture
    seule, aucune mutation."""
    with _verrou_db:
        rows = _conn.execute(
            "SELECT departement, COUNT(*) FROM jetons_autorisation GROUP BY departement"
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def effacer_etat_consultation():
    """Efface TOUT l'etat brut d'une consultation : compteurs, effectifs,
    codes courts, tokens consommes, budget epsilon, resultats publies,
    jetons d'autorisation.
    NE touche PAS a la cle RSA (infrastructure, pas donnee de consultation).

    Apres cet appel, le serveur ne conserve plus AUCUNE donnee de la
    consultation cloturee : ni resultat, ni compteur, ni code. C'est la
    garantie de minimisation de VERA rendue operationnelle -- un acces au
    serveur apres cloture ne revele rien de la consultation passee.
    Operation atomique (une seule transaction)."""
    with _verrou_db:
        for table in ("compteurs_votes", "effectifs",
                      "tokens_consommes", "budget_epsilon", "resultats_publies", "question_active",
                      "jetons_autorisation"):
            _conn.execute(f"DELETE FROM {table}")

        _conn.commit()
    # Le cache memoire des signatures aussi : il contient le lien
    # (jeton -> message aveugle), donnee de correlation la plus sensible du
    # systeme. Il expire de lui-meme en une heure, la cloture n'attend pas.
    vider_signatures_emises()
    # Checkpoint + VACUUM APRES le commit, hors transaction (SQLite l'exige).
    # Sans eux, la promesse affichee au RH -- "apres cloture le serveur ne
    # conserve plus rien" -- n'est vraie qu'au niveau LOGIQUE : les lignes
    # supprimees restent lisibles dans le journal -wal (qui contient les pages
    # AVANT suppression) et dans les pages liberees du fichier .db. Le PRAGMA
    # secure_delete ecrase les octets d'une ligne supprimee, mais les pages
    # liberees peuvent conserver des traces jusqu'a reecriture du fichier.
    # Meme correctif que celui applique aux migrations le 23/07 : le DROP
    # nettoyait la vue, pas les octets.
    #
    # Le wal_checkpoint qui figurait ici n'a plus d'objet depuis le passage en
    # journal_mode=DELETE (13/08) : aucun journal ne persiste entre deux
    # transactions. VACUUM suffit et fait le travail.
    #
    # LE VERROU EST TENU PENDANT LE VACUUM, ET C'EST ACCEPTABLE ICI.
    #
    # Un audit externe du 03/09/2026 l'a qualifie de « deni de service par
    # construction » : VACUUM reecrit tout le fichier, ce qui peut durer
    # plusieurs secondes, et rien ne passe pendant ce temps.
    #
    # Le constat est exact, la portee ne l'est pas. Cette fonction n'est appelee
    # que par la CLOTURE (vera_consultation_api.py) : a cet instant la
    # consultation est fermee, plus aucun vote n'est accepte, et il n'y a rien a
    # bloquer. Les autres VACUUM de ce module sont dans les migrations, jouees au
    # DEMARRAGE, avant que le service ne serve.
    #
    # Le sortir du verrou serait pire : une lecture concurrente pendant la
    # reecriture du fichier verrait un etat intermediaire. La minimisation des
    # octets doit etre atomique -- c'est tout l'objet de cette fonction.
    with _verrou_db:
        _conn.execute("VACUUM")


def effacer_cle_rsa():
    """Efface TOUTES les cles RSA (destruction groupee : toutes les cles de
    departement d'une consultation meurent ensemble a la cloture)."""
    with _verrou_db:
        _conn.execute("DELETE FROM cle_rsa_active")
        _conn.commit()


def charger_toutes_cles_chiffrees() -> dict:
    """Charge et dechiffre TOUTES les cles de departement (rechargement au boot).
    Renvoie {departement: (cle_privee_der, cle_publique_der, ouverture_unix)}.
    Une cle sans salt (ancien format) est ignoree avec avertissement plutot que
    de bloquer tout le rechargement.

    FAIL-CLOSED si AUCUNE cle ne se dechiffre alors que la table en contient.
    Auparavant un echec de dechiffrement etait avale par un `continue`
    silencieux : si VERA_DB_KEY etait erronee au redemarrage (typo dans l'unit
    systemd, restauration sur une autre machine, rotation mal appliquee), les
    cles existantes etaient ignorees sans le moindre signal et de NOUVELLES
    cles etaient generees a la premiere demande. Consequence : tous les liens
    deja distribues par SMS -- qui portent l'empreinte de l'ancienne cle dans
    leur fragment #k= -- devenaient invalides en pleine consultation, et le
    RH ne l'apprenait que par les plaintes des votants.

    Refuser de demarrer est le comportement sur : l'operateur voit
    immediatement l'erreur, corrige la cle, et redemarre sans avoir rien
    detruit. Le cas legitime de rotation de VERA_DB_KEY passe par la cloture
    de consultation, qui purge ces lignes -- la table est alors vide et ce
    garde-fou ne se declenche pas.
    """
    with _verrou_db:
        rows = _conn.execute(
            "SELECT departement, cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex FROM cle_rsa_active"
        ).fetchall()
    resultat = {}
    echecs = 0
    for dep, priv_hex, pub_hex, ouverture, salt_hex in rows:
        if salt_hex is None:
            echecs += 1
            print(f"ATTENTION : cle du departement '{dep}' en ancien format (sans salt), ignoree.")
            continue
        salt = bytes.fromhex(salt_hex)
        f = _get_fernet(salt)
        try:
            cle_privee = f.decrypt(bytes.fromhex(priv_hex))
        except Exception:
            echecs += 1
            print(f"CRITIQUE : dechiffrement impossible pour le departement '{dep}' "
                  f"-- VERA_DB_KEY ne correspond pas a cette cle.")
            continue
        resultat[dep] = (cle_privee, bytes.fromhex(pub_hex), ouverture)

    # Des cles existent en base mais AUCUNE n'est exploitable : la cle de
    # chiffrement est presque certainement la mauvaise. Continuer reviendrait
    # a regenerer des cles et a invalider tous les liens en circulation.
    if rows and not resultat:
        raise RuntimeError(
            f"VERA REFUSE DE DEMARRER : {len(rows)} cle(s) RSA presente(s) en base, "
            f"aucune dechiffrable ({echecs} echec(s)). VERA_DB_KEY ne correspond pas "
            "aux cles stockees. Verifier la variable d'environnement dans l'unit "
            "systemd. Demarrer malgre tout regenererait des cles et invaliderait "
            "TOUS les liens de vote deja distribues."
        )
    return resultat


# --------------------------------------------------------------------------
# Chiffrement de la cle RSA (Porte 11)
# --------------------------------------------------------------------------

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_PBKDF2_ITERATIONS = 100000

def _get_fernet(salt: bytes) -> Fernet:
    secret = os.environ.get("VERA_DB_KEY", "")
    if not secret:
        raise RuntimeError(
            "ERREUR CRITIQUE : VERA_DB_KEY non definie. "
            "La cle RSA ne peut pas etre chiffree/dechiffree. "
            "Verifiez le fichier systemd."
        )
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    cle_derivee = base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))
    return Fernet(cle_derivee)


def persister_cle_rsa_chiffree(departement: str, cle_privee_der: bytes, cle_publique_der: bytes, ouverture_unix: float) -> None:
    """Ecrit la cle RSA d'UN departement, chiffree avec VERA_DB_KEY, salt aleatoire
    par enregistrement. Une ligne par departement (PRIMARY KEY departement)."""
    salt = os.urandom(16)
    f = _get_fernet(salt)
    cle_privee_chiffree = f.encrypt(cle_privee_der).hex()
    with _verrou_db:
        sql = "INSERT INTO cle_rsa_active (departement, cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex) VALUES (?, ?, ?, ?, ?) ON CONFLICT(departement) DO UPDATE SET cle_privee_hex = excluded.cle_privee_hex, cle_publique_hex = excluded.cle_publique_hex, ouverture_unix = excluded.ouverture_unix, salt_hex = excluded.salt_hex"
        _conn.execute(sql, (departement, cle_privee_chiffree, cle_publique_der.hex(), ouverture_unix, salt.hex()))
        _conn.commit()


def charger_cle_rsa_chiffree(departement: str) -> tuple[bytes, bytes, float] | None:
    """Charge et dechiffre la cle RSA d'UN departement en utilisant le salt stocke."""
    with _verrou_db:
        row = _conn.execute(
            "SELECT cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex FROM cle_rsa_active WHERE departement = ?",
            (departement,)
        ).fetchone()
    if row is None:
        return None
    if row[3] is None:
        raise RuntimeError(
            "Cle RSA persistee sans salt (ancien format pre-migration). "
            "Supprimez la ligne dans cle_rsa_active pour forcer une regeneration."
        )
    salt = bytes.fromhex(row[3])
    f = _get_fernet(salt)
    try:
        cle_privee = f.decrypt(bytes.fromhex(row[0]))
    except Exception as e:
        raise RuntimeError(
            f"Impossible de dechiffrer la cle RSA depuis SQLite : {e}. "
            "Verifiez que VERA_DB_KEY est correcte et inchangee."
        )
    cle_publique = bytes.fromhex(row[1])
    return cle_privee, cle_publique, row[2]


def persister_resultat_publie(departement, resultat_dict):
    """Stocke le resultat bruite fige d'un departement (calcule une seule fois)."""
    import json
    with _verrou_db:
        sql = "INSERT INTO resultats_publies (departement, resultat_json) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET resultat_json = excluded.resultat_json"
        _conn.execute(sql, (departement, json.dumps(resultat_dict)))
        _conn.commit()


def persister_publication_atomique(departement, epsilon_consomme, nb_publications, resultat_dict):
    """Persiste le budget epsilon ET le resultat fige dans UNE SEULE
    transaction. Empeche l'etat incoherent "budget consomme mais resultat
    absent" qui, apres un crash entre deux commits separes, verrouillait
    definitivement un departement (deja_publie=True mais resultat introuvable).
    Un crash laisse desormais soit les deux ecritures, soit aucune."""
    import json
    with _verrou_db:
        sql_budget = "INSERT INTO budget_epsilon (departement, epsilon_consomme, nb_publications) VALUES (?, ?, ?) ON CONFLICT(departement) DO UPDATE SET epsilon_consomme = excluded.epsilon_consomme, nb_publications = excluded.nb_publications"
        _conn.execute(sql_budget, (departement, epsilon_consomme, nb_publications))
        sql_resultat = "INSERT INTO resultats_publies (departement, resultat_json) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET resultat_json = excluded.resultat_json"
        _conn.execute(sql_resultat, (departement, json.dumps(resultat_dict)))
        _conn.commit()  # un seul commit -> atomicite


def charger_resultat_publie(departement):
    """Recupere le resultat bruite fige d'un departement, ou None s'il n'existe pas."""
    import json
    with _verrou_db:
        row = _conn.execute("SELECT resultat_json FROM resultats_publies WHERE departement = ?", (departement,)).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
