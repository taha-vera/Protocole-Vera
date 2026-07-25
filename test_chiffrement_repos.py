#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_chiffrement_repos.py -- Verifie ce qui est, ou n'est pas, chiffre au
repos dans le fichier .db. Point important pour l'argument "anonymat prouve" :
que revele le vol du fichier de base ?

Isolation : base temporaire jetable. Ne touche jamais la prod.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_test_chiffrement_repos"
import vera_persistance as p

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
p.DB_PATH = Path(_tmp.name)
p.initialiser()

class Echec(Exception): pass
def _ok(n): print(f"OK   {n}")
def _nettoyer():
    for s in ("", "-wal", "-shm"):
        try: Path(str(_tmp.name)+s).unlink()
        except FileNotFoundError: pass

def _octets_db():
    """Lit tous les octets du fichier .db (+ WAL) pour inspection au repos."""
    data = b""
    for s in ("", "-wal", "-shm"):
        chemin = Path(str(_tmp.name)+s)
        if chemin.exists():
            data += chemin.read_bytes()
    return data

def main():
    print("Test chiffrement au repos (base jetable)")
    print("-" * 50)
    ok = True

    # La cle RSA privee ne doit JAMAIS apparaitre en clair.
    try:
        cle_privee_secrete = b"SECRET_CLE_RSA_PRIVEE_NE_DOIT_PAS_FUIR_9999"
        p.persister_cle_rsa_chiffree("DeptTest", cle_privee_secrete, b"pub", 1.0)
        # forcer l'ecriture WAL sur disque
        p._conn.execute("PRAGMA wal_checkpoint(FULL)")
        octets = _octets_db()
        if cle_privee_secrete in octets:
            raise Echec("la cle RSA privee APPARAIT EN CLAIR dans le .db !")
        _ok("1. cle RSA privee absente du fichier en clair (chiffree)")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # Constat honnete : les VOTES (departement, reponse) sont-ils en clair ?
    # On le documente factuellement plutot que d'affirmer.
    try:
        p.persister_vote("DEPT_TEST_XYZ", "reponse_test_abc", 1, 1)
        p._conn.execute("PRAGMA wal_checkpoint(FULL)")
        octets = _octets_db()
        dept_en_clair = b"DEPT_TEST_XYZ" in octets
        rep_en_clair = b"reponse_test_abc" in octets
        print(f"     [constat] departement en clair dans le .db : {dept_en_clair}")
        print(f"     [constat] reponse en clair dans le .db      : {rep_en_clair}")
        # Ce test NE FAIT PAS echouer : il documente l'etat reel. Les compteurs
        # sont agreges (pas de vote individuel), mais le nom du departement et
        # les libelles de reponse sont stockes en clair. C'est acceptable SI
        # le modele de menace l'assume (le .db est deja protege par l'OS/SSH,
        # et l'agregation empeche de relier un vote a une personne).
        _ok("2. constat documente sur ce qui est en clair (voir ci-dessus)")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    _nettoyer()
    print("-" * 50)
    if ok:
        print("Chiffrement au repos : cle RSA protegee. Reste documente factuellement.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
