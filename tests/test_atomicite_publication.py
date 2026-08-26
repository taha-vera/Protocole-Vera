#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_atomicite_publication.py -- Verifie que budget et resultat sont persistes
de facon ATOMIQUE (audit Fable 5, point 2). Sans atomicite, un crash entre les
deux ecritures laissait un departement verrouille a jamais (deja_publie=True
mais resultat introuvable). Base jetable, prod jamais touchee.
"""
import os, sys, tempfile
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_test_atomicite"
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
    print("Test atomicite budget<->resultat (base jetable)")
    print("-" * 52)
    ok = True

    # 1. La publication atomique ecrit budget ET resultat ensemble.
    try:
        p.persister_publication_atomique("A", 0.5, 1, {"oui": 45, "non": 30})
        budget = p.charger_budget_epsilon()
        resultat = p.charger_resultat_publie("A")
        if budget.get("A", {}).get("nombre_publications") != 1:
            raise Echec("budget non persiste")
        if resultat != {"oui": 45, "non": 30}:
            raise Echec("resultat non persiste")
        _ok("1. budget + resultat persistes ensemble")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. COHERENCE : jamais "budget marque publie" sans resultat.
    #    On verifie l'invariant qui evite le lockout : si nb_publications>0,
    #    alors le resultat DOIT exister.
    try:
        budget = p.charger_budget_epsilon()
        for dept, etat in budget.items():
            if etat["nombre_publications"] > 0 and p.charger_resultat_publie(dept) is None:
                raise Echec(f"INCOHERENCE: {dept} publie mais resultat absent (lockout)")
        _ok("2. invariant coherent: tout departement publie a son resultat")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. VRAIE injection de panne ENTRE les deux ecritures.
    #    La version precedente se contentait de cinq appels reussis en boucle
    #    puis verifiait que les deux ecritures etaient la : vrai avec un commit
    #    unique COMME avec deux commits separes. Le test ne pouvait donc pas
    #    detecter la perte d'atomicite -- verifie par mutation le 25/07, il
    #    restait vert avec deux commits. Elle sautait meme la verification si
    #    le budget n'etait pas ecrit du tout (condition == 1).
    #    Ici on force une exception APRES l'ecriture du budget et AVANT celle
    #    du resultat, puis on verifie qu'AUCUNE des deux n'a ete committee.
    try:
        appels = {"n": 0}
        vraie_conn = p._conn

        # sqlite3.Connection.execute est en lecture seule (objet C) : on
        # enveloppe la connexion entiere dans un proxy qui delegue tout sauf
        # execute, ou l'on injecte la panne.
        class ConnexionQuiCasse:
            def __init__(self, conn):
                self._c = conn

            def execute(self, sql, *args, **kwargs):
                resultat = self._c.execute(sql, *args, **kwargs)
                if "resultats_publies" in sql:
                    appels["n"] += 1
                    raise RuntimeError("PANNE SIMULEE entre budget et resultat")
                return resultat

            def __getattr__(self, nom):
                return getattr(self._c, nom)

        p._conn = ConnexionQuiCasse(vraie_conn)
        try:
            p.persister_publication_atomique("DPanne", 0.5, 1, {"oui": 1, "non": 0})
            raise Echec("la panne simulee n'a pas interrompu l'ecriture")
        except RuntimeError:
            pass
        finally:
            p._conn = vraie_conn
            p._conn.rollback()

        if appels["n"] == 0:
            raise Echec("la panne n'a jamais ete declenchee -- test invalide")

        budget = p.charger_budget_epsilon()
        resultat = p.charger_resultat_publie("DPanne")
        budget_ecrit = "DPanne" in budget
        if budget_ecrit or resultat is not None:
            raise Echec(
                f"ETAT PARTIEL apres panne : budget_ecrit={budget_ecrit}, "
                f"resultat={resultat is not None} -- l'atomicite est perdue")
        _ok("3. panne entre les deux ecritures : AUCUNE des deux persistee")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    _nettoyer()
    print("-" * 52)
    if ok:
        print("ATOMICITE OK : plus d'etat 'publie sans resultat' possible.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
