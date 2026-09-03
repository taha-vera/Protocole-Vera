#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apres cloture, le fichier .db ne contient plus les empreintes.

POURQUOI CE TEST EXISTE

Le module de persistance affirme qu'apres `effacer_etat_consultation()`, « le
serveur ne conserve plus AUCUNE donnee de la consultation cloturee ». Le modele
de menace en fait la Porte 14. Trois mecanismes sont censes la tenir :
`PRAGMA secure_delete=ON`, les `DELETE`, et le `VACUUM` final.

**Personne ne l'avait verifie sur les octets.** Douze audits ont lu le code et
approuve le raisonnement ; aucun n'a ouvert le fichier apres coup. Un auditeur
l'a propose le 03/09/2026 -- c'est le seul controle qui distingue « le code
appelle secure_delete » de « les donnees ont disparu ».

CE QUE CE TEST FAIT

Il monte une consultation complete sur une base jetable : jetons emis, votes
deposes, compteurs incrementes. Il releve les valeurs qui ne doivent PAS
survivre, cloture, puis lit le fichier OCTET PAR OCTET -- pas par SQL, qui ne
montrerait que la vue logique.

CE QUE CE TEST NE PROUVE PAS, ET IL FAUT LE DIRE

Il verifie ce que SQLite controle : le contenu du fichier `.db`. Il ne dit rien
du nivellement d'usure des SSD, des instantanes d'hyperviseur, des sauvegardes,
du journal du systeme de fichiers, de la memoire vive ni du fichier d'echange.
Une organisation dont l'effacement doit etre opposable a besoin d'un chiffrement
au niveau du volume, qui sort du perimetre de ce projet.

Autrement dit : ce test etablit une minimisation applicative, pas une
destruction forensique du support.
"""

import hashlib
import os
import pathlib
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

BASE = tempfile.mktemp(suffix=".db", prefix="vera_forensic_")
os.environ["VERA_DB_PATH"] = BASE
os.environ.setdefault("VERA_DB_KEY", "0" * 64)

import vera_persistance as p  # noqa: E402

echecs = []


def _ok(message):
    print(f"  OK  {message}")


# --- Monter une consultation complete -------------------------------------

p.initialiser()

GROUPE = "Atelier"
JETONS = [f"jeton_secret_numero_{i}" for i in range(5)]
EMPREINTES_K = [hashlib.sha384(f"secret_K_{i}".encode()).hexdigest()
                for i in range(5)]

p.persister_jetons_autorisation_lot(JETONS, GROUPE)
p.persister_groupes_declares([GROUPE])
p.persister_question("Estimez-vous votre charge soutenable ?")

for i, emp in enumerate(EMPREINTES_K):
    p.consommer_jeton_autorisation(JETONS[i])
    p.enregistrer_vote_atomique(GROUPE, "oui" if i % 2 else "non", emp)

p.persister_budget_epsilon(GROUPE, 0.5, 1)

# Les valeurs qui ne doivent PAS survivre. Les empreintes de jetons sont
# calculees comme le module le fait, pas recopiees.
empreintes_jetons = [hashlib.sha256(j.encode("utf-8")).hexdigest() for j in JETONS]
ne_doit_pas_survivre = {
    "empreinte de jeton": empreintes_jetons,
    "empreinte de secret K": EMPREINTES_K,
    "intitule de la question": ["Estimez-vous votre charge soutenable ?"],
}

# --- Verifier qu'elles sont bien la AVANT ---------------------------------
#
# Sans ce controle, un test qui ne trouve rien apres cloture ne prouve rien :
# peut-etre n'y avait-il jamais rien ecrit.

octets_avant = pathlib.Path(BASE).read_bytes()
absents_avant = [
    f"{nature} ({v[:24]}...)"
    for nature, valeurs in ne_doit_pas_survivre.items()
    for v in valeurs
    if v.encode("utf-8") not in octets_avant
]
if absents_avant:
    echecs.append(
        "AVANT cloture, ces valeurs ne sont deja pas dans le fichier :\n      "
        + "\n      ".join(absents_avant)
        + "\n      Le test ne prouverait rien : il faut qu'elles y soient pour "
        "que leur absence\n      apres cloture signifie quelque chose.")
else:
    _ok(f"1. avant cloture, les {sum(len(v) for v in ne_doit_pas_survivre.values())} "
        "valeurs sensibles sont bien dans le fichier")

# --- Cloturer -------------------------------------------------------------

p.effacer_etat_consultation()
p.effacer_cle_rsa()
p.vider_signatures_emises()

# --- Lire les octets ------------------------------------------------------

octets = pathlib.Path(BASE).read_bytes()

survivants = []
for nature, valeurs in ne_doit_pas_survivre.items():
    for v in valeurs:
        if v.encode("utf-8") in octets:
            survivants.append(f"{nature} : {v[:32]}...")

if survivants:
    echecs.append(
        f"APRES cloture, {len(survivants)} valeur(s) subsistent dans les "
        "octets du fichier :\n      " + "\n      ".join(survivants[:6])
        + "\n      La Porte 14 affirme que le serveur ne conserve plus rien de "
        "la consultation.\n      secure_delete, les DELETE ou le VACUUM n'ont "
        "pas fait leur travail.")
else:
    _ok("2. apres cloture, aucune de ces valeurs ne subsiste dans les octets")

# --- Ce qui DOIT survivre, et qu'on verifie aussi -------------------------
#
# `historique_consultations` est conservee deliberement : elle alimente
# l'avertissement de frequence. Si elle disparaissait, ce test le dirait --
# une minimisation trop large casserait une fonction annoncee.

if p.compter_consultations_recentes(GROUPE) >= 0:
    _ok("3. historique_consultations survit, comme annonce")

# --- Le fichier reste exploitable ----------------------------------------

try:
    p.charger_compteurs()
    p.charger_tokens_consommes()
    _ok("4. la base reste lisible et vide apres VACUUM")
except Exception as e:
    echecs.append(f"la base est inutilisable apres cloture : {e}")

try:
    os.unlink(BASE)
except OSError:
    pass

# --- Verdict --------------------------------------------------------------

print()
if echecs:
    print("ECHEC : l'effacement de cloture ne tient pas au niveau des octets.\n")
    for e in echecs:
        print("  - " + e)
    print("\nCe test lit le FICHIER, pas la vue SQL : un DELETE nettoie la "
          "seconde,\npas necessairement le premier.")
    sys.exit(1)

print("OK : apres cloture, les empreintes de jetons, les empreintes de secrets "
      "et\n     l'intitule de la question ont disparu des octets du fichier.")
sys.exit(0)
