#!/usr/bin/env python3
"""Le repli en clair VERA_ADMIN_PASS n'existe plus.

POURQUOI CE TEST EXISTE

Jusqu'au 23/08/2026, l'amorcage creait le compte d'administration depuis
VERA_ADMIN_PASS quand VERA_ADMIN_HASH etait absente. Le mot de passe vivait
alors en clair dans l'unite systemd, lisible par `systemctl cat` et recopie dans
toute sauvegarde de configuration. C'est le canal par lequel des secrets ont
fuite le 31/07/2026.

Le repli a survecu longtemps pour une raison mecanique : run_tests.sh l'exportait,
donc toute la suite l'empruntait, et le retirer cassait les tests. Ce test ferme
la boucle dans l'autre sens -- il echoue si le repli revient.

QUATRE VERIFICATIONS

1. Avec VERA_ADMIN_PASS seule, l'amorcage doit LEVER une erreur. Le refus est
   deliberement franc : ignorer la variable en silence demarrerait un service
   sans aucun compte d'administration, ce que l'organisateur ne decouvrirait
   qu'au moment de se connecter, consultation ouverte.
2. Le message doit nommer la variable, sans quoi l'exploitant ne saura pas quoi
   corriger.
3. Avec VERA_ADMIN_HASH, le compte doit etre cree et le mot de passe verifie --
   la voie de production ne doit pas etre cassee par le retrait.
4. Structurellement, plus aucune ligne ne cree de compte depuis un mot de passe
   d'environnement, ni dans l'API ni dans le module d'authentification.

Le test n'importe que vera_admin_auth : ni fastapi, ni opendp, ni le module
Rust. Il tourne donc partout, y compris sur un poste sans environnement complet.
"""

import os
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

import vera_admin_auth as auth  # noqa: E402

echecs = []


def poser(**variables):
    """Fixe l'environnement d'amorcage, en retirant ce qui n'est pas donne."""
    for cle in ("VERA_ADMIN_USER", "VERA_ADMIN_HASH", "VERA_ADMIN_PASS"):
        os.environ.pop(cle, None)
    for cle, valeur in variables.items():
        os.environ[cle] = valeur


# --- 1 et 2. Le repli doit faire echouer l'amorcage ------------------------

poser(VERA_ADMIN_USER="rh_test", VERA_ADMIN_PASS="mdp_de_test")
try:
    auth.amorcer_compte_principal()
    echecs.append(
        "avec VERA_ADMIN_PASS seule, l'amorcage reussit. Il doit lever une "
        "erreur : soit le repli est revenu, soit le service demarrerait sans "
        "compte d'administration sans le dire.")
except RuntimeError as e:
    if "VERA_ADMIN_PASS" not in str(e):
        echecs.append(
            "l'amorcage refuse mais le message ne nomme pas VERA_ADMIN_PASS : "
            "l'exploitant ne saura pas quoi corriger.\n    message : " + str(e))

if "rh_test" in auth._comptes_rh:
    echecs.append(
        "un compte a ete cree malgre le refus. L'echec doit etre total.")

# --- 3. La voie de production reste intacte --------------------------------

empreinte = auth.generer_empreinte("mdp_de_test")
if "$" not in empreinte:
    echecs.append("generer_empreinte() ne produit pas une empreinte 'sel$hash'.")

poser(VERA_ADMIN_USER="rh_prod", VERA_ADMIN_HASH=empreinte)
try:
    cree = auth.amorcer_compte_principal()
    if cree != "rh_prod":
        echecs.append(
            f"avec VERA_ADMIN_HASH, l'amorcage renvoie {cree!r} au lieu de "
            "'rh_prod'.")
    if not auth.verifier_identifiants("rh_prod", "mdp_de_test"):
        echecs.append(
            "le compte cree depuis l'empreinte ne reconnait pas son mot de "
            "passe : la voie de production est cassee.")
    if auth.verifier_identifiants("rh_prod", "mauvais_mot_de_passe"):
        echecs.append(
            "le compte accepte un mot de passe errone.")
except RuntimeError as e:
    echecs.append(
        "avec VERA_ADMIN_HASH, l'amorcage echoue. La voie de production est "
        "cassee.\n    message : " + str(e))

# --- 4. Structurelle -------------------------------------------------------

for nom in ("vera_consultation_api.py", "vera_admin_auth.py"):
    source = (RACINE / nom).read_text(encoding="utf-8")
    code = "\n".join(
        ligne for ligne in source.splitlines()
        if not ligne.lstrip().startswith("#")
    )
    if re.search(r"creer_compte\s*\(\s*[^)]*os\.environ", code) or \
       re.search(r"creer_compte\s*\(\s*identifiant\s*,\s*os\.environ", code):
        echecs.append(
            f"{nom} cree un compte depuis une variable d'environnement en "
            "clair. Seul creer_compte_depuis_empreinte() est admis a "
            "l'amorcage.")

api = (RACINE / "vera_consultation_api.py").read_text(encoding="utf-8")
lignes_actives = [
    l for l in api.splitlines()
    if "VERA_ADMIN_PASS" in l and not l.lstrip().startswith("#")
]
if lignes_actives:
    echecs.append(
        "vera_consultation_api.py mentionne VERA_ADMIN_PASS hors commentaire. "
        "L'amorcage doit passer par vera_admin_auth.amorcer_compte_principal(), "
        "seul endroit ou cette variable est encore nommee -- pour la refuser.\n"
        "    " + "\n    ".join(lignes_actives))

# --- Verdict ---------------------------------------------------------------

poser()

if echecs:
    print("ECHEC : le repli en clair VERA_ADMIN_PASS n'est pas correctement "
          "retire.\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)

print("OK : VERA_ADMIN_PASS fait echouer l'amorcage, VERA_ADMIN_HASH cree le "
      "compte.")
sys.exit(0)
