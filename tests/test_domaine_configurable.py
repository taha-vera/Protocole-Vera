#!/usr/bin/env python3
"""Le domaine du service est une donnee d'exploitation, pas une constante.

POURQUOI CE TEST EXISTE

Le domaine apparaissait en dur a deux endroits de `vera_consultation_api.py` :
l'origine autorisee par CORS, et la base des liens d'invitation. Changer de
domaine etait donc une modification de CODE -- donc un cycle de deploiement
complet, avec relecture, tests et redemarrage -- pour ce qui est une donnee de
configuration.

Ce n'est pas seulement inelegant. VERA tourne aujourd'hui sur un sous-domaine
DuckDNS : gratuit, sans engagement contractuel, sans recours en cas de reprise
du nom. Qui controle la zone DNS peut obtenir un certificat valide pour ce nom
et servir son propre JavaScript aux votants -- le scenario « operateur actif »
de LIMITS.md section 6, ouvert a un tiers qui n'a jamais ete choisi comme tel
(section 12bis). Le passage a un domaine detenu en propre est donc attendu, et
il ne doit pas dependre d'une relecture de code.

CE QUE CE TEST VERIFIE

1. Le domaine n'apparait qu'a UN endroit du code : la valeur par defaut de
   VERA_DOMAINE. Toute autre occurrence est une constante oubliee, qui
   survivrait a la migration et pointerait les votants vers l'ancien nom.
2. VERA_DOMAINE est bien lue depuis l'environnement.
3. Un domaine en HTTP est refuse. En clair, le message aveugle circule en clair
   et la garantie ne tient plus : mieux vaut un service qui ne demarre pas
   qu'un service qui protege moins que ce qu'il annonce.

Le test lit le fichier source : ni fastapi, ni opendp, ni le module Rust.
"""

import pathlib
import re
import sys

# tests/ etant un sous-repertoire, la racine du depot est le parent.
RACINE = pathlib.Path(__file__).resolve().parent.parent
API = RACINE / "vera_consultation_api.py"

echecs = []

source = API.read_text(encoding="utf-8")
code = "\n".join(
    ligne for ligne in source.splitlines()
    if not ligne.lstrip().startswith("#")
)

# --- 1. Une seule occurrence, celle du defaut ------------------------------

# Les domaines d'exemple des messages d'erreur sont exclus : ce sont des
# gabarits destines a l'exploitant, pas des adresses vers lesquelles le code
# enverrait quoi que ce soit. La convention est de les nommer "exemple".
occurrences = [
    ligne.strip() for ligne in code.splitlines()
    if re.search(r"https://[A-Za-z0-9.\-]+\.(org|fr|com|net|io|eu)", ligne)
    and "exemple" not in ligne
]
hors_defaut = [
    ligne for ligne in occurrences
    if "VERA_DOMAINE" not in ligne and "os.environ.get(" not in ligne
]

if len(occurrences) > 2:
    echecs.append(
        "le domaine apparait a plus d'un endroit du code :\n    "
        + "\n    ".join(occurrences))

if hors_defaut:
    echecs.append(
        "un domaine est ecrit en dur hors de la valeur par defaut de "
        "VERA_DOMAINE. Il survivrait a une migration et pointerait les votants "
        "vers l'ancien nom :\n    " + "\n    ".join(hors_defaut))

# --- 2. La variable est bien lue ------------------------------------------

if not re.search(r'VERA_DOMAINE\s*=\s*os\.environ\.get\(\s*\n?\s*"VERA_DOMAINE"',
                 code):
    echecs.append(
        "VERA_DOMAINE n'est pas lue depuis l'environnement : le domaine reste "
        "une constante de code.")

for usage in ("allow_origins=[VERA_DOMAINE]", 'f"{VERA_DOMAINE}/vote"'):
    if usage not in code:
        echecs.append(
            f"l'expression attendue {usage!r} est absente : soit l'origine "
            "CORS, soit la base des liens d'invitation n'utilise pas la "
            "variable.")

# --- 3. HTTP refuse --------------------------------------------------------

if 'startswith("https://")' not in code:
    echecs.append(
        "rien ne verifie que VERA_DOMAINE est une origine HTTPS. En clair, le "
        "message aveugle circule en clair et la garantie ne tient plus.")

# --- Verdict ---------------------------------------------------------------

if echecs:
    print("ECHEC : le domaine n'est pas correctement externalise.\n")
    for e in echecs:
        print("  - " + e)
    print("\nLe domaine doit vivre dans VERA_DOMAINE, definie dans l'unite "
          "systemd, et nulle part ailleurs dans le code.")
    sys.exit(1)

print("OK : le domaine vit dans VERA_DOMAINE, HTTPS exige, aucune constante "
      "residuelle.")
sys.exit(0)
