#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ordre des controles dans /api/rh/generer_autorisations.

POURQUOI CE TEST EXISTE

Constat d'un audit externe le 03/09/2026, et c'est le defaut le plus couteux
trouve sur ce projet -- non parce qu'il casse l'anonymat, mais parce qu'il
detruit une consultation entiere sur une faute de frappe.

CE QUI SE PASSAIT

`generer_autorisations` appelait `gestionnaire_signature.cle_publique(groupe)`
AVANT de verifier que le groupe figurait dans la liste declaree. Or cette
methode est CREATRICE si la cle est absente, et elle la PERSISTE.

Le 409 arrivait donc trop tard. La cle du groupe fautif existait deja, et
l'empreinte de l'ENSEMBLE des cles -- celle inscrite dans chaque lien deja
distribue -- avait change.

Une faute de frappe suffisait : « Ateliers » pour « Atelier », une majuscule,
un pluriel. Le motif de validation du champ accepte tout nom bien forme, il ne
verifie aucune appartenance. Le RH voyait un message d'erreur clair et croyait
qu'il ne s'etait rien passe.

Tous les votants, TOUS GROUPES CONFONDUS, recevaient ensuite « la configuration
du serveur ne correspond pas a ce lien. Vote refuse par securite ». Et l'etat
etait irrecuperable : aucune route ne retire une cle, seule la cloture les
detruit toutes. Il fallait recommencer la consultation et redistribuer les liens.

Le commentaire du code decrivait exactement ce defaut -- il expliquait pourquoi
le controle existe. Il ne disait pas qu'il s'executait trop tard.

CE QUE CE TEST VERIFIE

1. Dans `generer_autorisations`, le chargement des groupes declares precede
   l'appel a `cle_publique()`. C'est un test d'ORDRE : le meme code, dans
   l'autre sens, est vulnerable.
2. Les deux `raise HTTPException(409)` du controle precedent eux aussi cet
   appel -- sans quoi le controle existerait sans bloquer.
3. Aucun endpoint PUBLIC n'appelle la variante creatrice. Un appelant anonyme
   qui creerait une cle produirait le meme desastre sans authentification.
"""

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
API = RACINE / "vera_consultation_api.py"

echecs = []


def _ok(message):
    print(f"  OK  {message}")


source = API.read_text(encoding="utf-8", errors="replace")
lignes = source.splitlines()

# --- Delimiter la fonction ------------------------------------------------

debut = None
for i, l in enumerate(lignes):
    if l.startswith("def generer_autorisations("):
        debut = i
        break

if debut is None:
    echecs.append(
        "generer_autorisations introuvable : ce test cible une fonction qui "
        "n'existe plus sous ce nom. Le motif est perime, pas le code.")
    fin = 0
else:
    fin = len(lignes)
    for j in range(debut + 1, len(lignes)):
        if lignes[j].startswith(("def ", "@app.")):
            fin = j
            break

corps = lignes[debut:fin] if debut is not None else []

# --- 1 et 2. L'ordre ------------------------------------------------------

if corps:
    def _rang(motif):
        for k, l in enumerate(corps):
            if l.lstrip().startswith("#"):
                continue
            if re.search(motif, l):
                return k
        return None

    creation = _rang(r"gestionnaire_signature\.cle_publique\s*\(")
    controle = _rang(r"charger_groupes_declares\s*\(")

    if creation is None:
        _ok("1. la fonction n'appelle plus la variante creatrice")
    elif controle is None:
        echecs.append(
            "generer_autorisations appelle cle_publique() sans jamais charger "
            "la liste des groupes declares. Un groupe mal orthographie "
            "creerait une cle et invaliderait tous les liens distribues.")
    elif controle > creation:
        echecs.append(
            f"l'ordre est inverse : cle_publique() est appelee ligne "
            f"{debut + creation + 1}, le controle des groupes declares ligne "
            f"{debut + controle + 1}.\n      cle_publique() est CREATRICE et "
            "PERSISTE. Le 409 arrive apres que le mal est fait : l'empreinte "
            "de l'ensemble\n      des cles a change, et tous les liens deja "
            "distribues sont invalides.")
    else:
        _ok("1. le controle des groupes declares precede la creation de cle")

    # Les refus doivent eux aussi preceder la creation.
    if creation is not None:
        refus = [k for k, l in enumerate(corps)
                 if "status_code=409" in l and not l.lstrip().startswith("#")]
        tardifs = [k for k in refus if k > creation]
        if tardifs:
            echecs.append(
                f"un refus 409 est leve APRES la creation de cle (ligne "
                f"{debut + tardifs[0] + 1}). Le controle existe mais ne bloque "
                "plus rien.")
        elif refus:
            _ok("2. les refus 409 precedent la creation de cle")

# --- 3. Aucun endpoint public n'appelle la variante creatrice -------------

publics = []
courant = None
for i, l in enumerate(lignes):
    m = re.match(r'@app\.(get|post)\("([^"]+)"', l.strip())
    if m:
        courant = m.group(2)
    if courant and re.search(r"gestionnaire_signature\.cle_publique\s*\(", l) \
            and not l.lstrip().startswith("#"):
        if not courant.startswith("/api/rh/"):
            publics.append((courant, i + 1))
        courant = None

if publics:
    for route, numero in publics:
        echecs.append(
            f"l'endpoint PUBLIC {route} appelle la variante CREATRICE de "
            f"cle_publique (ligne {numero}).\n      Un appelant anonyme "
            "creerait une cle et invaliderait tous les liens distribues. "
            "Utiliser cle_publique_si_existe.")
else:
    _ok("3. aucun endpoint public n'appelle la variante creatrice")

# --- Verdict --------------------------------------------------------------

print()
if echecs:
    print("ECHEC : une cle peut etre creee avant le controle qui doit "
          "l'empecher.\n")
    for e in echecs:
        print("  - " + e)
    print("\nUne faute de frappe du RH suffirait alors a invalider tous les "
          "liens\ndistribues, sans recuperation possible hors cloture.")
    sys.exit(1)

print("OK : le controle des groupes declares precede toute creation de cle.")
sys.exit(0)
