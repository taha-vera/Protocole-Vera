#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_registres_disjoints.py -- les deux registres ne doivent jamais se
retrouver dans un meme fichier journal.

L'INVARIANT PROTEGE
VERA repose sur une disjonction : le registre des jetons emis porte l'identite
(l'organisation detient la liste personne -> jeton), le registre des votes
porte la reponse. Les joindre, c'est savoir qui a repondu quoi.

La cryptographie assure cette disjonction sur le CONTENU : le serveur ne voit
jamais le secret qu'il signe. Elle ne l'assure pas sur le STOCKAGE.

CE QUI S'EST PASSE
En journal_mode=WAL, chaque validation ecrit l'image des pages modifiees dans
un journal qui survit entre les transactions. La consommation d'un jeton
(registre 1) et l'increment du compteur de reponses (registre 2) s'ecrivaient
donc dans le meme fichier, a quelques millisecondes d'intervalle. Un lecteur du
seul journal reconstituait :

    jeton d'ALICE consomme  ->  compteur "oui" +1
    jeton de BOB consomme   ->  compteur "non" +1

Une lecture unique suffisait : instantane d'hebergeur, sauvegarde, agent de
supervision lisant /root. Aucune clef, aucun acces applicatif.

Un premier correctif avait sorti du journal la table des signatures emises,
en documentant precisement ce risque -- sans voir que la table des jetons
faisait la meme chose. C'est pourquoi ce test verifie la CLASSE du probleme et
non une table en particulier : il echoue des qu'un journal persistant apparait,
quelle qu'en soit la cause.

CE QUE CE TEST NE FAIT PAS
Il ne verifie pas le systeme de fichiers sous-jacent (journalisation ext4,
copie sur ecriture d'un snapshot LVM ou d'un hyperviseur). Ces couches peuvent
conserver des versions anterieures du fichier de base ; c'est une limite
d'exploitation, documentee dans le guide de deploiement.
"""

import os
import sys

import vera_persistance as p


class Echec(Exception):
    pass


def _ok(nom):
    print("OK   " + nom)


def _fichiers_journaux(chemin_db):
    """Journaux persistants a cote de la base, quel que soit le mode."""
    trouves = []
    for suffixe in ("-wal", "-shm", "-journal"):
        f = chemin_db + suffixe
        if os.path.exists(f) and os.path.getsize(f) > 0:
            trouves.append((f, os.path.getsize(f)))
    return trouves


def main():
    print("Test : les deux registres ne partagent aucun journal")
    print("-" * 58)
    ok = True

    chemin = os.environ.get("VERA_DB_PATH", "")
    if not chemin:
        print("ECHEC : VERA_DB_PATH doit etre defini pour ce test.")
        return 2

    p.initialiser()

    # 1. Le mode de journalisation ne doit pas laisser de fichier persistant.
    try:
        with p._verrou_db:
            mode = p._conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        if mode == "wal":
            raise Echec(
                "journal_mode=WAL : le journal survit entre les transactions "
                "et joint les deux registres. Voir l'en-tete de ce test."
            )
        _ok(f"1. journal_mode = {mode} (aucun journal persistant)")
    except Echec as e:
        print(f"ECHEC 1. {e}")
        ok = False

    # 2. LE TEST CENTRAL : apres une sequence reelle -- consommation d'un jeton
    #    puis depot d'un vote -- aucun journal ne doit subsister sur disque.
    try:
        for nom, reponse in (("ALICE", "oui"), ("BOB", "non"), ("CAROL", "abstention")):
            jeton = f"JETON_{nom}_" + "x" * 24
            p.persister_jeton_autorisation(jeton, "Service")
            p.consommer_jeton_autorisation(jeton)
            p.enregistrer_vote_atomique("Service", reponse, f"emp_{nom:0>60}")

        journaux = _fichiers_journaux(chemin)
        if journaux:
            detail = ", ".join(f"{f} ({t} o)" for f, t in journaux)
            raise Echec(
                f"un journal persiste apres les ecritures : {detail}. "
                "Les images successives des pages y sont differentiables, "
                "donc l'ordre des consommations de jetons et celui des votes "
                "sont appariables."
            )
        _ok("2. apres consommations et votes : aucun journal sur disque")
    except Echec as e:
        print(f"ECHEC 2. {e}")
        ok = False

    # 3. L'empreinte d'un jeton ne doit apparaitre dans AUCUN fichier annexe.
    #    Le fichier de base lui-meme en contient une (la table des jetons),
    #    c'est normal et documente : ce qui ne doit pas exister, c'est un
    #    second fichier ou l'on puisse lire la CHRONOLOGIE.
    try:
        residus = []
        for suffixe in ("-wal", "-shm", "-journal"):
            f = chemin + suffixe
            if not os.path.exists(f):
                continue
            brut = open(f, "rb").read()
            for nom in ("ALICE", "BOB", "CAROL"):
                if f"JETON_{nom}".encode() in brut:
                    residus.append(f"{nom} dans {f}")
        if residus:
            raise Echec("empreintes de jeton dans un fichier annexe : "
                        + ", ".join(residus))
        _ok("3. aucune empreinte de jeton dans un fichier annexe")
    except Echec as e:
        print(f"ECHEC 3. {e}")
        ok = False

    # 4. Les donnees restent correctes -- un test de confidentialite qui
    #    casserait la fonctionnalite ne vaudrait rien.
    try:
        compteurs, effectifs = p.charger_compteurs()
        total = sum(compteurs.get("Service", {}).values())
        if total != 3:
            raise Echec(f"{total} votes comptes au lieu de 3")
        if effectifs.get("Service") != 3:
            raise Echec(f"effectif {effectifs.get('Service')} au lieu de 3")
        _ok("4. les trois votes sont correctement enregistres")
    except Echec as e:
        print(f"ECHEC 4. {e}")
        ok = False

    print("-" * 58)
    if ok:
        print("REGISTRES DISJOINTS : aucun journal ne permet d'apparier")
        print("la consommation d'un jeton et le depot d'un vote.")
        return 0
    print("ECHEC : les deux registres sont appariables au niveau du stockage.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
