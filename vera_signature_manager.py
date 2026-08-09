#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_signature_manager.py - Signature aveugle RSABSSA + persistance cle RSA (Porte 14)."""

import base64
import hashlib
import json
import secrets
import threading
import time

import vera_blind_sig as vbs

# Duree de vie d'une consultation. Passe ce delai le timer detruit les cles
# (memoire ET base) et plus aucun vote n'est accepte : les votants recoivent un
# 503 "Aucune consultation active".
#
# Portee a 7 jours le 24/07/2026, contre 48h auparavant. Raison : la valeur
# precedente entrait en contradiction avec K_MIN=240. Reunir 240 reponses en
# 48h suppose un taux de participation de 80% sur un departement de 300
# personnes en deux jours -- irrealiste dans une organisation reelle, ou les
# gens ouvrent leur SMS quand ils peuvent et ou il faut relancer les
# retardataires. Une consultation risquait donc de ne JAMAIS rien publier, le
# RH voyant seulement "effectif insuffisant" a l'expiration sans comprendre.
#
# Le gain de securite de 48h vs 7 jours est marginal : la cle est chiffree au
# repos (Fernet), et l'operateur capable de la dechiffrer detient VERA_DB_KEY
# de toute facon. Le cout d'usage, lui, etait majeur.
DUREE_VIE_CLE_SECONDES = 7 * 24 * 3600

try:
    import vera_persistance as _persistance
    _PERSISTANCE_DISPONIBLE = True
except ImportError:
    _persistance = None
    _PERSISTANCE_DISPONIBLE = False


