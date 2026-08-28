#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parcours complet, par le CHEMIN HTTP REEL.

POURQUOI CE TEST EXISTE

Constat d'un audit externe le 27/08/2026, laisse de cote ce jour-la et repris
lors d'une relecture de notre propre travail : sur trente-trois tests, **aucun
n'appelait une route**. `vera_consultation_api.py` fait 1 800 lignes --
authentification, emission des jetons, signature aveugle, depot, anti-rejeu,
publication, cloture -- et toute regression y passait sans qu'un seul test ne
bronche.

Les tests existants exercent les modules SOUS l'API : le gestionnaire de
signature, la persistance, le budget. Aucun ne verifiait que les routes les
appellent correctement, ni qu'elles refusent ce qu'elles doivent refuser. Les
tests JavaScript de `chantier_crypto/` couvrent ce chemin, mais `run_tests.sh`
ne les lance pas -- il les mentionne en fin d'execution comme un rappel.

CE QUE CE TEST PARCOURT

Le cycle entier, en HTTP, sur une base jetable :

  1. connexion RH refusee sans identifiants, acceptee avec
  2. question, groupes, ouverture des depots
  3. generation des jetons d'autorisation
  4. cle publique du groupe
  5. aveuglement CLIENT (vera_blind_sig, comme le navigateur)
  6. signature aveugle par le serveur
  7. finalisation CLIENT
  8. depot du vote
  9. anti-rejeu : le meme K refuse en 409
 10. jeton deja consomme : refuse
 11. refus de publier sous K_MIN
 12. cloture : l'etat disparait

Le point 9 est le coeur : c'est l'invariant qui empeche un votant de compter
deux fois, et il n'etait verifie par aucun appel HTTP.

CE QU'IL EXIGE

Le module Rust compile -- il fait l'aveuglement cote client, comme le
navigateur. Sans lui, le test s'arrete avec le message qui dit quoi compiler,
comme les autres tests de la chaine cryptographique.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# Base jetable OBLIGATOIRE : vera_persistance refuse la production, mais on
# fixe la variable ici pour que le test soit lancable seul.
if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db",
                                                 prefix="vera_http_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS",
                      os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)

if not callable(getattr(vbs, "generer_cles", None)):
    print("IGNORE : vera_blind_sig est importable mais n'expose pas "
          "generer_cles() -- le module Rust n'est pas compile.")
    print("  cd vera_blind_sig && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 "
          "maturin develop --release")
    raise SystemExit(2)

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible (httpx manquant ?).")
    print("  pip install httpx")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_du_parcours_http"
os.environ["VERA_ADMIN_USER"] = "rh_parcours"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402

GROUPE = "ParcoursHTTP"
echecs = []


def _ok(message):
    print(f"  OK  {message}")


def verifier(condition, message, detail=""):
    if condition:
        _ok(message)
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")

# --- 1. Authentification --------------------------------------------------

r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_parcours", "mot_de_passe": "faux"})
verifier(r.status_code == 401,
         "1a. connexion refusee avec un mauvais mot de passe",
         f"recu {r.status_code}")

