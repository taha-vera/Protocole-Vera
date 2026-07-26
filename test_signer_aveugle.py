#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test de la LOGIQUE de signature aveugle (brique 2 du refactor crypto).

NB (26/07) : ce fichier n'atteint PAS l'endpoint HTTP, contrairement a ce que
son ancien titre laissait croire -- aucun appel reseau ici. Il exerce la
primitive vera_blind_sig de bout en bout et le refus du rejeu de jeton, en
memoire. L'endpoint est couvert par chantier_crypto/test_brique7_v2.mjs, qui
frappe le vrai serveur. Un titre qui promet plus que le contenu fait croire a
une couverture inexistante."""
import tempfile, sys
from pathlib import Path
import vera_persistance as p
import vera_blind_sig as vbs

def main():
    t = tempfile.NamedTemporaryFile(suffix=".db", delete=False); t.close()
    p.DB_PATH = Path(t.name); p.initialiser()
    sk, pk = vbs.generer_cles()
    p.persister_jeton_autorisation("j1", "dept_test")
    msg = b'{"vote":"oui"}'
    bm, sec, rnd = vbs.aveugler_message(list(pk), list(msg))
    dept = p.consommer_jeton_autorisation("j1")
    sig_av = bytes(vbs.signer_aveugle(list(sk), list(bm)))
    rejeu = p.consommer_jeton_autorisation("j1")
    sig = bytes(vbs.finaliser_signature(list(pk), list(msg), list(bm), list(sec), list(sig_av), list(rnd)))
    valide = vbs.verifier_signature(list(pk), list(msg), list(sig), list(rnd))
    ok = (dept == "dept_test" and len(sig_av) == 256 and rejeu is None and valide)
    print("jeton->dept:", dept, "| sig_av:", len(sig_av), "| rejeu:", rejeu, "| valide:", valide)
    print("OK" if ok else "ECHEC")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
