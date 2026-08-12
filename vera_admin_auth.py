#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_admin_auth.py — Authentification pour l'interface RH (generation de
tokens de vote). Separe de l'authentification des participants (qui n'en
ont pas besoin, juste leur token de vote individuel).

Principe : un compte RH par organisation, mot de passe hashe (jamais en
clair, ni en memoire au-dela du necessaire ni en log), session par jeton
opaque distinct des tokens de vote (pour ne jamais melanger les deux
espaces de noms).
"""

import hashlib
import hmac
import os
import secrets
import threading
import time

# --------------------------------------------------------------------------
# Stockage des comptes RH (en memoire pour ce prototype -- a migrer vers
# une vraie base si le besoin de persistance au-dela d'un redemarrage
# devient reel)
# --------------------------------------------------------------------------

_verrou = threading.Lock()

# identifiant_compte -> {"hash_mdp": bytes, "sel": bytes}
_comptes_rh: dict[str, dict] = {}

# jeton_session -> {"compte": str, "expire_a": float}
_sessions: dict[str, dict] = {}

DUREE_SESSION_SECONDES = 8 * 3600  # 8h, une journee de travail


def _hacher_mot_de_passe(mot_de_passe: str, sel: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256, 200k iterations -- standard raisonnable pour un
    prototype, a durcir (argon2) si le projet passe en production reelle."""
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, 200_000)


def creer_compte(identifiant: str, mot_de_passe: str) -> bool:
    """Cree un compte RH. Retourne False si l'identifiant existe deja."""
    with _verrou:
        if identifiant in _comptes_rh:
            return False
        sel = secrets.token_bytes(16)
        hash_mdp = _hacher_mot_de_passe(mot_de_passe, sel)
        _comptes_rh[identifiant] = {"hash_mdp": hash_mdp, "sel": sel}
        return True


def creer_compte_depuis_empreinte(identifiant: str, empreinte: str) -> bool:
    """Cree un compte a partir d'une empreinte pre-calculee, jamais du mot de
    passe en clair. Format attendu : "sel_hex$hash_hex".

    POURQUOI CETTE VOIE EXISTE
    Le compte d'amorçage etait cree depuis VERA_ADMIN_PASS, donc le mot de
    passe vivait en clair et en permanence dans l'unite systemd -- lisible par
    `systemctl cat`, recopie dans toute sauvegarde de configuration, visible
    sur la moindre capture d'ecran de diagnostic. C'est exactement par ce canal
    que les secrets ont fuite le 31/07/2026 : pas une faille du code, un
    fichier de configuration affiche au mauvais moment.

    Avec une empreinte, ce fichier ne contient plus rien d'utilisable. Un
    lecteur obtient PBKDF2-SHA256 a 200 000 iterations sur un sel aleatoire :
    inversible seulement par force brute, ce qui est le but d'un hachage.

    CE QUE CELA NE PROTEGE PAS
    Un attaquant qui a deja root detient VERA_DB_KEY et peut modifier le code :
    il n'a pas besoin du mot de passe. Cette mesure ferme la fuite
    accidentelle, pas la compromission. C'est le canal qui a reellement servi.

    Genere l'empreinte avec :
        python3 -c "import vera_admin_auth as a; print(a.generer_empreinte('MOT_DE_PASSE'))"
    """
    # Le decodage se fait AVANT de prendre le verrou : il ne touche a aucun
    # etat partage, et le faire sous verrou allongerait inutilement la section
    # critique. Le test d'existence et l'ecriture, eux, sont sous UN SEUL
    # verrou -- les separer laissait deux appels concurrents ecraser le premier
    # compte. Non exploitable en pratique (appel unique au demarrage), corrige
    # par principe : une section critique en deux morceaux finit toujours par
    # etre appelee d'une facon qu'on n'avait pas prevue.
    try:
        sel_hex, hash_hex = empreinte.split("$", 1)
        sel = bytes.fromhex(sel_hex)
        hash_mdp = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError) as e:
        raise ValueError(
            "Empreinte de compte mal formee. Format attendu : sel_hex$hash_hex. "
            f"Detail : {e}"
        )
    if len(sel) != 16 or len(hash_mdp) != 32:
        raise ValueError(
            f"Empreinte invalide : sel de {len(sel)} octets (16 attendus), "
            f"hash de {len(hash_mdp)} octets (32 attendus)."
        )
    with _verrou:
        if identifiant in _comptes_rh:
            return False
        _comptes_rh[identifiant] = {"hash_mdp": hash_mdp, "sel": sel}
    return True


def generer_empreinte(mot_de_passe: str) -> str:
    """Calcule l'empreinte a placer dans VERA_ADMIN_HASH. A executer une fois,
    hors ligne. Le mot de passe n'est jamais ecrit nulle part : seule
    l'empreinte l'est."""
    sel = secrets.token_bytes(16)
    return f"{sel.hex()}${_hacher_mot_de_passe(mot_de_passe, sel).hex()}"


def verifier_identifiants(identifiant: str, mot_de_passe: str) -> bool:
    """Verifie un mot de passe en temps constant (hmac.compare_digest)
    pour eviter les attaques par mesure de timing."""
    with _verrou:
        compte = _comptes_rh.get(identifiant)
        if compte is None:
            # Calcul factice pour ne pas reveler par le timing que le
            # compte n'existe pas
            _hacher_mot_de_passe(mot_de_passe, secrets.token_bytes(16))
            return False
        hash_calcule = _hacher_mot_de_passe(mot_de_passe, compte["sel"])
        return hmac.compare_digest(hash_calcule, compte["hash_mdp"])


def ouvrir_session(identifiant: str) -> str:
    """Genere un jeton de session opaque, distinct des tokens de vote."""
    jeton = "sess_" + secrets.token_urlsafe(32)
    with _verrou:
        _sessions[jeton] = {
            "compte": identifiant,
            "expire_a": time.time() + DUREE_SESSION_SECONDES,
        }
    return jeton


def session_valide(jeton_session: str) -> str | None:
    """Retourne l'identifiant du compte si la session est valide et non
    expiree, sinon None. Purge les sessions expirees au passage."""
    with _verrou:
        maintenant = time.time()
        expirees = [j for j, s in _sessions.items() if s["expire_a"] < maintenant]
        for j in expirees:
            del _sessions[j]

        session = _sessions.get(jeton_session)
        if session is None:
            return None
        return session["compte"]


def fermer_session(jeton_session: str) -> None:
    with _verrou:
        _sessions.pop(jeton_session, None)