r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_parcours", "mot_de_passe": MDP})
verifier(r.status_code == 200, "1b. connexion acceptee",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 2. Une route RH refuse un appel non authentifie ---------------------

sans_session = TestClient(api.app, base_url="https://testserver")
r = sans_session.post("/api/rh/question",
                      json={"intitule": "Question sans session, doit echouer."})
verifier(r.status_code in (401, 403),
         "2. route RH refusee sans session",
         f"recu {r.status_code} -- un appelant anonyme pilotait la consultation")

# --- 3. Preparation de la consultation ------------------------------------

r = client.post("/api/rh/question",
                json={"intitule": "Estimez-vous votre charge soutenable ?"})
verifier(r.status_code == 200, "3a. question definie",
         f"recu {r.status_code} : {r.text[:150]}")

r = client.post("/api/rh/declarer_groupes", json={"groupes": [GROUPE]})
verifier(r.status_code == 200, "3b. groupes declares",
         f"recu {r.status_code} : {r.text[:150]}")

# L'API refuse une ouverture immediate : elle exige que l'emission et les
# depots se separent dans le temps (LIMITS.md section 9).
r = client.post("/api/rh/ouverture",
                json={"ouverture_unix": time.time() + 2})
verifier(r.status_code == 200, "3c. ouverture des depots fixee",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 4. Emission des jetons ----------------------------------------------

r = client.post("/api/rh/generer_autorisations",
                json={"departement": GROUPE, "quantite": 3})
verifier(r.status_code == 200, "4a. jetons generes",
         f"recu {r.status_code} : {r.text[:200]}")

jetons = []
if r.status_code == 200:
    corps = r.json()
    jetons = [a["jeton"] for a in corps.get("autorisations", [])]
    verifier(len(jetons) == 3, "4b. trois jetons renvoyes",
             f"recu {len(jetons)}")
    verifier("empreinte_cle" in corps,
             "4c. empreinte de cle renvoyee, pour le lien du votant")

# --- 5. Le parcours du votant, en HTTP -----------------------------------

if jetons:
    time.sleep(2.2)          # attendre l'ouverture des depots

    r = client.get("/api/cle_publique", params={"departement": GROUPE})
    verifier(r.status_code == 200, "5a. cle publique obtenue",
             f"recu {r.status_code} : {r.text[:150]}")

    if r.status_code == 200:
        pub = bytes.fromhex(r.json()["cle_publique_hex"])

        # Aveuglement CLIENT -- ce que fait le navigateur du votant.
        message = os.urandom(32)
        aveugle, secret, randomizer = vbs.aveugler_message(
            list(pub), list(message))

        r = client.post("/api/signer_aveugle", json={
            "jeton_autorisation": jetons[0],
            "message_aveugle_hex": bytes(aveugle).hex()})
        verifier(r.status_code == 200, "5b. signature aveugle obtenue",
                 f"recu {r.status_code} : {r.text[:200]}")

        if r.status_code == 200:
            sig_aveugle = bytes.fromhex(r.json()["signature_aveugle_hex"])
            # Signature reelle, relue dans vera_blind_sig/src/lib.rs et dans
            # tests/test_signer_aveugle.py : SIX arguments, dans cet ordre.
            # Une premiere version en passait quatre, devines -- le test
            # echouait sur un TypeError apres avoir franchi onze etapes.
            finale = bytes(vbs.finaliser_signature(
                list(pub), list(message), list(aveugle), list(secret),
                list(sig_aveugle), list(randomizer)))

            corps_vote = {
                "K_hex": bytes(message).hex(),
                "randomizer_hex": bytes(randomizer).hex(),
                "signature_hex": finale.hex(),
                "reponse": "oui",
                "departement": GROUPE,
                "pad": "x" * 100,
            }

            r = client.post("/api/repondre", json=corps_vote)
            verifier(r.status_code == 200, "5c. vote depose",
                     f"recu {r.status_code} : {r.text[:200]}")

            # --- 6. ANTI-REJEU : le coeur de ce test ---------------------
            r = client.post("/api/repondre", json=corps_vote)
            verifier(r.status_code == 409,
                     "6. rejeu du meme K refuse en 409",
                     f"recu {r.status_code} -- un votant comptait DEUX fois")

        # --- 7. Le jeton consomme ne resigne pas un AUTRE message -------
        autre = os.urandom(32)
        aveugle2, _, _ = vbs.aveugler_message(list(pub), list(autre))
        r = client.post("/api/signer_aveugle", json={
            "jeton_autorisation": jetons[0],
            "message_aveugle_hex": bytes(aveugle2).hex()})
        verifier(r.status_code >= 400,
                 "7. jeton deja consomme : second message refuse",
                 f"recu {r.status_code} -- un jeton signait deux credentials")

# --- 8. Refus de publier sous le seuil -----------------------------------

r = client.post("/api/rh/publier", json={"departement": GROUPE})
verifier(r.status_code >= 400,
         "8. publication refusee sous K_MIN",
         f"recu {r.status_code} -- un resultat publie sur un vote")

# --- 9. Endpoints publics ------------------------------------------------

r = client.get("/api/engagement_cles")
verifier(r.status_code == 200 and "K_MIN" in r.text or r.status_code == 200,
         "9a. engagement des cles public et lisible",
         f"recu {r.status_code}")

r = client.get("/vote")
verifier(r.status_code == 200 and "<html" in r.text.lower(),
         "9b. page de vote servie",
         f"recu {r.status_code}")

# --- 10. Cloture : l'etat disparait --------------------------------------

r = client.post("/api/rh/cloturer", json={})
verifier(r.status_code == 200, "10a. cloture acceptee",
         f"recu {r.status_code} : {r.text[:200]}")

if r.status_code == 200:
    r = client.get("/api/rh/etat_departements")
    reste = r.json() if r.status_code == 200 else {}
    verifier(GROUPE not in str(reste),
             "10b. apres cloture, le groupe a disparu de l'etat",
             f"reste : {str(reste)[:150]}")

# --- Verdict --------------------------------------------------------------

print()
if echecs:
    print(f"ECHEC : {len(echecs)} etape(s) du parcours HTTP.\n")
    for e in echecs:
        print("  - " + e)
    print("\nCe test est le seul a exercer les routes. Un echec ici porte sur "
          "le chemin\nque le votant emprunte reellement.")
    sys.exit(1)

print("OK : parcours HTTP complet -- authentification, emission, signature "
      "aveugle,\n     depot, anti-rejeu, refus sous seuil, cloture.")
sys.exit(0)