def encoder_token_pour_url(token_complet):
    json_str = json.dumps(token_complet, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("ascii")


def decoder_token_depuis_url(token_encode):
    try:
        json_str = base64.urlsafe_b64decode(token_encode.encode("ascii")).decode("utf-8")
        token_complet = json.loads(json_str)
    except Exception as e:
        raise ValueError("Token encode invalide: " + str(e))
    for champ in ("message", "signature", "randomizer"):
        if champ not in token_complet:
            raise ValueError("Champ manquant dans le token: " + champ)
    return token_complet


class TokenDejaUtiliseError(Exception):
    pass


class SignatureInvalideError(Exception):
    pass


# Nom reserve sous lequel la cle maitresse RSAPBSSA est persistee dans
# cle_rsa_active. Le caractere NUL ne peut apparaitre dans aucun nom de
# departement : le motif de validation cote API l'exclut.
NOM_CLE_MAITRESSE = "\x00__MAITRESSE__"


class ClePasEncorePreteError(Exception):
    """La cle maitresse est en cours de generation. Situation transitoire et
    normale, a traduire en message d'attente et non en erreur."""


class GestionnaireSignature:
    def __init__(self):
        self._verrou = threading.Lock()
        self._cles = {}
        # Cles PUBLIQUES d'une consultation expiree. Conservees apres
        # destruction des privees pour que les votes deja signes puissent
        # encore etre verifies et deposes (voir _detruire_cle_privee).
        # Videes a la cloture explicite, qui met fin a la consultation.
        self._cles_publiques_expirees = {}
        # Cle maitresse RSAPBSSA : une seule pour toute la consultation, les
        # cles de departement s'en derivent. None tant qu'elle n'est pas prete.
        self._cle_maitresse = None
        self._generation_en_cours = False
        self._consultation_ouverte = False
        self._ouverture_ts = None
        self._timer_destruction = None
        if _PERSISTANCE_DISPONIBLE:
            self._tokens_consommes = {e: True for e in _persistance.charger_tokens_consommes()}
        else:
            self._tokens_consommes = {}

    def ouvrir_consultation(self):
        with self._verrou:
            if self._consultation_ouverte:
                raise RuntimeError("Une consultation est deja active.")
            self._cles = {}
            # Une nouvelle consultation ne doit rien heriter de la precedente.
            self._cles_publiques_expirees = {}
            ts_recharge = None
            if _PERSISTANCE_DISPONIBLE:
                toutes = _persistance.charger_toutes_cles_chiffrees()
                # La cle maitresse est rangee dans la meme table sous un nom
                # reserve : on la sort du lot avant de traiter les autres.
                if NOM_CLE_MAITRESSE in toutes:
                    priv_m, pub_m, _ouv = toutes.pop(NOM_CLE_MAITRESSE)
                    self._cle_maitresse = (bytes(priv_m), bytes(pub_m))
                for dep, (priv, pub, ouv) in toutes.items():
                    if time.time() - ouv < DUREE_VIE_CLE_SECONDES:
                        self._cles[dep] = (priv, pub)
                        if ts_recharge is None or ouv < ts_recharge:
                            ts_recharge = ouv
                    else:
                        _persistance.effacer_cle_rsa()
                        self._cles = {}
                        ts_recharge = None
                        break
            # L'horloge des 7 jours part de la PREMIERE CLE, pas du demarrage
            # du serveur. Avant le 26/07, _ouverture_ts valait time.time() des
            # le lancement du service : un serveur en ligne depuis six jours ne
            # laissait que 24h au RH qui ouvrait sa consultation ce jour-la, et
            # les votants arrivant apres l'echeance recevaient une erreur
            # technique sans jamais apprendre que la consultation etait finie.
            # Sans cle en base, la consultation n'a pas commence : on n'arme
            # rien. Le timer est arme a la creation de la premiere cle (voir
            # _armer_expiration, appele depuis _obtenir_ou_creer_cle).
            self._ouverture_ts = ts_recharge
            self._consultation_ouverte = True
        if self._ouverture_ts is not None:
            self._armer_expiration()

    def _armer_expiration(self):
        """Arme (ou reamorce) le timer de destruction depuis _ouverture_ts.
        Appele au demarrage si des cles existent deja, et a la creation de la
        toute premiere cle d'une consultation neuve."""
        if self._timer_destruction is not None:
            self._timer_destruction.cancel()
        temps_ecoule = time.time() - self._ouverture_ts
        temps_restant = max(0.0, DUREE_VIE_CLE_SECONDES - temps_ecoule)
        self._timer_destruction = threading.Timer(temps_restant, self._expirer_cle)
        self._timer_destruction.daemon = True
        self._timer_destruction.start()


    def fermer_consultation(self):
        """Cloture EXPLICITE : detruit tout, privees ET publiques.

        Difference avec l'expiration automatique : celle-ci conserve les cles
        publiques pour laisser aboutir les votes deja signes. La cloture, elle,
        met fin a la consultation -- plus rien ne doit pouvoir etre depose, et
        le serveur ne doit plus rien conserver. C'est la garantie de
        minimisation rendue verifiable.
        """
        if self._timer_destruction:
            self._timer_destruction.cancel()
            self._timer_destruction = None
        self._detruire_cle_privee()
        with self._verrou:
            self._cles_publiques_expirees = {}
            # La cle MAITRESSE aussi : sans cela, elle survivrait en memoire
            # jusqu'au prochain redemarrage et le serveur continuerait de
            # servir des cles derivees apres la cloture. La promesse « le
            # serveur ne conserve plus rien » serait fausse.
            if self._cle_maitresse is not None:
                priv, _pub = self._cle_maitresse
                # Ecrasement explicite avant liberation, meme demarche que
                # pour les cles de departement.
                self._cle_maitresse = None
                del priv
        if _PERSISTANCE_DISPONIBLE:
            _persistance.effacer_cle_rsa()

    def _expirer_cle(self):
        """Appelee par le TIMER a l'echeance des 48h. Detruit la cle en memoire
        ET la purge de la base.

        Correctif du 24/07 : le timer n'appelait que _detruire_cle_privee, qui
        zeroise la RAM. La cle privee chiffree survivait donc dans
        cle_rsa_active jusqu'au prochain ouvrir_consultation, c'est-a-dire
        jusqu'a un redemarrage. La garantie affichee -- "a 48h la cle est
        detruite" -- n'etait vraie qu'en memoire : un snapshot disque ou une
        sauvegarde prise entre l'echeance et le reboot contenait encore la cle.
        Meme motif que la Porte 19 : une garantie qui repose sur une hypothese
        d'environnement ("il y aura un redemarrage").

        Methode distincte de _detruire_cle_privee pour ne pas dupliquer
        l'effacement : fermer_consultation appelle deja les deux etapes
        separement."""
        self._detruire_cle_privee()
        if _PERSISTANCE_DISPONIBLE:
            _persistance.effacer_cle_rsa()

    def _detruire_cle_privee(self):
        """Detruit les cles PRIVEES a l'expiration, conserve les PUBLIQUES.

        La destruction de la partie privee a un objectif precis : plus aucune
        signature ne peut etre emise apres l'echeance. Elle ne doit PAS
        empecher de VERIFIER les signatures deja emises.

        Le comportement precedent vidait `self._cles` en entier, publiques
        comprises. Consequence : un votant ayant obtenu sa signature quelques
        minutes avant l'echeance ne pouvait plus deposer son vote --
        cle_publique_si_existe levait, la verification echouait, et sa voix
        etait perdue alors que son credential etait parfaitement valide. Son
        jeton d'autorisation, lui, avait bien ete consomme : il ne pouvait pas
        recommencer.

        Les publiques sont donc deplacees dans un registre dedie qui survit
        jusqu'a la cloture explicite. Elles ne sont pas un secret -- elles sont
        distribuees dans chaque lien de vote (empreinte en fragment) et servent
        precisement a permettre a quiconque de verifier une signature.
        """
        with self._verrou:
            for dep, (priv, pub) in list(self._cles.items()):
                if priv is not None:
                    # Ecrasement explicite avant liberation. Python ne garantit
                    # pas l'effacement memoire immediat, mais on ne laisse pas
                    # la reference intacte pour autant.
                    self._cles[dep] = (b"\x00" * len(priv), pub)
                # La publique survit : elle seule permet de verifier les
                # signatures deja en circulation.
                self._cles_publiques_expirees[dep] = pub
            self._cles = {}
            self._consultation_ouverte = False

    def consultation_active(self):
        return self._consultation_ouverte

    def temps_restant_secondes(self):
        if self._ouverture_ts is None:
            return None
        ecoule = time.time() - self._ouverture_ts
        return max(0.0, DUREE_VIE_CLE_SECONDES - ecoule)

    # --- Cle maitresse RSAPBSSA, preparee en arriere-plan --------------------
    #
    # RSAPBSSA exige des nombres premiers SURS : il faut trouver p tel que
    # (p-1)/2 soit lui-meme premier. C'est bien plus rare, donc bien plus lent
    # -- 21,6 secondes mesurees contre 0,07 pour RSABSSA, un facteur 300.
    #
    # En contrepartie il n'y a qu'UNE cle pour toute la consultation au lieu
    # d'une par departement : le cout total ne depend plus du nombre de
    # groupes. Mais ces 21 secondes tomberaient au moment ou le RH demande ses
    # premiers liens, et il attendrait devant son ecran sans comprendre.
    #
    # On lance donc la generation des que la question est definie. Le RH
    # prepare ensuite ses lots ; quand il demande ses liens, la cle est prete.
    # L'attente existe toujours, elle est simplement placee la ou personne ne
    # la voit.

    def preparer_cle_maitresse(self):
        """Lance la generation de la cle maitresse en arriere-plan.

        Idempotente : plusieurs appels ne declenchent qu'une generation. Sans
        cela, deux definitions de question successives lanceraient deux calculs
        de 21 secondes en parallele pour rien.
        """
        with self._verrou:
            if self._cle_maitresse is not None or self._generation_en_cours:
                return
            self._generation_en_cours = True

        def _generer():
            try:
                priv, pub = vbs.pb_generer_cles()
                with self._verrou:
                    self._cle_maitresse = (bytes(priv), bytes(pub))
                    if self._ouverture_ts is None:
                        self._ouverture_ts = time.time()
                        self._armer_expiration()
                    ts = self._ouverture_ts
                # Persistee sous un nom reserve, dans la table existante : pas
                # de migration de schema sur une base de production. Le prefixe
                # NUL rend toute collision impossible avec un nom saisi par un
                # RH (le motif de validation refuse ce caractere).
                if _PERSISTANCE_DISPONIBLE:
                    _persistance.persister_cle_rsa_chiffree(
                        NOM_CLE_MAITRESSE, bytes(priv), bytes(pub), ts)
                print("Cle maitresse RSAPBSSA prete.")
            except Exception as e:
                # Un echec ne doit pas laisser le drapeau leve : sinon plus
                # aucune tentative ne serait possible jusqu'au redemarrage.
                print(f"ERREUR : generation de la cle maitresse impossible : {e}")
            finally:
                with self._verrou:
                    self._generation_en_cours = False

        threading.Thread(target=_generer, daemon=True).start()

    def cle_maitresse_publique(self):
        """(privee, publique) de la cle maitresse. Leve si elle n'est pas prete.

        Utilisee par la verification au depot : elle derive la cle du
        departement a la volee au lieu de la lire en base.
        """
        with self._verrou:
            if self._cle_maitresse is None:
                raise ClePasEncorePreteError("Cle maitresse indisponible.")
            return self._cle_maitresse

    def etat_cle_maitresse(self):
        """(prete, en_cours) -- pour informer le RH et le votant.

        Trois etats possibles, et chacun merite un message distinct :
        prete, en cours de preparation, ou pas encore demandee.
        """
        with self._verrou:
            return (self._cle_maitresse is not None, self._generation_en_cours)

    def _obtenir_ou_creer_cle(self, departement):
        """Renvoie (priv, pub) du departement, DERIVEE de la cle maitresse.

        Ce n'est plus une generation mais une derivation : la cle publique du
        departement est une fonction deterministe de (modulus maitre, nom du
        departement). Consequence directe -- le votant peut la RECALCULER au
        lieu de faire confiance a celle que le serveur lui envoie.

        C'est ce qui ferme l'attaque par marquage : un serveur ne peut plus
        fabriquer une cle par personne, puisqu'une cle ne vaut que si elle
        correspond a une metadonnee legitime.

        La derivation coute quelques millisecondes ; c'est la GENERATION de la
        maitresse qui prend une vingtaine de secondes, et elle a lieu une seule
        fois, en arriere-plan, des la definition de la question.

        DOIT etre appelee sous self._verrou.
        """
        if departement in self._cles:
            return self._cles[departement]

        if self._cle_maitresse is None:
            # Le RH a demande des liens avant que la cle soit prete. L'appelant
            # traduit cela en message d'attente : c'est une situation normale,
            # pas une panne.
            raise ClePasEncorePreteError(
                "La cle de la consultation est en cours de preparation. "
                "Reessayez dans quelques secondes."
            )

        # On renvoie la cle MAITRESSE, pas la derivee : le client derive
        # lui-meme a l'interieur de blind(). Lui envoyer la derivee produit
        # « number does not fit in 255 bytes ».
        # Consequence heureuse : tous les votants recoivent la MEME cle, donc
        # la meme empreinte dans leur lien -- deux collegues peuvent comparer.
        priv_m, pub_m = self._cle_maitresse
        self._cles[departement] = (priv_m, pub_m)
        return priv_m, pub_m

    def cle_publique(self, departement):
        """CREATRICE si absente. A reserver aux flux AUTHENTIFIES (RH,
        /api/rh/generer_autorisations). Ne JAMAIS appeler depuis un endpoint
        public : voir cle_publique_si_existe."""
        with self._verrou:
            if not self._consultation_ouverte:
                raise RuntimeError("Aucune consultation active.")
            _priv, pub = self._obtenir_ou_creer_cle(departement)
        return pub

    def agregat_cles(self):
        """Empreinte de l'ENSEMBLE des cles publiques de la consultation.

        A QUOI SERT CETTE VALEUR
        L'empreinte `#k=` de chaque lien est calculee par le serveur. Elle ne
        l'engage donc pas : un serveur malveillant peut generer une cle par
        votant et l'empreinte correspondante, le controle cote client passe, et
        au depot il retrouve quel votant a produit quelle signature en essayant
        ses cles. Desanonymisation complete sans rien casser.

        L'agregat ferme ce vecteur A CONDITION d'etre publie AILLEURS que sur
        ce serveur -- depot de code, page servie par une autre infrastructure,
        message d'un representant du personnel. Le client recupere alors la
        liste complete des cles, recalcule l'agregat, et le compare a la valeur
        publiee. Le serveur ne peut plus fabriquer de cle supplementaire : leur
        NOMBRE et leur CONTENU sont engages par une valeur qu'il ne controle
        pas.

        Publie par le serveur lui-meme, cet agregat ne vaudrait rien. C'est
        pourquoi il est affiche au RH pour publication manuelle, et non pousse
        automatiquement.

        CONSTRUCTION
        SHA-256 sur la concatenation des couples (departement, cle publique)
        tries par nom de departement. Le tri rend la valeur reproductible quel
        que soit l'ordre de creation. La longueur de chaque champ precede le
        champ lui-meme, pour qu'aucune paire de listes distinctes ne produise
        la meme concatenation.

        Renvoie None si aucune cle n'existe encore.
        """
        import hashlib
        with self._verrou:
            if not self._cles:
                return None
            h = hashlib.sha256()
            for dep in sorted(self._cles):
                _priv, pub = self._cles[dep]
                nom = dep.encode("utf-8")
                # Longueur avant contenu : sans cela, ("AB", "C") et ("A", "BC")
                # produiraient la meme suite d'octets.
                h.update(len(nom).to_bytes(4, "big"))
                h.update(nom)
                h.update(len(pub).to_bytes(4, "big"))
                h.update(bytes(pub))
            return h.hexdigest()

    def cles_publiques_toutes(self):
        """Liste (departement, cle publique hex) triee, pour que le client
        recalcule l'agregat lui-meme.

        Aucune information sensible : ces cles sont publiques par nature, et
        deja distribuees une par une via /api/cle_publique. Les exposer
        ensemble ne revele que la liste des departements consultes -- deja
        deductible des liens en circulation.
        """
        with self._verrou:
            return [
                {"departement": dep, "cle_publique_hex": bytes(self._cles[dep][1]).hex()}
                for dep in sorted(self._cles)
            ]

    def cle_publique_si_existe(self, departement):
        """Lecture SEULE : renvoie la cle publique du departement si elle
        existe deja, leve KeyError sinon. Obligatoire sur les endpoints NON
        authentifies (/api/cle_publique, /api/repondre). Sans cela, tout
        anonyme force une generation RSA + une ecriture persistee dans
        cle_rsa_active par requete avec un nom de departement arbitraire :
        DoS CPU (keygen) + croissance illimitee de la DB. La cle d'un
        departement legitime existe toujours a ce stade, creee par le RH
        lors de generer_autorisations.

        APRES EXPIRATION : la cle publique reste disponible via le registre
        des publiques expirees, pour que les votes deja signes puissent
        encore etre VERIFIES et deposes. Sans cela, un votant ayant obtenu sa
        signature juste avant l'echeance perdait sa voix : son jeton
        d'autorisation etait consomme, mais le depot echouait faute de cle
        pour verifier. Emettre de NOUVELLES signatures reste impossible (la
        cle privee, elle, est bien detruite) -- c'est la seule chose que
        l'expiration doit empecher.
        """
        with self._verrou:
            if departement in self._cles:
                _priv, pub = self._cles[departement]
                return pub
            # Consultation expiree : on peut encore verifier ce qui a ete signe.
            if departement in self._cles_publiques_expirees:
                return self._cles_publiques_expirees[departement]
            # RSAPBSSA : la cle d'un departement se DERIVE de la maitresse. Il
            # n'y a donc plus de « departement inconnu » a memoriser -- si la
            # maitresse existe, toute metadonnee est servable. Sans cela, un
            # redemarrage du service renverrait 404 aux votants dont le lien
            # est en circulation, alors que leur cle est parfaitement calculable.
            # La cloture met _cle_maitresse a None : ce test suffit donc a
            # distinguer « consultation vivante » de « consultation close ».
            # Sans lui, le serveur continuerait de servir des cles apres la
            # cloture, contredisant sa promesse de ne plus rien conserver.
            if self._cle_maitresse is not None and self._consultation_ouverte:
                _priv, pub_m = self._cle_maitresse
                self._cles[departement] = (_priv, pub_m)
                return pub_m
            if not self._consultation_ouverte:
                raise RuntimeError("Aucune consultation active.")
            raise KeyError(departement)

    def signer_message_aveugle(self, departement, message_aveugle_bytes):
        """Signe a l'aveugle un message DEJA aveugle par le client (navigateur
        du votant). C'est la SEULE etape du protocole RSABSSA qui reste cote
        serveur dans le nouveau flux : le serveur ne voit jamais le message en
        clair (il est aveugle), ne fait PAS l'aveuglement (le client l'a fait)
        ni la finalisation (le client la fera). Il ne peut donc pas relier ce
        qu'il signe au token final -> unlinkability effective.
        Renvoie la signature aveugle (bytes)."""
        with self._verrou:
            if not self._consultation_ouverte:
                raise RuntimeError("Impossible de signer: aucune consultation active.")
            # _obtenir_ou_creer_cle renvoie desormais (privee MAITRESSE, publique
            # DERIVEE). La signature se fait avec la cle secrete derivee pour ce
            # departement, que pb_signer_aveugle recalcule a partir de la paire
            # maitresse -- la derivation exige les facteurs premiers, donc les
            # deux moities.
            priv_m, _pub_derivee = self._obtenir_ou_creer_cle(departement)
            _priv, pub_m = self._cle_maitresse
            meta = list(departement.encode("utf-8"))
            sig_aveugle = bytes(vbs.pb_signer_aveugle(
                list(priv_m), list(pub_m), list(message_aveugle_bytes), meta))
        return sig_aveugle

    def generer_token_signe(self, departement):
        raise RuntimeError(
            "generer_token_signe est obsolete (ancien Modele A). Flux Modele B : "
            "aveuglement cote client, voir signer_message_aveugle(departement, msg)."
        )

    def verifier_et_consommer(self, token_complet):
        raise RuntimeError(
            "verifier_et_consommer est obsolete (ancien Modele A). Flux Modele B : "
            "verification dans /api/repondre sous la cle publique du departement."
        )
