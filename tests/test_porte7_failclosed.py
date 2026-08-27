#!/usr/bin/env python3
"""Porte 7 : le fail-closed doit se declencher, pas seulement etre ecrit.

POURQUOI CE TEST EXISTE

`vera_consultation_api.py` porte un fail-closed explicite : « Le serveur refuse
de demarrer sans signature aveugle RSABSSA (Porte 7 fail-closed) ». Le README et
`requirements.txt` repetent l'affirmation.

Elle etait fausse. Constat d'un audit externe le 27/08/2026.

`vera_blind_sig/` est un REPERTOIRE du depot -- Cargo.toml, src/, pas de
__init__.py. Depuis la PEP 420, Python le resout comme paquet d'espace de noms :
`import vera_blind_sig` reussit sur un simple clone, sans qu'une seule ligne de
Rust ait ete compilee. Le module obtenu est vide, mais l'import ne leve rien.

Le try/except de l'API entourait donc un import qui reussit toujours, suivi d'un
`ouvrir_consultation()` qui ne touche jamais le module. L'`except` n'etait
jamais atteint : le serveur demarrait et se declarait disponible. L'echec ne
survenait qu'a la premiere generation de cle -- c'est-a-dire quand
l'organisateur genere ses liens, consultation deja lancee.

Ce n'etait pas exploitable pour desanonymiser : sans cle, aucun lien n'est emis,
donc aucun vote. Mais une garantie de securite affichee trois fois dans le depot
ne se declenchait pas, et c'est le genre d'ecart qui entame la credibilite de
tout le reste.
"""

import pathlib
import re
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
GESTIONNAIRE = RACINE / "vera_signature_manager.py"
API = RACINE / "vera_consultation_api.py"

FONCTIONS_ATTENDUES = ("generer_cles", "signer_aveugle")

echecs = []

source_gestionnaire = GESTIONNAIRE.read_text(encoding="utf-8", errors="replace")

for fonction in FONCTIONS_ATTENDUES:
    appelee = re.search(rf"vbs\.{re.escape(fonction)}\s*\(", source_gestionnaire)
    controlee = f'"{fonction}"' in source_gestionnaire or \
                f"'{fonction}'" in source_gestionnaire
    if appelee and not controlee:
        echecs.append(
            f"vera_signature_manager.py appelle vbs.{fonction}() sans verifier "
            "a l'import que le module l'expose. Sur un clone non compile, "
            "l'echec surviendrait au premier appel -- consultation deja "
            "ouverte -- au lieu du demarrage.")

if "callable(getattr(vbs" not in source_gestionnaire:
    echecs.append(
        "vera_signature_manager.py ne verifie pas que vera_blind_sig expose "
        "des fonctions appelables. L'import seul ne prouve rien : le "
        "repertoire du depot est resolu comme paquet d'espace de noms.")

source_api = API.read_text(encoding="utf-8", errors="replace")
for numero, ligne in enumerate(source_api.splitlines(), 1):
    if not ligne.lstrip().startswith("#"):
        continue
    minuscule = ligne.lower()
    if "continue de fonctionner" in minuscule and "sans ce module" in minuscule:
        contexte = "\n".join(source_api.splitlines()[max(0, numero - 12):numero + 4])
        if not any(m in contexte.lower() for m in
                   ("figurait ici", "datait", "retire", "inverse", "historique")):
            echecs.append(
                f"vera_consultation_api.py:{numero} affirme que le serveur "
                "fonctionne sans le module de signature aveugle, alors que le "
                "fail-closed dit l'inverse.\n    " + ligne.strip()[:110])

with tempfile.TemporaryDirectory(prefix="vera_porte7_") as faux:
    paquet = pathlib.Path(faux) / "vera_blind_sig"
    paquet.mkdir()
    (paquet / "__init__.py").write_text(
        "# Faux module : importable, mais n'expose aucune fonction native.\n",
        encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'" + faux + "'); "
         "sys.path.insert(1, r'" + str(RACINE) + "'); "
         "import vera_signature_manager"],
        capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        echecs.append(
            "avec un vera_blind_sig VIDE, l'import de vera_signature_manager "
            "reussit. C'est exactement le scenario du clone non compile : le "
            "serveur demarrerait, et n'echouerait qu'a la generation des "
            "liens.")
    elif "n'expose pas" not in (r.stderr or ""):
        echecs.append(
            "l'import echoue, mais le message n'explique pas que le module "
            "n'est pas compile. L'exploitant ne saura pas quoi corriger.\n"
            "    " + (r.stderr or "").strip()[-300:])

if echecs:
    print("ECHEC : le fail-closed de la Porte 7 ne ferme pas.\n")
    for e in echecs:
        print("  - " + e)
    print("\nUn import qui reussit ne prouve pas qu'un module fonctionne.")
    sys.exit(1)

print("OK : Porte 7 -- un vera_blind_sig non compile fait echouer le "
      "demarrage, avec un message exploitable.")
sys.exit(0)
