#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_cycle_vie_cle.py -- comportement des cles apres expiration.

CE QUE CE TEST SPECIFIE
A l'echeance des 7 jours, la cle PRIVEE est detruite : plus aucune signature
ne peut etre emise. Mais la cle PUBLIQUE survit, pour que les votes DEJA
signes puissent encore etre verifies et deposes.

LE PROBLEME QUE CELA CORRIGE
_detruire_cle_privee vidait le registre entier, publiques comprises. Un votant
ayant obtenu sa signature quelques minutes avant l'echeance ne pouvait plus
deposer son vote : cle_publique_si_existe levait, la verification echouait,
sa voix etait perdue. Son jeton d'autorisation, lui, avait bien ete consomme
-- il ne pouvait pas recommencer.

La cle publique n'est pas un secret : elle est distribuee dans chaque lien de
vote (empreinte dans le fragment) et sert precisement a permettre a quiconque
de verifier une signature. La conserver n'affaiblit rien.

DISTINCTION AVEC LA CLOTURE
L'expiration conserve les publiques (laisser aboutir les votes en vol).
La cloture explicite detruit tout (mettre fin a la consultation, ne plus rien
conserver). Les deux comportements sont volontairement differents.
"""

import sys

import vera_persistance as _p
import vera_signature_manager as vsm

_p.initialiser()

def _preparer_cle(g, timeout=90):
    """Prepare la cle maitresse et attend qu'elle soit prete.

    En production, preparer_cle_maitresse() est declenchee a la definition de
    la question et la generation se fait en arriere-plan pendant que le RH
    prepare ses lots. Un test n'a pas cette fenetre : il doit attendre.

    La generation prend une vingtaine de secondes -- davantage depuis qu'on
    rejette les modulus de 2047 bits, qui font echouer le client JavaScript.
    """
    import time as _t
    g.preparer_cle_maitresse()
    debut = _t.time()
    while _t.time() - debut < timeout:
        prete, _en_cours = g.etat_cle_maitresse()
        if prete:
            return
        _t.sleep(0.5)
    raise RuntimeError(f"cle maitresse non prete apres {timeout} s")



class Echec(Exception):
    pass


def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test cycle de vie des cles -- expiration vs cloture")
    print("-" * 55)
    ok = True

    DEPT = "Service Test"

    # 1. En consultation active, la cle publique est disponible.
    try:
        g = vsm.GestionnaireSignature()
        g.ouvrir_consultation()
        _preparer_cle(g)
        g.cle_publique(DEPT)
        pub_avant = g.cle_publique_si_existe(DEPT)
        if not pub_avant:
            raise Echec("cle publique indisponible en consultation active")
        _ok("1. consultation active : cle publique disponible")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. LE TEST CENTRAL : apres expiration, la publique reste accessible.
    #    C'est ce qui permet a un vote deja signe d'aboutir.
    try:
        g._detruire_cle_privee()  # simule l'echeance des 7 jours
        pub_apres = g.cle_publique_si_existe(DEPT)
        if pub_apres != pub_avant:
            raise Echec("la cle publique a change apres expiration")
        _ok("2. apres expiration : la cle publique reste verifiable")
    except KeyError:
        print("ECHEC 2. cle publique introuvable apres expiration : les votes "
              "deja signes ne peuvent plus etre deposes, les voix sont perdues")
        ok = False
    except RuntimeError as e:
        print(f"ECHEC 2. RuntimeError apres expiration : {e}")
        ok = False
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. Mais plus aucune signature ne peut etre EMISE.
    #    C'est le seul objectif de l'expiration : fermer l'emission, pas la
    #    verification. Sans ce test, garder la publique pourrait masquer une
    #    privee restee vivante.
    try:
        try:
            g.signer_message_aveugle(DEPT, b"x" * 256)
            raise Echec(
                "une signature a ete EMISE apres expiration : la cle privee "
                "n'est pas reellement detruite"
            )
        except Echec:
            raise
        except Exception:
            pass  # tout refus est acceptable ici
        _ok("3. apres expiration : plus aucune signature emise")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. La consultation est bien marquee fermee.
    try:
        if g.consultation_active():
            raise Echec("la consultation est encore active apres expiration")
        _ok("4. la consultation est marquee fermee")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    # 5. La CLOTURE, elle, efface tout -- publiques comprises.
    #    Distinction volontaire : l'expiration laisse aboutir les votes en vol,
    #    la cloture met fin a la consultation et ne conserve plus rien.
    try:
        g2 = vsm.GestionnaireSignature()
        g2.ouvrir_consultation()
        _preparer_cle(g2)
        g2.cle_publique(DEPT)
        g2.fermer_consultation()
        try:
            g2.cle_publique_si_existe(DEPT)
            raise Echec(
                "la cle publique survit a la CLOTURE : le serveur conserve "
                "encore quelque chose de la consultation passee"
            )
        except Echec:
            raise
        except (KeyError, RuntimeError):
            pass  # comportement attendu
        _ok("5. la cloture efface aussi les cles publiques")
    except Echec as e:
        print(f"ECHEC 5. {e}")
        ok = False

    # 6. Une nouvelle consultation n'herite de rien.
    try:
        g3 = vsm.GestionnaireSignature()
        g3.ouvrir_consultation()
        try:
            g3.cle_publique_si_existe("Departement Fantome")
            raise Echec("une cle inconnue est renvoyee sur consultation neuve")
        except Echec:
            raise
        except (KeyError, RuntimeError):
            pass
        _ok("6. une consultation neuve n'herite d'aucune cle")
    except Echec as e:
        print(f"ECHEC 6. {e}")
        ok = False

    print("-" * 55)
    if ok:
        print("CYCLE DE VIE : l'expiration ferme l'emission, la cloture efface tout.")
        return 0
    print("ECHEC : le cycle de vie des cles ne respecte plus la specification.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
