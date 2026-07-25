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
    "CREATE TABLE IF NOT EXISTS codes_courts (code TEXT PRIMARY KEY, token TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS jetons_autorisation (jeton TEXT PRIMARY KEY, departement TEXT NOT NULL, utilise INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS cle_rsa_active (departement TEXT PRIMARY KEY, cle_privee_hex TEXT NOT NULL, cle_publique_hex TEXT NOT NULL, ouverture_unix REAL NOT NULL, salt_hex TEXT)",
]


def _connexion():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
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
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("VACUUM")


def initialiser():
    global _conn
    with _verrou_db:
        _conn = _connexion()
        _migrer_schema_cles(_conn)
        _migrer_schema_tokens(_conn)
        _migrer_jetons_vers_empreintes(_conn)
        _migrer_tokens_sans_rowid(_conn)
        for sql in _SQL_TABLES:
            _conn.execute(sql)
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
            return compte_reel, effectif_reel
        except sqlite3.IntegrityError:
            _conn.rollback()
            raise DoubleVoteErreur(empreinte_k)
        except Exception:
            _conn.rollback()
            raise


def charger_codes_courts():
    """Recharge le mapping {code_court: token} au demarrage. Sans cela, un
    redemarrage pendant une consultation active invaliderait tous les codes
    a 4 chiffres deja distribues aux participants."""
    with _verrou_db:
        rows = _conn.execute("SELECT code, token FROM codes_courts").fetchall()
    return {row[0]: row[1] for row in rows}


def persister_code_court(code, token):
    """Enregistre un code court a sa generation."""
    with _verrou_db:
        _conn.execute(
            "INSERT INTO codes_courts (code, token) VALUES (?, ?) "
            "ON CONFLICT(code) DO UPDATE SET token = excluded.token",
            (code, token),
        )
        _conn.commit()


def supprimer_code_court(code):
    """Supprime un code court une fois le token consomme. Libere l'espace des
    codes (evite la saturation a long terme) et empeche toute reutilisation."""
    with _verrou_db:
        _conn.execute("DELETE FROM codes_courts WHERE code = ?", (code,))
        _conn.commit()


# ============================================================================
# REGISTRE 1 -- Jetons d'autorisation (credentials d'emission, refactor crypto)
# Ces jetons prouvent le DROIT de demander une signature aveugle (Temps 1).
# Ils sont distribues par le RH (SMS). Usage unique. Ce registre est SEPARE du
# registre des tokens de vote consommes (tokens_consommes / Temps 2) et ne doit
# JAMAIS etre joint a lui -- c'est ce qui garantit la non-liaison identite<->vote.
# ============================================================================

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


def persister_jeton_autorisation(jeton, departement):
    """Enregistre l'EMPREINTE d'un jeton d'autorisation a sa generation."""
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
        for table in ("compteurs_votes", "effectifs", "codes_courts",
                      "tokens_consommes", "budget_epsilon", "resultats_publies",
                      "jetons_autorisation"):
            _conn.execute(f"DELETE FROM {table}")
        _conn.commit()
    # Checkpoint + VACUUM APRES le commit, hors transaction (SQLite l'exige).
    # Sans eux, la promesse affichee au RH -- "apres cloture le serveur ne
    # conserve plus rien" -- n'est vraie qu'au niveau LOGIQUE : les lignes
    # supprimees restent lisibles dans le journal -wal (qui contient les pages
    # AVANT suppression) et dans les pages liberees du fichier .db. Le PRAGMA
    # secure_delete ecrase bien les octets d'une ligne supprimee, mais il ne
    # vide pas le WAL. Meme correctif que celui applique aux migrations le
    # 23/07 : le DROP nettoyait la vue, pas les octets.
    with _verrou_db:
        _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
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
    de bloquer tout le rechargement."""
    with _verrou_db:
        rows = _conn.execute(
            "SELECT departement, cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex FROM cle_rsa_active"
        ).fetchall()
    resultat = {}
    for dep, priv_hex, pub_hex, ouverture, salt_hex in rows:
        if salt_hex is None:
            continue  # ancien format sans salt : ignore
        salt = bytes.fromhex(salt_hex)
        f = _get_fernet(salt)
        try:
            cle_privee = f.decrypt(bytes.fromhex(priv_hex))
        except Exception:
            continue  # dechiffrement impossible (VERA_DB_KEY changee) : ignore
        resultat[dep] = (cle_privee, bytes.fromhex(pub_hex), ouverture)
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
