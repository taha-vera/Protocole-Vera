#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_jetons_autorisation.py -- Registre 1 du refactor crypto (jetons
d'autorisation / credentials d'emission). Verifie surtout l'ATOMICITE de la
consommation : un jeton ne peut etre consomme qu'UNE fois (anti-double-vote a
la source). Base jetable, prod jamais touchee.
"""
import os, sys, tempfile, threading
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_test_jetons"
import vera_persistance as p

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
p.DB_PATH = Path(_tmp.name); p.initialiser()

class Echec(Exception): pass
def _ok(n): print(f"OK   {n}")
def _nettoyer():
    for s in ("", "-wal", "-shm"):
        try: Path(str(_tmp.name)+s).unlink()
        except FileNotFoundError: pass

def main():
    print("Test registre 1 - jetons d'autorisation (base jetable)")
    print("-" * 54)
    ok = True

    # 1. Creer un jeton et le charger.
    try:
        p.persister_jeton_autorisation("jeton_A", "dept1")
        etat = p.charger_jetons_autorisation()
        # La base ne stocke QUE des empreintes SHA-256 (correctif Porte A du
        # 24/07 : un jeton en clair y etait rejouable par un lecteur de base
        # contre /api/signer_aveugle). charger_jetons_autorisation renvoie donc
        # un dict indexe par empreinte. Chercher "jeton_A" en clair rendait ce
        # test ROUGE sur du code sain et VERT si on retirait le hachage --
        # il incitait a reintroduire la faille.
        emp_A = p._empreinte_jeton("jeton_A")
        if etat.get(emp_A) != ("dept1", False):
            raise Echec(f"jeton_A mal enregistre: {etat.get(emp_A)}")
        _ok("1. jeton cree et disponible (utilise=False)")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Consommer le jeton -> renvoie le departement.
    try:
        dept = p.consommer_jeton_autorisation("jeton_A")
        if dept != "dept1":
            raise Echec(f"consommation devrait renvoyer dept1, a renvoye {dept}")
        _ok("2. premiere consommation OK -> renvoie le departement")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. CRUCIAL : reconsommer le meme jeton -> None (deja utilise).
    try:
        dept2 = p.consommer_jeton_autorisation("jeton_A")
        if dept2 is not None:
            raise Echec(f"deuxieme consommation devrait renvoyer None, a renvoye {dept2}")
        _ok("3. deuxieme consommation refusee (None) -- anti-double-vote")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. Jeton inconnu -> None.
    try:
        if p.consommer_jeton_autorisation("jeton_inexistant") is not None:
            raise Echec("jeton inconnu devrait renvoyer None")
        _ok("4. jeton inconnu refuse (None)")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. ATOMICITE SOUS CONCURRENCE : 20 threads tentent de consommer le meme
    #    jeton. UN SEUL doit reussir (le reste None). C'est le test qui prouve
    #    qu'un double vote par requetes simultanees est impossible.
    try:
        p.persister_jeton_autorisation("jeton_concurrent", "dept2")
        resultats = []
        verrou_res = threading.Lock()
        def tenter():
            r = p.consommer_jeton_autorisation("jeton_concurrent")
            with verrou_res:
                resultats.append(r)
        threads = [threading.Thread(target=tenter) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        succes = [r for r in resultats if r is not None]
        if len(succes) != 1:
            raise Echec(f"exactement 1 thread devrait reussir, {len(succes)} ont reussi")
        _ok("5. 20 threads concurrents -> 1 seul consomme (atomicite prouvee)")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    # 6. Persistance : l'etat utilise survit a un rechargement.
    try:
        # ASSERTION ANTI-REGRESSION (Porte A) : le jeton en CLAIR ne doit
        # exister nulle part en base. Sans elle, ce test passe au vert meme si
        # _empreinte_jeton est neutralise -- verifie par mutation le 25/07 :
        # avec le hachage retire, le test restait a exit 0. Il verifiait la
        # coherence ecriture/lecture, pas le hachage lui-meme.
        rows = p._conn.execute("SELECT jeton FROM jetons_autorisation").fetchall()
        for (valeur,) in rows:
            if valeur == "jeton_A":
                raise Echec("le jeton est stocke EN CLAIR en base -- regression Porte A")
            if not (len(valeur) == 64 and all(ch in "0123456789abcdef" for ch in valeur)):
                raise Echec(f"valeur stockee non conforme a un SHA-256 : {valeur[:20]}")
        _ok("6a. jetons stockes uniquement sous forme d'empreinte SHA-256")

        etat = p.charger_jetons_autorisation()
        if etat.get(p._empreinte_jeton("jeton_A")) != ("dept1", True):
            raise Echec(f"jeton_A devrait etre utilise=True apres rechargement: {etat.get('jeton_A')}")
        _ok("6. etat 'utilise' persiste (survit au rechargement)")
    except Echec as e:
        print(f"FAIL 6. {e}"); ok = False

    _nettoyer()
    print("-" * 54)
    if ok:
        print("REGISTRE 1 OK : jetons d'autorisation atomiques, anti-double-vote prouve.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
