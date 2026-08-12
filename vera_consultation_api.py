#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_consultation_api.py — Serveur complet : vote public (sans auth) +
interface RH protegee par authentification (generation de tokens,
consultation des resultats agreges).

Coherent avec ATTRIBUTION_FLOW.md : le compte RH est l'autorite
d'attribution. Il connait departement <-> quantite de tokens demandes,
jamais l'identite des votants individuels cote serveur -- l'envoi des
liens reste sous la responsabilite de la personne RH elle-meme, en dehors
de ce systeme.
"""

import hmac
import re
import secrets
from urllib.parse import quote
import threading
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Cookie, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import vera_admin_auth as auth
import vera_blind_sig as vbs
from vera_epsilon_budget import BudgetEpsilonParDepartement
from vera_dp_noise import appliquer_bruit_dp, publier_histogramme_dp

app = FastAPI(title="VERA Consultation")

# --------------------------------------------------------------------------
# GARDE CRITIQUE : un seul worker autorise.
# L'etat (budget epsilon, verrou, registre tokens) est en memoire de
# processus et protege par un threading.Lock, qui ne synchronise PAS entre
# plusieurs processus. Avec 2+ workers uvicorn, deux requetes paralleles
# peuvent chacune consommer le budget epsilon du meme departement -> la
# composition sequentielle DP est cassee silencieusement (epsilon reel
# double). On refuse donc de demarrer si plus d'un worker est detecte.
# --------------------------------------------------------------------------
def _verifier_worker_unique():
    import os, sys
    # Deux sources a verifier, et la premiere ne suffit PAS :
    # - WEB_CONCURRENCY est une convention GUNICORN. uvicorn --workers N en
    #   ligne de commande ne pose PAS cette variable. Le commentaire precedent
    #   affirmait le contraire : la garde ne se declenchait donc pas sur un
    #   uvicorn --workers 2, le serveur demarrait avec plusieurs processus et
    #   la composition epsilon se dedoublait SILENCIEUSEMENT (Porte 4 cassee
    #   sans aucune erreur). Meme motif que la Porte 19 : une protection qui
    #   repose sur une hypothese d'environnement non verifiee.
    # - On inspecte donc aussi sys.argv pour attraper --workers / -w.
    nb_workers = os.environ.get("WEB_CONCURRENCY")
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg in ("--workers", "-w") and i + 1 < len(argv):
            nb_workers = argv[i + 1]
            break
        if arg.startswith("--workers="):
            nb_workers = arg.split("=", 1)[1]
            break
    if nb_workers is not None:
        try:
            if int(nb_workers) > 1:
                raise RuntimeError(
                    f"VERA REFUSE DE DEMARRER : {nb_workers} workers detectes. "
                    "L'etat DP est en memoire de processus et n'est pas partage "
                    "entre workers -- lancer plusieurs workers casse la garantie "
                    "de composition epsilon (Porte 4). Lancez uvicorn avec un seul "
                    "worker (comportement par defaut, sans --workers)."
                )
        except ValueError:
            pass

_verifier_worker_unique()

# Compte RH de démarrage, créé une seule fois au lancement du service.
#
# Deux voies, par ordre de préférence :
#
#   VERA_ADMIN_HASH  — une empreinte "sel_hex$hash_hex" calculée hors ligne.
#                      Le mot de passe n'apparaît alors nulle part sur le
#                      serveur. C'est la voie à utiliser.
#   VERA_ADMIN_PASS  — le mot de passe en clair. Conservée pour ne pas casser
#                      un déploiement existant, mais il vit alors en
#                      permanence dans l'unité systemd, lisible par
#                      `systemctl cat` et recopié dans toute sauvegarde de
#                      configuration. C'est par ce canal que les secrets ont
#                      fuité le 31/07/2026.
#
# Pour basculer :
#   python3 -c "import vera_admin_auth as a; print(a.generer_empreinte('MDP'))"
# puis remplacer VERA_ADMIN_PASS par VERA_ADMIN_HASH dans l'unité systemd.
import os
_admin_user = os.environ.get("VERA_ADMIN_USER")
_admin_hash = os.environ.get("VERA_ADMIN_HASH")
_admin_pass = os.environ.get("VERA_ADMIN_PASS")

if _admin_user and _admin_hash:
    auth.creer_compte_depuis_empreinte(_admin_user, _admin_hash)
elif _admin_user and _admin_pass:
    auth.creer_compte(_admin_user, _admin_pass)
    print("ATTENTION : compte d'amorçage créé depuis VERA_ADMIN_PASS. Le mot "
          "de passe vit en clair dans l'unité systemd. Préférez "
          "VERA_ADMIN_HASH (voir vera_admin_auth.generer_empreinte).")

# CORS restreint au domaine de VERA. allow_origins=["*"] etait inutilement
# large : tout le client (page de vote, tableau de bord) est servi depuis ce
# meme domaine, aucune origine tierce n'a besoin d'appeler l'API. Le risque
# etait limite -- allow_credentials n'etant pas active, le cookie de session RH
# n'a jamais ete transmis en cross-origin -- mais une politique ouverte permet
# a n'importe quel site d'interroger les endpoints publics depuis le navigateur
# d'un visiteur. Principe de moindre privilege.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vera-consultation.duckdns.org"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/vote")
def page_vote():
    """Page de vote du participant. Le lien SMS distribue par le RH pointe ici
    (/vote?a=JETON&d=DEPARTEMENT#k=EMPREINTE). Sans cette route, le lien
    renvoyait 404 alors que le fichier existait sous /static/vote.html : tout
    votant recevant son SMS tombait sur une erreur. Le fragment #k= n'est pas
    transmis au serveur (le navigateur le garde), il reste disponible au JS."""
    return FileResponse("static/vote.html")

verrou = threading.Lock()


# Compteurs cumules par departement, jamais une liste de reponses
# individuelles -- decision actee apres challenge multi-IA (ChatGPT + Grok,
# convergents) : une liste, meme temporaire et meme sans identite associee,
# expose un resultat partiel non agrege en cas d'acces root/dump memoire
# pendant la fenetre de vote. Les compteurs cumules reduisent au minimum
# l'information presente a tout instant -- s'il n'y a plus de liste, il n'y
# a plus rien a extraire au-dela de ce que K_MIN protege deja a la
# publication. Voir LIMITS.md pour la limite honnete documentee : ceci ne
# protege pas contre un attaquant root pendant l'execution (aucune solution
# logicielle ne le peut, cf. discussion id_opaque), seulement contre
# l'existence meme de la donnee a extraire.
compteurs_par_departement: dict[str, dict[str, int]] = {}
effectif_par_departement: dict[str, int] = {}

# Porte 4 du modele de menace : budget de confidentialite cumule par
# departement. Chaque publication de resultat (cf. /api/rh/resultats)
# consomme une fraction de ce budget -- une fois epuise pour un
# departement donne, plus aucun resultat n'est publie pour cette cohorte,
# meme si K_MIN est atteint. Empeche qu'un organisateur recoupe plusieurs
# publications successives sur la meme population pour en deduire plus
# que ce qu'une seule publication ne revelerait (cf. LIMITS.md).
EPSILON_PAR_PUBLICATION = 0.5  # coherent avec validation_opendp.py existant
# Budget epsilon = 0.5 par population = UNE seule publication par departement.
# Le resultat bruite est fige a la premiere publication (voir deja_publie plus
# bas) : republier renverrait le meme resultat, jamais un nouveau tirage. Il
# n'y a donc volontairement AUCUNE re-publication -- c'est ce qui empeche le
# moyennage du bruit. Le budget est aligne sur ce comportement reel (0.5, pas
# 1.5) pour ne pas laisser croire a 3 publications possibles.
budget_epsilon = BudgetEpsilonParDepartement(epsilon_total_autorise=0.5)

import vera_persistance as persistance

persistance.initialiser()

_budget_persiste = persistance.charger_budget_epsilon()
for _dep, _etat in _budget_persiste.items():
    budget_epsilon.injecter_etat(_dep, _etat["epsilon_consomme"], _etat["nombre_publications"])

_compteurs_persistes, _effectifs_persistes = persistance.charger_compteurs()
compteurs_par_departement.update(_compteurs_persistes)
effectif_par_departement.update(_effectifs_persistes)

# --------------------------------------------------------------------------
# Porte 7 durcie (signature aveugle RSABSSA) -- mode optionnel, EN PLUS du
# systeme de tokens actuel, pas a sa place. Le serveur Hetzner (Linux) n'a
# actuellement PAS le module vera_blind_sig compile (compile uniquement sur
# Windows/Dell pour l'instant) -- l'import est protege pour que le serveur
# continue de fonctionner normalement meme sans ce module. A activer
# reellement seulement apres avoir recompile vera_blind_sig pour Linux et
# valide ce nouveau chemin en parallele de l'ancien.
# --------------------------------------------------------------------------
try:
    from vera_signature_manager import (
        GestionnaireSignature,
        decoder_token_depuis_url,
        encoder_token_pour_url,
        TokenDejaUtiliseError,
        SignatureInvalideError,
    )
    gestionnaire_signature = GestionnaireSignature()
    gestionnaire_signature.ouvrir_consultation()
    SIGNATURE_AVEUGLE_DISPONIBLE = True
except Exception as e:
    raise RuntimeError(
        f"ERREUR CRITIQUE : signature aveugle non disponible ({type(e).__name__}: {e}). "
        "Le serveur refuse de demarrer sans signature aveugle RSABSSA (Porte 7 fail-closed). "
        "Verifiez que le venv est active : source /root/vera_blind_sig/.venv/bin/activate"
    )

# code_court (4 chiffres) -> token complet
# Permet d'envoyer "4827" plutot que le token long, sans jamais exposer
# le vrai token tant que le code n'a pas ete verifie cote serveur.
registre_codes_courts: dict[str, str] = {}
# Rechargement au demarrage : sans cela, un redemarrage pendant une
# consultation active invaliderait tous les codes courts deja distribues.
try:
    registre_codes_courts.update(persistance.charger_codes_courts())
except Exception as _e:
    import logging
    logging.warning("Impossible de recharger les codes courts au demarrage: %s", _e)

# Protection anti-brute-force : avec seulement 10000 combinaisons a 4
# chiffres, il faut limiter les tentatives. IP -> {"echecs": int, "bloque_jusqu_a": float}
import time
_tentatives_par_ip: dict[str, dict] = {}
SEUIL_ECHECS_AVANT_BLOCAGE = 5
DUREE_BLOCAGE_SECONDES = 300  # 5 minutes


def _ip_client(request) -> str:
    """IP source robuste au deploiement. Si la connexion vient de localhost,
    c'est Nginx qui relaie : on fait confiance a X-Real-IP qu'il pose lui-meme
    (non falsifiable). Sinon l'app est exposee directement et X-Real-IP serait
    pose par le client : on l'ignore. On ne lit jamais X-Forwarded-For, dont le
    premier element est controle par le client."""
    ip_directe = request.client.host if request.client else "inconnue"
    if ip_directe in ("127.0.0.1", "::1"):
        return request.headers.get("x-real-ip") or ip_directe
    return ip_directe


def _verifier_anti_bruteforce(ip: str) -> None:
    """Leve une exception si l'IP a depasse le seuil d'echecs recents."""
    with verrou:
        info = _tentatives_par_ip.get(ip)
        if info and info.get("bloque_jusqu_a", 0) > time.time():
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives. Réessayez dans quelques minutes.",
            )


# Duree apres laquelle une entree IP inactive est purgee (aucun echec recent
# et blocage expire). Empeche _tentatives_par_ip de croitre sans borne, y
# compris pour des IP a 1-4 echecs qui disparaissent (fuite pilotable sinon).
DUREE_RETENTION_IP_SECONDES = 3600  # 1h


def _purger_ip_expirees() -> None:
    """Supprime toute entree inactive depuis DUREE_RETENTION_IP_SECONDES et
    dont le blocage est expire, QUEL QUE SOIT le nombre d'echecs. Appele sous
    verrou. Corrige la fuite ou une IP a echecs != 0 restait indefiniment."""
    maintenant = time.time()
    a_supprimer = [
        ip for ip, info in _tentatives_par_ip.items()
        if info.get("bloque_jusqu_a", 0) < maintenant
        and (maintenant - info.get("derniere_activite", 0)) > DUREE_RETENTION_IP_SECONDES
    ]
    for ip in a_supprimer:
        _tentatives_par_ip.pop(ip, None)


def _enregistrer_echec(ip: str) -> None:
    with verrou:
        _purger_ip_expirees()
        info = _tentatives_par_ip.setdefault(ip, {"echecs": 0, "bloque_jusqu_a": 0, "derniere_activite": 0})
        info["echecs"] += 1
        info["derniere_activite"] = time.time()
        if info["echecs"] >= SEUIL_ECHECS_AVANT_BLOCAGE:
            info["bloque_jusqu_a"] = time.time() + DUREE_BLOCAGE_SECONDES
            info["echecs"] = 0


def _reinitialiser_echecs(ip: str) -> None:
    with verrou:
        _tentatives_par_ip.pop(ip, None)


CAPACITE_CODES = 10000
SEUIL_SATURATION_CODES = 9000  # au-dela, on refuse de generer

# Valeur par DEFAUT. L'intitule reel est defini par l'organisation via
# POST /api/rh/question, tant qu'aucune cle n'existe (donc avant la generation
# du premier lien). Il est ensuite fige pour toute la consultation : le laisser
# modifiable permettrait de recueillir 200 reponses sur une question, de la
# changer, puis d'en recueillir 40 autres et de publier le tout comme un
# resultat unique -- une manipulation invisible dans les chiffres.
# Les OPTIONS ne sont pas modifiables : toute la calibration DP suppose trois
# options (DELTA_INT=2, K_MIN=240 mesure sur trois).
QUESTION_ACTIVE = {
    "question": "Êtes-vous favorable à la proposition soumise à cette consultation ?",
    "options": [
        {"valeur": "oui", "texte": "Oui"},
        {"valeur": "non", "texte": "Non"},
        {"valeur": "abstention", "texte": "Je m'abstiens"},
    ],
}

# Dernier intitule lu avec succes. "charge" distingue "jamais lu" de "lu, et il
# n'y avait pas de question definie" -- sans quoi on ne peut pas savoir si un
# None signifie "aucune question" ou "lecture impossible".
_cache_question = {"intitule": None, "charge": False}


def question_courante():
    """Question en cours : celle definie par l'organisation, ou le defaut.

    En cas d'erreur de lecture, ne retombe PLUS silencieusement sur la question
    par defaut. L'ancien `except Exception: pass` avait une consequence que rien
    ne signalait : une erreur SQLite transitoire faisait servir la question par
    defaut aux votants suivants, dont les reponses etaient comptees dans le MEME
    compteur que celles portant sur la vraie question. Substitution silencieuse
    de question -- exactement ce que definir_question interdit deliberement en
    figeant l'intitule des la generation du premier lien.

    Nouveau comportement : on sert le dernier intitule lu avec succes (cache
    memoire), et si aucun n'a jamais ete lu, on refuse plutot que de deviner.
    """
    try:
        intitule = persistance.charger_question()
        _cache_question["intitule"] = intitule
        _cache_question["charge"] = True
    except Exception:
        if not _cache_question["charge"]:
            # Jamais lu avec succes : impossible de savoir quelle question est
            # en cours. Servir le defaut risquerait de melanger des reponses
            # portant sur deux questions differentes.
            raise HTTPException(
                status_code=503,
                detail="Question de la consultation temporairement indisponible. Reessayez dans un instant.",
            )
        intitule = _cache_question["intitule"]

    return {
        "question": intitule or QUESTION_ACTIVE["question"],
        "options": QUESTION_ACTIVE["options"],
    }


# K_MIN = 240

# K_MIN : seuil MESURE (14/07/2026), pas choisi arbitrairement.
# A eps=0.5 avec projection sur le simplexe, l'erreur max sur les 3 options
# reste sous 5% de l'effectif dans 95% des publications a partir de n=240.
# En dessous (n=100 : 9%, n=200 : 6%), la promesse de precision ne tient pas.
K_MIN = 240

# Cible de bourrage des reponses portant un nom de departement. Doit depasser
# la longueur maximale autorisee (Field max_length=100) pour que la taille de
# la reponse reste constante quel que soit le departement.
LONGUEUR_PAD_REPONSE = 120


# --------------------------------------------------------------------------
# Authentification RH
# --------------------------------------------------------------------------

class IdentifiantsRH(BaseModel):
    identifiant: str
    mot_de_passe: str


def exiger_session(session_vera: Optional[str] = Cookie(None)) -> str:
    """Dependance FastAPI : verifie la session, leve 401 sinon."""
    if not session_vera:
        raise HTTPException(status_code=401, detail="Non authentifié")
    compte = auth.session_valide(session_vera)
    if compte is None:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    return compte


@app.post("/api/rh/connexion")
def connexion_rh(payload: IdentifiantsRH, response: Response, request: Request):
    # ANTI-BRUTEFORCE (ajoute le 24/07). Cet endpoint est public et declenche
    # un PBKDF2 de 200000 iterations A CHAQUE appel, y compris pour un compte
    # inexistant (calcul factice anti-timing). Sans limitation, deux attaques :
    # (1) brute-force du mot de passe RH sans jamais etre bloque ;
    # (2) plus grave, AMPLIFICATION -- le service tourne en worker unique
    #     (garde deliberee, etat DP en memoire), donc quelques dizaines de POST
    #     par seconde monopolisent le CPU et font tomber les votes legitimes en
    #     timeout. C'est "detruire des votes" sans toucher au logiciel.
    # Le mecanisme existait mais n'etait cable que sur le circuit code court,
    # devenu du code mort : plus aucun endpoint n'etait protege.
    ip_client = _ip_client(request)
    _verifier_anti_bruteforce(ip_client)

    if not auth.verifier_identifiants(payload.identifiant, payload.mot_de_passe):
        _enregistrer_echec(ip_client)
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")

    _reinitialiser_echecs(ip_client)
    jeton_session = auth.ouvrir_session(payload.identifiant)
    response.set_cookie(
        key="session_vera",
        value=jeton_session,
        httponly=True,
        secure=True,   # cookie jamais transmis en clair (lecon Porte 19 : ne
                       # pas dependre de l'hypothese "il y aura toujours une
                       # redirection HTTPS")
        samesite="lax",
        max_age=auth.DUREE_SESSION_SECONDES,
    )
    return {"statut": "connecte", "compte": payload.identifiant}


@app.post("/api/rh/deconnexion")
def deconnexion_rh(response: Response, session_vera: Optional[str] = Cookie(None)):
    if session_vera:
        auth.fermer_session(session_vera)
    response.delete_cookie("session_vera")
    return {"statut": "deconnecte"}


# --------------------------------------------------------------------------
# Creation de nouveaux comptes RH. Protege par un secret ADMIN distinct des
# comptes RH eux-memes -- un compte RH normal ne peut pas creer d'autres
# comptes RH, seul celui qui detient ce secret (l'operateur technique du
# serveur) le peut. Ce secret n'est PAS le mot de passe d'un compte RH :
# c'est une cle d'administration separee.
#
# PORTEE REELLE (corrigee le 24/07/2026) : cette fonction permet d'avoir
# PLUSIEURS ADMINISTRATEURS D'UNE MEME ORGANISATION (separation des roles,
# tracabilite de qui a genere quelles autorisations). Elle ne permet PAS
# d'heberger plusieurs organisations sur une meme instance, contrairement a
# ce que ce commentaire affirmait ("vraie separation organisationnelle entre
# plusieurs entites emettrices").
#
# Raison : la separation ne porte que sur l'AUTHENTIFICATION. Les DONNEES ne
# sont pas cloisonnees -- compteurs_votes, cle_rsa_active, budget_epsilon et
# jetons_autorisation sont tous indexes par departement SEUL, jamais par
# (compte, departement). Deux organisations creant chacune un departement
# "Marketing" partageraient donc la meme urne, la meme cle de signature et le
# meme budget epsilon : les votes de l'une compteraient dans les resultats de
# l'autre.
#
# INVARIANT DE DEPLOIEMENT : une instance VERA = une organisation consultante.
# Voir LIMITS.md. Un vrai multi-tenant exigerait de re-cler ces quatre tables
# par (compte, departement) ; non fait, et non necessaire tant que chaque
# organisation dispose de son instance.
# --------------------------------------------------------------------------

_secret_admin_creation = os.environ.get("VERA_SECRET_CREATION_COMPTE")


class CreerCompteRequete(BaseModel):
    identifiant: str
    mot_de_passe: str
    secret_admin: str


@app.post("/api/admin/creer_compte_rh")
def creer_compte_rh(payload: CreerCompteRequete):
    if not _secret_admin_creation:
        raise HTTPException(
            status_code=503,
            detail="Création de compte désactivée (VERA_SECRET_CREATION_COMPTE non configuré sur ce serveur).",
        )
    if not hmac.compare_digest(payload.secret_admin, _secret_admin_creation):
        raise HTTPException(status_code=403, detail="Secret administrateur incorrect")

    if len(payload.mot_de_passe) < 8:
        raise HTTPException(status_code=422, detail="Mot de passe trop court (8 caractères minimum)")

    succes = auth.creer_compte(payload.identifiant, payload.mot_de_passe)
    if not succes:
        raise HTTPException(status_code=409, detail="Cet identifiant existe déjà")

    return {"statut": "compte créé", "identifiant": payload.identifiant}


# --------------------------------------------------------------------------
# Endpoints RH proteges (necessitent une session valide)
# --------------------------------------------------------------------------

class GenererTokensRequete(BaseModel):
    # Contraintes de robustesse : un departement non vide et de longueur
    # bornee (evite les departements fantomes vides et les chaines geantes
    # qui pollueraient dicts et base). Quantite bornee cote schema (le 422
    # est alors automatique et clair, plutot qu'une verification manuelle).
    departement: str = Field(min_length=1, max_length=100)
    quantite: int = Field(ge=1, le=1000)


@app.post("/api/rh/generer_tokens")
def generer_tokens(payload: GenererTokensRequete, session_vera: Optional[str] = Cookie(None)):
    # ENDPOINT OBSOLETE (ancien Modele A). Le flux Modele B remplace la
    # generation de tokens complets cote serveur par la generation de JETONS
    # D'AUTORISATION (voir /api/rh/generer_autorisations). Conserve pour
    # renvoyer un message clair plutot qu'un 500 aux anciens appelants.
    exiger_session(session_vera)
    raise HTTPException(
        status_code=410,
        detail="Endpoint obsolete. Utilisez /api/rh/generer_autorisations (flux Modele B).",
    )
# ============================================================================
# REFACTOR CRYPTO -- Endpoint de signature aveugle (Temps 2, cote serveur)
# Le votant a aveugle son message DANS SON NAVIGATEUR. Il presente ici son
# jeton d'autorisation (Temps 1) + le message aveugle. Le serveur consomme le
# jeton (atomique, anti-double-vote), signe A L'AVEUGLE, et renvoie. Il ne voit
# jamais le message en clair ni le token final -> il ne peut pas relier
# identite et vote. C'est le coeur de l'unlinkability effective.
# ============================================================================
class SignerAveugleRequete(BaseModel):
    jeton_autorisation: str = Field(min_length=1, max_length=200)
    message_aveugle_hex: str = Field(min_length=1, max_length=2000)


@app.post("/api/signer_aveugle")
def signer_aveugle_endpoint(payload: SignerAveugleRequete):
    import hashlib
    # 0. Refuser AVANT de consommer le jeton si les depots ne sont pas ouverts.
    #    Sans ce controle, un votant arrivant en avance brulerait son jeton
    #    pour un credential qu'il ne pourrait pas deposer : sa voix serait
    #    perdue sans recours, puisqu'un jeton ne se consomme qu'une fois.
    #    L'ordre compte : ce test precede la consommation, jamais l'inverse.
    ouverture = persistance.charger_ouverture_depots()
    if ouverture is not None and time.time() < ouverture:
        raise HTTPException(
            status_code=425,
            detail="La consultation n'a pas encore commence. Votre lien reste "
                   "valable : revenez a la date indiquee dans votre invitation.",
        )

    # 1. Consommer le jeton d'autorisation (registre 1, ATOMIQUE). Renvoie le
    #    departement si valide et non utilise, sinon None. On consomme AVANT de
    #    signer : protege contre le double-vote par requetes simultanees (un
    #    seul appelant peut consommer un jeton donne). Le cas ou la signature
    #    echoue apres consommation est extremement rare (consultation fermee
    #    pile entre les deux) et prefere a un risque de double-vote.
    # 1bis. IDEMPOTENCE -- avant de consommer.
    #
    # LE PROBLEME QUE CELA RESOUT
    # Le jeton etait consomme AVANT la signature, pour qu'un meme jeton ne
    # puisse pas produire deux credentials differents. Consequence : si le
    # navigateur echouait apres que le serveur avait signe -- reseau coupe,
    # onglet ferme, page rechargee -- la voix etait perdue sans recours. Le
    # jeton etait brule, et rien ne permettait de retrouver la signature.
    #
    # LA SOLUTION
    # Le serveur memorise le couple (jeton, message aveugle) avec la signature
    # emise. Un rejeu A L'IDENTIQUE retrouve SA signature. Un message
    # DIFFERENT avec le meme jeton est refuse : c'est une tentative d'obtenir
    # un second credential, donc un double vote.
    #
    # POURQUOI C'EST SUR
    # Deux credentials distincts ne peuvent pas naitre d'un meme jeton,
    # puisque seul un rejeu identique est accepte. La garantie anti-double-vote
    # est preservee, et la voix cesse d'etre perdue sur un incident reseau.
    #
    # CE QUE CELA COUTE
    # La table conserve le lien (jeton -> message aveugle) : exactement ce que
    # le protocole existe pour ne pas conserver. D'ou une retention d'une heure
    # seulement, et un effacement a la cloture.
    try:
        message_aveugle = bytes.fromhex(payload.message_aveugle_hex)
    except ValueError:
        raise HTTPException(status_code=422, detail="message_aveugle_hex n'est pas de l'hexadecimal valide.")

    emp_jeton = hashlib.sha384(payload.jeton_autorisation.encode("utf-8")).hexdigest()
    emp_message = hashlib.sha384(message_aveugle).hexdigest()

    deja = persistance.signature_deja_emise(emp_jeton, emp_message)
    if deja is not None:
        sig_hex, dep = deja
        pad = "x" * max(0, LONGUEUR_PAD_REPONSE - len(dep))
        return {"signature_aveugle_hex": sig_hex, "departement": dep, "pad": pad}

    # Meme jeton, message different : refus. C'est la garantie anti-double-vote.
    if persistance.jeton_a_deja_signe(emp_jeton):
        raise HTTPException(
            status_code=403,
            detail="Ce lien a deja servi a obtenir une signature. Si votre vote "
                   "n'a pas abouti, rouvrez le lien tel quel sans recharger la "
                   "page : votre signature vous sera renvoyee.",
        )

    departement = persistance.consommer_jeton_autorisation(payload.jeton_autorisation)
    if departement is None:
        raise HTTPException(status_code=403, detail="Jeton d'autorisation invalide ou deja utilise.")

    # 3. Signer a l'aveugle (seule etape serveur du protocole RSABSSA).
    try:
        sig_aveugle = gestionnaire_signature.signer_message_aveugle(departement, message_aveugle)
    except RuntimeError as e:
        # Endpoint PUBLIC : le detail de l'exception reste cote serveur. Le
        # renvoyer exposerait des internes du gestionnaire de signature a
        # quiconque appelle la route, sans rien apporter au votant -- qui ne
        # peut de toute facon qu'attendre ou demander un nouveau lien.
        print(f"ERREUR : signature aveugle impossible pour '{departement}' : {e}")
        raise HTTPException(
            status_code=503,
            detail="Le service de signature est momentanement indisponible. Reessayez dans quelques instants.",
        )

    # Memoriser AVANT de repondre : si le client n'a jamais recu la reponse,
    # il pourra rejouer sa requete a l'identique et retrouver cette signature.
    # L'ordre compte -- memoriser apres l'envoi laisserait la fenetre ouverte.
    persistance.enregistrer_signature_emise(
        emp_jeton, emp_message, sig_aveugle.hex(), departement)

    # 4. Renvoyer la signature aveugle + le departement (le client en a besoin
    #    pour construire son vote). Aucun lien jeton<->signature n'est stocke.
    # Bourrage a longueur constante, meme raison que le pad du depot de vote :
    # sans lui, la TAILLE de cette reponse varie avec la longueur du nom de
    # departement, et un observateur passif classe les votants par service a la
    # simple taille du paquet TLS -- une requete avant que le bourrage du depot
    # n'entre en jeu. Le pad du client fermait la derniere requete du parcours,
    # celui-ci ferme celle-ci.
    # departement est renvoye parce que le client en a besoin pour finaliser
    # (static/vote.html) : on ne peut pas simplement l'omettre.
    pad = "x" * max(0, LONGUEUR_PAD_REPONSE - len(departement))
    return {
        "signature_aveugle_hex": sig_aveugle.hex(),
        "departement": departement,
        "pad": pad,
    }


# ============================================================================
# REFACTOR CRYPTO -- Exposition de la cle publique + son empreinte (Exigence 1)
# La cle publique est PUBLIQUE par nature : l'exposer n'est pas un risque. Le
# risque serait qu'un serveur malveillant en donne une DIFFERENTE par votant
# (attaque par substitution de cle -> desanonymisation). La PARADE (cote client)
# est de comparer l'empreinte de la cle recue a une empreinte ENGAGEE hors du
# serveur (dans le lien SMS, fragment #k=). Cet endpoint fournit la cle et son
# empreinte SHA-256 ; c'est le client qui doit verifier l'empreinte contre celle
# du lien, JAMAIS se fier aveuglement a ce que renvoie le serveur.
# ============================================================================
@app.get("/api/cle_publique")
def cle_publique_endpoint(departement: str):
    import hashlib
    # LECTURE SEULE (voir cle_publique_si_existe) : endpoint public, ne doit
    # jamais declencher de generation de cle. La cle est creee par le flux RH
    # authentifie (generer_autorisations) avant toute distribution de lien.
    try:
        pk_der = gestionnaire_signature.cle_publique_si_existe(departement)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Aucune consultation active.")
    except KeyError:
        raise HTTPException(status_code=404, detail="Departement inconnu.")
    return {
        "cle_publique_hex": pk_der.hex(),
        "empreinte_sha256": hashlib.sha256(pk_der).hexdigest(),
    }


# ============================================================================
# REFACTOR CRYPTO -- Generation des jetons d'autorisation par le RH (Temps 1)
# NOUVEAU flux : le RH ne genere plus de tokens de vote complets (ancien
# generer_tokens, conserve pour la transition). Il genere des JETONS
# D'AUTORISATION (identifiants aleatoires a usage unique, registre 1) qui
# prouvent le droit de demander une signature aveugle. Chaque jeton est
# integre dans un lien SMS avec l'empreinte de la cle publique (fragment #k=,
# jamais envoye au serveur) -> engagement de cle cote client (Exigence 1).
# Le RH envoie lui-meme les SMS (Option B) : le serveur ne voit jamais les
# numeros de telephone.
# ============================================================================
class GenererAutorisationsRequete(BaseModel):
    # Le motif restreint le nom aux caracteres qu'un service porte legitimement :
    # lettres (accents compris), chiffres, espace, tiret, apostrophe, parentheses,
    # point. Il exclut < > " & / et tout le reste.
    #
    # Ce n'est PAS la defense porteuse contre l'injection -- c'est l'echappement
    # a l'affichage qui l'est, et il est applique partout dans admin.html. Mais
    # un nom de departement n'a aucune raison legitime de contenir du balisage,
    # et fermer la classe entiere vaut mieux que de dependre d'un echappement
    # exhaustif : il a suffi d'UN chemin oublie (celui de la cloture) pour
    # rouvrir le vecteur.
    #
    # Le nom transite jusqu'au SMS et jusqu'a l'ecran de resultats : il est
    # recopie a plusieurs endroits, ce qui multiplie les occasions d'oubli.
    departement: str = Field(min_length=1, max_length=100,
                             pattern=r"^[\w \-'()\.À-ÿ]+$")
    quantite: int = Field(ge=1, le=1000)


@app.post("/api/rh/generer_autorisations")
def generer_autorisations(payload: GenererAutorisationsRequete, session_vera: Optional[str] = Cookie(None)):
    import hashlib
    compte = exiger_session(session_vera)

    # Empreinte de la cle publique de l'epoque (engagement de cle). Le RH la
    # met dans chaque lien SMS ; le client verifiera la cle recue contre elle.
    try:
        pk_der = gestionnaire_signature.cle_publique(payload.departement)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Aucune consultation active.")
    # Le groupe doit avoir ete declare AVANT. Sans ce controle, generer des
    # liens pour un groupe nouveau creerait une cle de plus, changerait
    # l'empreinte de l'ensemble, et invaliderait tous les liens deja
    # distribues -- exactement ce que la declaration prealable existe pour
    # empecher.
    declares = persistance.charger_groupes_declares()
    if declares is None:
        raise HTTPException(
            status_code=409,
            detail="Declarez d'abord la liste des groupes consultes. Les cles "
                   "sont creees ensemble pour que l'empreinte inscrite dans les "
                   "liens ne change plus.",
        )
    if payload.departement not in declares:
        raise HTTPException(
            status_code=409,
            detail=f"Le groupe « {payload.departement} » n'a pas ete declare. "
                   f"Groupes declares : {', '.join(declares)}. En ajouter un "
                   "maintenant invaliderait les liens deja distribues.",
        )

    # Le lien porte l'empreinte de l'ENSEMBLE des cles, pas celle du seul
    # groupe concerne.
    #
    # POURQUOI CE CHANGEMENT
    # L'empreinte d'une cle de groupe est calculee par le serveur et differe
    # d'un groupe a l'autre. Elle ne l'engage donc pas : il peut fabriquer une
    # cle par personne avec l'empreinte correspondante, le controle cote client
    # passe, et au depouillement il retrouve qui a produit quelle signature.
    # Et deux collegues de services differents ne pouvaient rien conclure d'une
    # divergence : elle etait NORMALE entre groupes.
    #
    # L'agregat change les deux choses a la fois. Il couvre le nombre ET le
    # contenu de toutes les cles, et il est IDENTIQUE pour tous les votants --
    # donc comparable entre collegues, quel que soit leur service.
    #
    # Surtout, il peut etre publie HORS BANDE avant l'envoi des liens : un
    # commit horodate dans le depot, qui n'est pas sur cette machine. Un
    # operateur qui forgerait des cles devrait alors servir une liste
    # divergente de celle publiee ET de celle que voient les autres votants.
    # On passe d'une trace a une trace anterieure, horodatee par un tiers.
    empreinte_cle = gestionnaire_signature.agregat_cles()
    if empreinte_cle is None:
        raise HTTPException(
            status_code=503,
            detail="Les cles de la consultation ne sont pas encore pretes.",
        )

    base_url = "https://vera-consultation.duckdns.org/vote"
    autorisations = []
    # HORS DU VERROU GLOBAL. La generation de jetons est du calcul local
    # (secrets.token_urlsafe) sur des donnees qui n'existent pas encore : elle
    # ne touche a aucun registre partage et n'a donc rien a serialiser contre
    # les votes en cours. L'ancienne version tenait `verrou` pendant toute la
    # boucle ET pendant les N commits SQLite, gelant l'API entiere.
    jetons = [secrets.token_urlsafe(24) for _ in range(payload.quantite)]

    # UNE SEULE transaction pour tout le lot (voir C-8 dans la persistance).
    persistance.persister_jetons_autorisation_lot(jetons, payload.departement)

    for jeton in jetons:
        # TOUT le credential passe par le FRAGMENT (#), rien en query string.
        # Le navigateur ne transmet JAMAIS le fragment au serveur : le jeton
        # n'apparait donc dans aucun access log (avec IP + horodatage), ni dans
        # un proxy, ni dans le Referer. En query (?a=JETON), le simple
        # chargement de la page suffisait a relier une identite a un instant de
        # vote -- le canal que la coupure des logs sur les POST visait, laisse
        # ouvert par le GET de la page.
        # Le departement est ENCODE : insere brut, un nom contenant un espace
        # ou un caractere special produisait une URL que certains clients SMS
        # tronquent au premier espace. Le votant recevait alors un lien coupe et
        # un departement inconnu. Constat du 26/07 : un departement nomme
        # "Dp test" avait bien produit un lien a espace.
        lien = f"{base_url}#a={jeton}&d={quote(payload.departement, safe='')}&k={empreinte_cle}"
        autorisations.append({"jeton": jeton, "lien_sms": lien})

    return {
        "departement": payload.departement,
        "quantite": len(autorisations),
        "empreinte_cle": empreinte_cle,
        "autorisations": autorisations,
        "genere_par": compte,
    }


def _publier_departement(departement, effectif):
    """Publie UN departement : tire le bruit DP, persiste, consomme le budget.

    DOIT etre appelee avec `verrou` deja tenu par l'appelant.

    C'EST LE SEUL CHEMIN DE PUBLICATION DU CODE. Avant ce correctif il en
    existait deux : celui de /api/rh/resultats (complet, avec verification de
    budget) et celui de /api/rh/cloturer (qui appelait publier_histogramme_dp
    en direct, SANS peut_publier ni consommer ni persister -- la Porte 4 etait
    purement et simplement contournee). Deux chemins pour une operation
    irreversible, c'est un chemin de trop : toute publication passe desormais
    ici, ou nulle part.

    Retourne un dict pret a etre renvoye au client.
    """
    etat_avant = budget_epsilon.etat(departement)

    if etat_avant["nombre_publications"] > 0:
        # Deja publie : on renvoie le resultat fige, JAMAIS un nouveau tirage.
        # Re-tirer permettrait de moyenner N echantillons et d'annuler le bruit.
        fige = persistance.charger_resultat_publie(departement)
        if fige is None:
            return {
                "refuse": True,
                "raison": "Resultat fige introuvable, publication refusee par securite.",
            }
        return {
            "resultats_bruits": fige,
            "budget_epsilon": budget_epsilon.etat(departement),
            "publie": True,
        }

    if not budget_epsilon.peut_publier(departement, EPSILON_PAR_PUBLICATION):
        return {
            "refuse": True,
            "raison": "Budget de confidentialite epuise pour ce groupe.",
        }

    # ORDRE CRITIQUE : on CALCULE l'etat futur sans muter la memoire. La
    # consommation reelle n'a lieu qu'APRES un commit reussi (plus bas).
    # Si consommer() mutait ici, une panne d'ecriture laisserait la memoire en
    # avance sur la base -- departement vu comme ayant publie alors que le
    # resultat fige est absent, donc verrouille a jamais.
    etat_apres = budget_epsilon.etat_apres_consommation(
        departement, EPSILON_PAR_PUBLICATION)

    comptes_bruts = compteurs_par_departement.get(departement, {})
    comptes_ordonnes = {
        option["valeur"]: comptes_bruts.get(option["valeur"], 0)
        for option in question_courante()["options"]
    }
    # Laplace vectoriel (Delta_1 = 2, scale = 4, eps = 0.5) PUIS projection sur
    # le simplexe {x >= 0, somme = effectif}. La projection est du
    # post-traitement : gratuite en epsilon, elle reduit l'erreur d'environ 25%
    # et garantit que les comptages publies somment exactement a l'effectif.
    comptes_bruites = publier_histogramme_dp(comptes_ordonnes, effectif)

    # ATOMICITE : budget + resultat committes ensemble. Sans cela, un crash
    # entre les deux ecritures laissait "budget consomme mais resultat absent"
    # -> departement verrouille a jamais.
    persistance.persister_publication_atomique(
        departement,
        etat_apres["epsilon_consomme"],
        etat_apres["nombre_publications"],
        comptes_bruites,
    )
    # Commit reussi : la memoire peut suivre.
    budget_epsilon.consommer(departement, EPSILON_PAR_PUBLICATION)

    return {
        "resultats_bruits": comptes_bruites,
        "budget_epsilon": budget_epsilon.etat(departement),
        "publie": True,
    }


@app.get("/api/rh/resultats")
def resultats(session_vera: Optional[str] = Cookie(None)):
    """LECTURE SEULE. Ne publie rien, ne consomme aucun budget epsilon.

    Avant ce correctif, cet endpoint PUBLIAIT : ouvrir le tableau de bord
    suffisait a figer le resultat. Consequence concrete sur un departement de
    1000 invites : le 240e vote arrive, le RH consulte son suivi, le resultat
    est fige sur 240 reponses -- et les votes 241 a 1000, bien qu'enregistres
    en base, ne seront JAMAIS publies. Aucun ecran ne signalait l'ecart.

    Aggravation anonymat : le resultat fige correspondait aux 240 PREMIERS
    votants, sous-ensemble que le RH peut enumerer en surveillant le compteur
    de participation pendant qu'il relance les gens. L'ensemble d'anonymat
    n'etait plus le departement mais une cohorte de 240 personnes identifiables.

    Aggravation securite : etant un GET mutant avec un cookie SameSite=Lax, il
    etait declenchable par simple navigation cross-site (CSRF). Un lien piege
    ouvert par un RH connecte figeait les resultats de tous les departements
    ayant franchi K_MIN. L'attaquant ne lisait rien (CORS), il n'en avait pas
    besoin : l'effet destructeur etait dans l'ecriture.

    La publication est desormais un acte delibere : POST /api/rh/publier.
    """
    exiger_session(session_vera)

    resultat_par_departement = {}
    with verrou:
        for departement, effectif in effectif_par_departement.items():

            # SEUIL K_MIN : refus pur et simple sous la barre. Verifie avant
            # toute autre consideration.
            if effectif < K_MIN:
                resultat_par_departement[departement] = {
                    "refuse": True,
                    "raison": f"Effectif insuffisant : moins de {K_MIN} participants (seuil minimum de publication). Le nombre exact n'est pas communique pour ne pas exposer la taille d'une petite cohorte.",
                    "publiable": False,
                    "publie": False,
                }
                continue

            deja_publie = budget_epsilon.etat(departement)["nombre_publications"] > 0

            if not deja_publie:
                # PUBLIABLE MAIS NON PUBLIE : on le dit, on ne le fait pas.
                # C'est ici que se jouait le bug : l'ancien code publiait.
                resultat_par_departement[departement] = {
                    "publiable": True,
                    "publie": False,
                    "message": (
                        "Ce groupe a atteint le seuil et peut etre publie. La "
                        "publication est definitive : elle fige le resultat sur "
                        "les reponses recues a cet instant, et les reponses "
                        "ulterieures ne pourront plus etre comptees."
                    ),
                }
                continue

            fige = persistance.charger_resultat_publie(departement)
            if fige is None:
                resultat_par_departement[departement] = {
                    "refuse": True,
                    "raison": "Resultat fige introuvable, publication refusee par securite.",
                    "publiable": False,
                    "publie": True,
                }
                continue

            resultat_par_departement[departement] = {
                "resultats_bruits": fige,
                "budget_epsilon": budget_epsilon.etat(departement),
                "publiable": True,
                "publie": True,
            }

    return resultat_par_departement


class PublierRequete(BaseModel):
    departement: str = Field(min_length=1, max_length=100)


@app.post("/api/rh/publier")
def publier(requete: PublierRequete, session_vera: Optional[str] = Cookie(None)):
    """Publie un departement. ACTE DELIBERE ET IRREVERSIBLE.

    POST et non GET, pour deux raisons cumulatives : la semantique (cette
    operation ecrit, consomme du budget epsilon et fige un resultat pour
    toujours) et la protection CSRF (le cookie de session est SameSite=Lax,
    qui bloque les POST cross-site mais laisse passer les GET de navigation).

    Un seul departement par appel : publier est une decision par groupe, pas
    une action de masse declenchee par inadvertance.
    """
    exiger_session(session_vera)

    with verrou:
        effectif = effectif_par_departement.get(requete.departement)
        if effectif is None:
            raise HTTPException(status_code=404, detail="Departement inconnu.")
        if effectif < K_MIN:
            raise HTTPException(
                status_code=409,
                detail=f"Effectif insuffisant : moins de {K_MIN} participants.",
            )
        resultat = _publier_departement(requete.departement, effectif)

    if resultat.get("refuse"):
        raise HTTPException(status_code=409, detail=resultat["raison"])

    return {"departement": requete.departement, **resultat}



@app.post("/api/rh/cloturer")
def cloturer_consultation(session_vera: Optional[str] = Cookie(None)):
    """Cloture la consultation en cours. Renvoie UNE DERNIERE FOIS les
    resultats finaux (le RH doit les sauvegarder de son cote), puis efface
    TOUT l'etat brut du serveur : compteurs, effectifs, codes courts, tokens
    consommes, budget, resultats publies, et la cle de signature.

    Apres cet appel, le serveur ne conserve PLUS AUCUNE donnee de la
    consultation. C'est la garantie de minimisation de VERA rendue
    operationnelle et verifiable. Une nouvelle consultation (nouvelle cle)
    est immediatement ouverte pour un usage ulterieur.

    ATTENTION : operation irreversible. Les resultats non sauvegardes par le
    RH a la reception de cette reponse sont definitivement perdus."""
    exiger_session(session_vera)

    # Garde anti double-cloture (B1bis). Si l'etat est deja entierement vide
    # (aucun vote, aucune invitation), il n'y a rien a clore : soit consultation
    # jamais demarree, soit RE-CLIC apres une cloture dont la reponse s'est
    # perdue en transit. Sans cette garde, on tombait dans la boucle sur un etat
    # vide et on renvoyait resultats_finaux={} -> le front affichait "aucun
    # groupe publiable", laissant croire que des reponses avaient ete jugees
    # insuffisantes alors qu'elles avaient deja ete affichees puis effacees.
    # On ne detruit/rouvre donc RIEN et on repond honnetement.
    invitations_existantes = persistance.compter_jetons_par_departement()
    with verrou:
        etat_vide = not effectif_par_departement and not invitations_existantes
    if etat_vide:
        return {
            "statut": "rien_a_cloturer",
            "message": (
                "Aucune donnee a cloturer. Si vous venez de cloturer une "
                "consultation, ses resultats vous ont ete affiches a ce "
                "moment-la : le serveur ne les conserve plus."
            ),
        }

    # VERROU TENU DE LA PUBLICATION JUSQU'A L'EFFACEMENT COMPLET.
    # Auparavant les etapes 2 et 3 s'executaient HORS verrou : un POST
    # /api/repondre concurrent pouvait commiter entre le figement des
    # resultats et l'effacement de la base. Le votant recevait
    # {"statut": "enregistre"} et l'ecran "Reponse enregistree -- votre
    # contribution a ete integree au resultat collectif", alors que son vote
    # etait efface quelques millisecondes plus tard et n'apparaissait dans
    # aucun resultat. Le message etait faux. La cloture est desormais atomique
    # du point de vue des votes : soit un vote est compte et publie, soit il
    # est refuse, jamais "accepte puis silencieusement detruit".
    resultats_finaux = {}
    with verrou:
        # 1. Figer/recuperer les resultats finaux des departements publiables.
        for departement, effectif in effectif_par_departement.items():
            if effectif < K_MIN:
                resultats_finaux[departement] = {
                    "refuse": True,
                    "raison": f"Effectif insuffisant : moins de {K_MIN} participants.",
                }
                continue
            # PASSAGE PAR LE CHEMIN BUDGETAIRE UNIQUE. L'ancien code appelait
            # publier_histogramme_dp en direct : ni peut_publier, ni consommer,
            # ni persister_publication_atomique. C'etait le seul chemin de
            # publication du code qui ignorait totalement la Porte 4 -- sur un
            # etat ou budget_epsilon serait renseigne mais resultats_publies
            # vide (restauration partielle de sauvegarde), la cloture tirait un
            # SECOND echantillon de bruit sur les memes comptages. Deux tirages
            # Laplace independants sur le meme vecteur se moyennent : epsilon
            # effectif divise par deux a chaque iteration.
            resultats_finaux[departement] = _publier_departement(departement, effectif)

        # 2. Detruire la cle de signature -> tous les tokens en circulation
        #    deviennent cryptographiquement invalides.
        gestionnaire_signature.fermer_consultation()

        # 3. Effacer tout l'etat brut cote base.
        persistance.effacer_etat_consultation()

        # 4. Vider les registres memoire.
        compteurs_par_departement.clear()
        effectif_par_departement.clear()
        registre_codes_courts.clear()

    # 5. Vider le set des tokens consommes du gestionnaire.
    try:
        gestionnaire_signature._tokens_consommes.clear()
        # Le budget epsilon en memoire doit etre purge comme les autres
        # registres : la table est videe par effacer_etat_consultation, mais
        # sans ce reset l'objet garderait nombre_publications > 0 et rendrait
        # tout departement de meme nom non publiable a la consultation suivante.
        budget_epsilon.reset()
    except Exception:
        pass

    # 6. Rouvrir une consultation neuve (nouvelle cle) pour un usage ulterieur.
    #    ISOLE DANS UN try : a ce stade les donnees sont DEJA detruites et les
    #    resultats finaux n'existent plus que dans la variable locale ci-dessous.
    #    Si ouvrir_consultation() levait, l'exception remontait en HTTP 500 et
    #    le RH perdait definitivement des resultats irrecuperables -- pour une
    #    panne qui ne concerne QUE la consultation SUIVANTE. On renvoie donc
    #    les resultats dans tous les cas, en signalant l'anomalie a part.
    avertissement_reouverture = None
    try:
        gestionnaire_signature.ouvrir_consultation()
    except Exception as e:
        # Le detail technique reste cote serveur : le renvoyer au client
        # exposerait des internes (chemins, structures, messages de
        # bibliotheque) sans rien lui apporter d'actionnable. Le RH a besoin
        # de savoir QUOI faire, pas POURQUOI ca a echoue -- et le diagnostic
        # est dans le journal du service pour l'operateur.
        print(f"ERREUR : reouverture de consultation impossible apres cloture : {e}")
        avertissement_reouverture = (
            "La consultation a bien ete cloturee et vos resultats sont ci-dessous. "
            "En revanche, la reouverture d'une nouvelle consultation a echoue : "
            "redemarrez le service avant d'en lancer une nouvelle."
        )

    reponse = {
        "statut": "consultation cloturee",
        "avertissement": "Sauvegardez ces resultats : le serveur ne les conserve plus.",
        "resultats_finaux": resultats_finaux,
    }
    if avertissement_reouverture:
        reponse["avertissement_reouverture"] = avertissement_reouverture
    return reponse


class QuestionRequete(BaseModel):
    intitule: str = Field(min_length=10, max_length=300)


@app.post("/api/rh/question")
def definir_question(payload: QuestionRequete, session_vera: Optional[str] = Cookie(None)):
    """Definit l'intitule de la consultation.

    N'est accepte que tant qu'AUCUNE cle n'existe, c'est-a-dire avant la
    generation du premier lien. Ensuite la question est figee : la modifier en
    cours de route permettrait de recueillir des reponses sur une question, de
    la changer, puis de publier l'ensemble comme un resultat unique -- une
    manipulation que rien dans les chiffres ne trahirait.

    Les options (oui / non / abstention) ne sont pas modifiables : la
    calibration DP les suppose au nombre de trois."""
    exiger_session(session_vera)
    if gestionnaire_signature.temps_restant_secondes() is not None:
        raise HTTPException(
            status_code=409,
            detail=("La consultation a deja commence : la question ne peut plus "
                    "etre modifiee. Cloturez d'abord la consultation en cours."),
        )
    intitule = payload.intitule.strip()
    if not intitule:
        raise HTTPException(status_code=422, detail="Intitule vide.")
    persistance.persister_question(intitule)
    return {"statut": "question definie", "question": intitule}


class DeclarerGroupesRequete(BaseModel):
    groupes: list[str] = Field(min_length=1, max_length=200)


@app.post("/api/rh/declarer_groupes")
def declarer_groupes(payload: DeclarerGroupesRequete,
                     session_vera: Optional[str] = Cookie(None)):
    """Fige la liste des groupes et cree toutes leurs cles d'un coup.

    POURQUOI CETTE ETAPE EXISTE
    Chaque lien porte l'empreinte de l'ENSEMBLE des cles, et non celle du seul
    groupe concerne : c'est ce qui la rend identique pour tous les votants,
    donc comparable entre collegues de services differents, et publiable hors
    de ce serveur avant l'envoi.

    Mais cette empreinte change des qu'une cle s'ajoute. Si le RH generait ses
    groupes l'un apres l'autre, les liens du premier porteraient une empreinte
    perimee des la creation du second -- et tous ses votants seraient refuses.

    D'ou cette declaration prealable : les cles naissent ensemble, l'empreinte
    est figee, et les liens peuvent partir.

    IRREVERSIBLE. Ajouter un groupe apres coup invaliderait les liens deja
    distribues. L'interface doit le dire avant de valider.
    """
    exiger_session(session_vera)

    if persistance.charger_groupes_declares() is not None:
        raise HTTPException(
            status_code=409,
            detail="Les groupes ont deja ete declares pour cette consultation. "
                   "Les modifier invaliderait les liens deja distribues. "
                   "Cloturez et recommencez si la liste etait incomplete.",
        )

    # Nettoyage : espaces superflus, doublons, entrees vides. Le tri rend
    # l'empreinte reproductible independamment de l'ordre de saisie.
    vus = set()
    groupes = []
    for g in payload.groupes:
        nom = g.strip()
        if not nom or nom in vus:
            continue
        if len(nom) > 100:
            raise HTTPException(
                status_code=422,
                detail=f"Nom de groupe trop long : « {nom[:40]}... »",
            )
        if not re.match(r"^[\w \-'()\.À-ÿ]+$", nom):
            raise HTTPException(
                status_code=422,
                detail=f"Le nom « {nom} » contient des caracteres non autorises. "
                       "Lettres, chiffres, espace, tiret, apostrophe, parentheses "
                       "et point uniquement.",
            )
        vus.add(nom)
        groupes.append(nom)

    if not groupes:
        raise HTTPException(status_code=422, detail="Aucun groupe valide.")

    groupes.sort()

    # Creer toutes les cles MAINTENANT, pour que l'empreinte soit complete.
    try:
        for nom in groupes:
            gestionnaire_signature.cle_publique(nom)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    persistance.persister_groupes_declares(groupes)
    agregat = gestionnaire_signature.agregat_cles()

    return {
        "groupes": groupes,
        "empreinte_ensemble": agregat,
        "message": "Publiez cette empreinte hors de ce serveur AVANT d'envoyer "
                   "les liens : elle sera inscrite dans chacun d'eux.",
    }


@app.get("/api/rh/groupes_declares")
def obtenir_groupes_declares(session_vera: Optional[str] = Cookie(None)):
    """Liste figee et empreinte associee, pour le tableau de bord."""
    exiger_session(session_vera)
    groupes = persistance.charger_groupes_declares()
    return {
        "groupes": groupes,
        "declares": groupes is not None,
        "empreinte_ensemble": gestionnaire_signature.agregat_cles(),
    }


@app.get("/api/engagement_cles")
def engagement_cles():
    """Liste des cles publiques et leur empreinte agregee. PUBLIC.

    Permet a un votant -- ou plus realistement au delegue du personnel, au DPO
    ou au service informatique qui verifie pour lui -- de recalculer
    l'empreinte de l'ensemble des cles et de la comparer a la valeur publiee
    hors de ce serveur.

    L'interet est la : une empreinte publiee PAR le serveur ne l'engage pas.
    Publiee ailleurs -- depot de code, page servie par une autre
    infrastructure -- elle l'engage, car il ne peut plus ajouter une cle
    fabriquee pour un votant particulier sans que l'agregat change.

    Rien de sensible n'est expose : ces cles sont publiques par construction et
    deja distribuees une par une. Leur liste ne revele que les departements
    consultes, deja deductibles des liens en circulation.
    """
    return {
        "agregat_sha256": gestionnaire_signature.agregat_cles(),
        "cles": gestionnaire_signature.cles_publiques_toutes(),
    }


class OuvertureRequete(BaseModel):
    # Instant Unix a partir duquel les votes sont acceptes. Le client envoie
    # une date choisie dans le tableau de bord.
    ouverture_unix: float = Field(gt=0)


@app.post("/api/rh/ouverture")
def definir_ouverture(payload: OuvertureRequete, session_vera: Optional[str] = Cookie(None)):
    """Fixe la date a partir de laquelle les votes sont acceptes.

    POURQUOI CETTE DATE EXISTE
    L'anonymat repose sur le fait que le registre des jetons emis et celui des
    votes deposes ne peuvent pas etre rapproches. La cryptographie l'assure sur
    le CONTENU : le serveur ne voit jamais le secret qu'il signe. Elle ne
    l'assure pas sur le TEMPS : si un votant obtient son credential a 14h02:11
    et depose a 14h02:47, la proximite suffit a joindre les deux registres,
    sans rien casser. Dans un petit groupe, c'est une desanonymisation.

    Fixer l'ouverture apres la fin de l'envoi des invitations garantit qu'entre
    l'emission d'un credential et son depot, beaucoup d'autres se sont
    intercales. C'est ce qui rend l'ensemble d'anonymat egal au groupe, et non
    a une fenetre de quelques secondes.

    L'emission peut donc s'etaler sur plusieurs jours -- ce qui correspond a la
    realite d'un envoi de SMS lisse pour ne pas declencher les filtres
    anti-spam des operateurs. Seuls les DEPOTS attendent.

    Modifiable tant que la date n'est pas passee : un RH dont l'envoi prend du
    retard doit pouvoir repousser l'ouverture.
    """
    exiger_session(session_vera)
    maintenant = time.time()

    ouverture_actuelle = persistance.charger_ouverture_depots()
    if ouverture_actuelle is not None and maintenant >= ouverture_actuelle:
        raise HTTPException(
            status_code=409,
            detail="Les votes sont deja ouverts : la date ne peut plus etre modifiee. "
                   "La repousser invaliderait les voix deja deposees.",
        )

    if payload.ouverture_unix <= maintenant:
        raise HTTPException(
            status_code=422,
            detail="La date d'ouverture doit etre dans le futur. Une ouverture "
                   "immediate ne separerait pas l'emission des depots.",
        )

    persistance.persister_ouverture_depots(payload.ouverture_unix)
    return {
        "ouverture_unix": payload.ouverture_unix,
        "secondes_avant_ouverture": int(payload.ouverture_unix - maintenant),
    }


@app.get("/api/rh/ouverture")
def obtenir_ouverture(session_vera: Optional[str] = Cookie(None)):
    """Etat de l'ouverture des depots, pour le tableau de bord."""
    exiger_session(session_vera)
    ouverture = persistance.charger_ouverture_depots()
    if ouverture is None:
        return {"ouverture_unix": None, "depots_ouverts": True, "date_fixee": False}
    return {
        "ouverture_unix": ouverture,
        "depots_ouverts": time.time() >= ouverture,
        "date_fixee": True,
        "secondes_avant_ouverture": max(0, int(ouverture - time.time())),
    }


@app.get("/api/rh/echeance")
def echeance_consultation(session_vera: Optional[str] = Cookie(None)):
    """Date de fin de la consultation en cours.

    Ajoute le 26/07 : temps_restant_secondes() existait dans le gestionnaire
    mais aucun endpoint ne l'exposait. Ni le RH, ni le votant, ni le SMS
    n'indiquaient jusqu'a quand voter. A l'echeance, un votant recevait une
    erreur technique sans jamais apprendre que la consultation etait terminee.

    Renvoie ouverte=False si aucune cle n'existe encore : la consultation n'a
    pas commence, l'horloge des 7 jours ne demarre qu'a la premiere generation
    de liens."""
    exiger_session(session_vera)
    restant = gestionnaire_signature.temps_restant_secondes()
    if restant is None:
        return {
            "ouverte": False,
            "message": "Aucune consultation ouverte. Elle demarrera a la generation des premiers liens.",
        }
    fin = datetime.utcnow() + timedelta(seconds=restant)
    return {
        "ouverte": True,
        "heures_restantes": round(restant / 3600, 1),
        "jours_restants": round(restant / 86400, 1),
        "fin_utc": fin.isoformat(timespec="minutes") + "Z",
    }


@app.get("/api/rh/etat_departements")
def etat_departements(session_vera: Optional[str] = Cookie(None)):
    """Vue d'ensemble pour le tableau de bord RH : progression des votes
    par departement (nombre de votes recus, seuil K_MIN atteint ou non),
    sans jamais montrer les reponses elles-memes.

    NOTE : en mode signature aveugle (production), le serveur ne conserve
    AUCUNE trace des tokens emis -- c'est precisement ce qui garantit
    l'anonymat (impossible de lier un token a un participant). On ne peut
    donc pas afficher "tokens generes/consommes" : cette information
    n'existe pas cote serveur, par conception. On affiche la seule chose
    reelle et non identifiante : le nombre de votes recus par departement."""
    exiger_session(session_vera)

    invitations = persistance.compter_jetons_par_departement()
    etat = {}
    with verrou:
        # UNION jetons U effectifs : un departement peut avoir des invitations
        # generees sans aucun vote encore. Il DOIT alors apparaitre -- sinon le
        # RH, ne voyant rien apres avoir genere 300 liens, croit a un echec et
        # regenere, doublant les liens en circulation.
        departements = set(effectif_par_departement) | set(invitations)
        for dep in departements:
            nb_votes = effectif_par_departement.get(dep, 0)
            nb_invitations = invitations.get(dep, 0)
            publiable = nb_votes >= K_MIN
            if publiable:
                # Au-dessus du seuil : l'effectif exact n'est plus sensible.
                votes_exposes = nb_votes
            else:
                # Sous le seuil : on masque le nombre de votes (NI l'effectif
                # exact NI le manque, qui permettrait de le deduire). Le nombre
                # d'INVITATIONS reste expose : c'est la saisie du RH, pas une
                # donnee de participant. Les votes restant masques ici, aucun
                # taux de participation exact n'est calculable en regime sensible.
                votes_exposes = f"< {K_MIN}"
            etat[dep] = {
                "votes_recus": votes_exposes,
                "invitations_generees": nb_invitations,
                "seuil_k_min": K_MIN,
                "publiable": publiable,
            }

    return etat


# --------------------------------------------------------------------------
# Endpoints publics (vote, sans authentification -- le token EST
# l'autorisation, cf. ATTRIBUTION_FLOW.md)
# --------------------------------------------------------------------------

class ReponseEntrante(BaseModel):
    reponse: str


class CodeCourtEntrant(BaseModel):
    code: str


@app.get("/api/question")
def obtenir_question():
    # Modele B : la question est PUBLIQUE. Ce qui est protege, c'est le lien
    # identite<->vote (unlinkability), pas le contenu de la question elle-meme.
    # Aucun token requis ici : le droit de voter est prouve au moment du vote
    # (signature sur K dans /api/repondre), pas a la consultation de la question.
    return question_courante()


class ReponseModeleB(BaseModel):
    # Champ de bourrage (P-A) : le client complete le corps JSON pour que sa
    # taille soit CONSTANTE quelle que soit la reponse choisie. Sans lui, la
    # longueur du corps chiffre trahit "abstention" (10 octets) face a
    # "oui"/"non" (3 octets) : TLS preserve la longueur du plaintext, donc un
    # observateur passif distingue les abstentions sans dechiffrer. Le serveur
    # ignore ce champ, il n'existe que pour uniformiser la taille sur le reseau.
    pad: str = Field(default="", max_length=200)
    K_hex: str = Field(min_length=1, max_length=200)
    randomizer_hex: str = Field(min_length=1, max_length=200)
    signature_hex: str = Field(min_length=1, max_length=2000)
    reponse: str = Field(min_length=1, max_length=200)
    departement: str = Field(min_length=1, max_length=100)


@app.post("/api/repondre")
def repondre(payload: ReponseModeleB):
    import hashlib
    # Flux Modele B (brique 7). Le votant a obtenu (K, signature) via le flux
    # aveugle cote client. Il presente ici K + randomizer + signature + reponse.
    # Le serveur verifie la signature sous la cle publique du departement, puis
    # marque K comme consomme (anti-rejeu) et compte le vote, EN UNE transaction
    # atomique. Aucun lien entre K et le jeton d'autorisation : unlinkability.

    # SEPARATION DES PHASES -- avant toute autre chose.
    #
    # CE QUE CE CONTROLE FERME
    # L'organisation envoie ses SMS dans un ordre qu'elle connait, etale sur
    # plusieurs heures ou plusieurs jours. Sans date d'ouverture, chacun vote
    # dans la foulee de sa reception : l'ordre des votes reproduit alors
    # l'ordre des envois, que l'organisateur connait personne par personne.
    # Dans un groupe de douze, cela suffit a attribuer chaque reponse.
    # La date brise ce lien : apres elle, l'ordre d'arrivee des votes n'a plus
    # de rapport avec l'ordre d'envoi des invitations.
    #
    # CE QU'IL NE FERME PAS
    # La proximite entre les DEUX requetes d'un meme votant. Signature et
    # depot s'ouvrent au meme instant : quelqu'un qui arrive apres la date
    # obtient son credential a 14h02:11 et depose a 14h02:47. Un operateur
    # qui journalise les deux requetes peut les rapprocher.
    #
    # Ce canal reste ouvert, et c'est assume : le fermer exigerait deux
    # visites du votant -- obtenir son credential, revenir plus tard pour
    # deposer -- pour une menace qui suppose deja un operateur activement
    # malveillant (Niveau 2, hors garantie). Les journaux nginx sont d'ailleurs
    # coupes sur ces deux routes, ce qui retire le moyen le plus simple de
    # conserver cette information.
    #
    # None = pas de date fixee : depots ouverts immediatement. C'est le
    # comportement des consultations anterieures, qu'on ne casse pas.
    ouverture = persistance.charger_ouverture_depots()
    if ouverture is not None and time.time() < ouverture:
        raise HTTPException(
            status_code=425,  # Too Early
            detail="La consultation n'a pas encore commence. Votre lien reste "
                   "valable : revenez a la date indiquee dans votre invitation.",
        )

    try:
        K = bytes.fromhex(payload.K_hex)
        randomizer = bytes.fromhex(payload.randomizer_hex)
        signature = bytes.fromhex(payload.signature_hex)
    except ValueError:
        raise HTTPException(status_code=422, detail="Champs hex invalides.")

    valeurs_valides = {opt["valeur"] for opt in question_courante()["options"]}
    if payload.reponse not in valeurs_valides:
        raise HTTPException(status_code=422, detail="Reponse invalide")

    # LECTURE SEULE de la cle : un departement inconnu -> 404, JAMAIS de
    # generation a la volee ici (endpoint non authentifie -> sinon DoS keygen
    # + croissance illimitee de cle_rsa_active). Note assumee : le 404 revele
    # l'existence d'un nom de departement, information deja publique via les
    # liens de vote distribues ; c'est le moindre mal face au DoS.
    try:
        cle_pub_der = gestionnaire_signature.cle_publique_si_existe(payload.departement)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Aucune consultation active.")
    except KeyError:
        raise HTTPException(status_code=404, detail="Departement inconnu.")

    # Validation des longueurs AVANT d'appeler la primitive : sans elle, une
    # entree malformee (mauvaise taille) fait lever ValueError dans la lib Rust
    # -> 500 avec trace interne, et un oracle distinguant "malforme" de
    # "signature invalide". On renvoie le MEME 403 dans les deux cas.
    if len(K) != 32 or len(randomizer) != 32 or len(signature) != 256:
        raise HTTPException(status_code=403, detail="Signature invalide.")

    try:
        valide = vbs.verifier_signature(
            list(cle_pub_der), list(K), list(signature), list(randomizer))
    except Exception:
        raise HTTPException(status_code=403, detail="Signature invalide.")
    if not valide:
        raise HTTPException(status_code=403, detail="Signature invalide.")

    empreinte_k = hashlib.sha384(K).hexdigest()

    with verrou:
        # Fast-path memoire (evite un aller SQLite sur rejeu evident), mais
        # l'AUTORITE anti-rejeu est la contrainte PRIMARY KEY de la DB dans
        # enregistrer_vote_atomique. Ordre critique : on PERSISTE D'ABORD,
        # on ne mute la memoire QU'APRES le commit reussi. Si la persistance
        # leve (disque plein, corruption), memoire et DB restent coherentes
        # (aucune des deux n'a compte le vote) et le votant peut re-essayer
        # avec le meme K.
        if empreinte_k in gestionnaire_signature._tokens_consommes:
            raise HTTPException(status_code=409, detail="Deja vote (K consomme).")

        # Correctif P-D : plus aucun compteur calcule depuis la RAM n'est
        # ecrit en base. enregistrer_vote_atomique incremente en SQL
        # (compte = compte + 1) et RENVOIE les valeurs vraies relues apres
        # commit. La memoire se resynchronise dessus : elle ne peut plus
        # corrompre le total meme si elle etait en retard.
        try:
            compte_reel, effectif_reel = persistance.enregistrer_vote_atomique(
                payload.departement, payload.reponse, empreinte_k)
        except persistance.DoubleVoteErreur:
            # La DB connaissait deja ce K (cache memoire incoherent ou
            # restauration de DB) : on resynchronise le cache et on refuse.
            gestionnaire_signature._tokens_consommes[empreinte_k] = True
            raise HTTPException(status_code=409, detail="Deja vote (K consomme).")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Erreur de persistance, vote NON enregistre. Reessayez.")

        # Commit DB reussi : la memoire peut suivre.
        compteurs_par_departement.setdefault(payload.departement, {})
        compteurs_par_departement[payload.departement][payload.reponse] = compte_reel
        effectif_par_departement[payload.departement] = effectif_reel
        gestionnaire_signature._tokens_consommes[empreinte_k] = True

    return {"statut": "enregistre"}


@app.get("/api/health")
def health():
    return {"statut": "ok", "horodatage": datetime.utcnow().isoformat(), "signature_aveugle": "obligatoire_rsabssa_rfc9474"}

