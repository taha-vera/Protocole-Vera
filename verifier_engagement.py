#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verifier_engagement.py -- controler qu'un serveur VERA n'a pas fabrique de cles.

A QUI CE SCRIPT S'ADRESSE
Aux delegues du personnel, delegues a la protection des donnees, services
informatiques : ceux qui verifient POUR les participants. Aucun votant ne
lancera ce script, et ce n'est pas grave -- ce qui compte est qu'un tiers
puisse le faire.

CE QU'IL VERIFIE
Chaque lien de vote contient l'empreinte de la cle publique de son groupe, et
le navigateur refuse de voter si elle ne correspond pas. Mais cette empreinte
est calculee par le serveur : elle ne l'engage donc pas. Un serveur qui
voudrait desanonymiser genererait une cle par personne, avec l'empreinte
correspondante -- le controle passerait, et au depouillement il retrouverait
qui a produit quelle signature.

Ce script ferme ce vecteur en verifiant trois choses :

  1. le serveur ne declare qu'UNE cle par groupe -- c'est le controle
     decisif, un hachage seul ne le detecte pas ;
  2. les groupes declares correspondent a ceux que l'organisation a annonces ;
  3. l'empreinte de l'ensemble correspond a celle publiee AVANT la
     distribution des liens.

CE QU'IL NE VERIFIE PAS
Que le serveur execute le code publie. Aucune verification depuis l'exterieur
ne le peut. Ce script produit une TRACE : si le serveur ment, il doit mentir de
facon coherente et durable, et toute modification du jeu de cles apres
publication devient visible.

USAGE
    python3 verifier_engagement.py https://vera-consultation.fr
    python3 verifier_engagement.py <url> --attendu <empreinte_publiee>
    python3 verifier_engagement.py <url> --groupes "Atelier,Direction,RH"
"""

import argparse
import hashlib
import json
import sys
import urllib.request


class ChampManquant(Exception):
    """Le serveur n'a pas fourni de quoi mener un controle."""


def calculer_agregat(cles):
    """Recalcule l'empreinte de l'ensemble, exactement comme le serveur.

    Tri par nom de groupe : la valeur ne depend pas de l'ordre de creation.
    Longueur avant contenu : sans cela, ("AB","C") et ("A","BC") donneraient
    la meme suite d'octets, donc la meme empreinte.
    """
    h = hashlib.sha256()
    for entree in sorted(cles, key=lambda c: c.get("departement", "")):
        # Un champ manquant est une anomalie a signaler, pas une trace Python.
        #
        # Constate le 29/08/2026 : un serveur omettant cle_publique_hex faisait
        # planter cet outil sur un KeyError. Le delegue du personnel a qui le
        # guide demande de le lancer recevait une trace d'interpreteur, sans
        # pouvoir distinguer un serveur en faute d'un outil casse. Meme famille
        # que les controles conditionnels corriges le meme jour : un outil de
        # verification doit dire ce qui manque, pas s'interrompre.
        for champ in ("departement", "cle_publique_hex"):
            if champ not in entree:
                raise ChampManquant(
                    f"le serveur annonce une cle sans champ « {champ} ». "
                    "L'empreinte agregee ne peut pas etre recalculee : ce "
                    "controle n'a pas pu avoir lieu.")
        nom = entree["departement"].encode("utf-8")
        try:
            pub = bytes.fromhex(entree["cle_publique_hex"])
        except ValueError:
            raise ChampManquant(
                f"la cle publique du groupe « {entree['departement']} » n'est "
                "pas une suite hexadecimale valide. L'empreinte agregee ne "
                "peut pas etre recalculee.")
        h.update(len(nom).to_bytes(4, "big"))
        h.update(nom)
        h.update(len(pub).to_bytes(4, "big"))
        h.update(pub)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(
        description="Verifie l'engagement sur les cles d'une consultation VERA.")
    p.add_argument("url", help="Adresse du serveur, ex. https://vera-consultation.fr")
    p.add_argument("--attendu", help="Empreinte publiee avant la distribution des liens")
    p.add_argument("--groupes", help="Groupes annonces par l'organisation, separes par des virgules")
    args = p.parse_args()

    url = args.url.rstrip("/") + "/api/engagement_cles"
    print(f"Interrogation de {url}\n")

    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            donnees = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"ECHEC : serveur injoignable ({e})")
        return 2

    cles = donnees.get("cles", [])
    annonce = donnees.get("agregat_sha256")

    if not cles:
        # « Aucune consultation ouverte » n'est PAS un feu vert.
        #
        # Le message etait exact et se lisait comme une validation par quelqu'un
        # qui venait de « faire la verification ». Un controle lance au mauvais
        # moment -- avant la declaration des groupes, apres la cloture --
        # comptait comme un controle reussi (03/09/2026).
        print("Aucune cle : aucune consultation n'est ouverte sur ce serveur.")
        print("\n  ATTENTION : ce n'est PAS une verification reussie, seulement")
        print("  le constat qu'il n'y a rien a verifier pour l'instant.")
        print("  Relancez ce script APRES l'ouverture de la consultation et")
        print("  AVANT la distribution des liens.")
        # TOUT ARGUMENT FOURNI ET JAMAIS COMPARE DOIT SE VOIR.
        #
        # Le script sortait ici en code 0 sans dire que --attendu n'avait pas
        # ete examine. Corrige le 29/08... pour --attendu SEULEMENT. Un audit
        # externe a constate le 03/09 que --groupes, declare sur la ligne d'a
        # cote, restait muet : le delegue fournissait sa liste de reference,
        # elle n'etait pas regardee, et il obtenait un code 0.
        #
        # Le correctif avait ferme l'argument, pas la classe. On les traite
        # desormais ensemble : ajouter un argument de comparaison sans
        # l'inscrire ici est une regression que ce bloc rend visible.
        non_compares = []
        if args.attendu:
            non_compares.append("--attendu (empreinte publiee)")
        if args.groupes:
            non_compares.append("--groupes (liste annoncee par l'organisation)")
        if non_compares:
            print("\nATTENTION : ce que vous avez fourni n'a PAS ete compare, "
                  "faute de cle\nsur ce serveur :")
            for a_ in non_compares:
                print(f"  - {a_}")
            print("\nCe n'est pas une verification reussie. Relancez lorsque "
                  "la consultation\nest ouverte, avant la distribution des "
                  "liens.")
            return 1
        return 0

    anomalies = []

    # --- 0. La reponse est-elle seulement exploitable ? ----------------------
    #
    # CONSTAT DU 03/09/2026, par un audit externe.
    #
    # Le 29/08, une garde a ete ajoutee dans calculer_agregat pour qu'un champ
    # manquant devienne une anomalie au lieu d'une trace Python. Elle protegeait
    # le point ou le defaut etait APPARU -- ligne 236. Elle ne protegeait pas la
    # ligne 128, cent lignes plus haut, qui accede a c["departement"] sans rien
    # verifier. Un serveur omettant ce champ faisait toujours planter l'outil,
    # avant meme que la garde n'entre en jeu.
    #
    # Le correctif avait ferme le CAS, pas la CLASSE. On valide donc la forme de
    # la reponse UNE FOIS, ici, avant tout traitement : ce que le serveur
    # renvoie est soit exploitable, soit une anomalie -- jamais une exception.
    for rang, entree in enumerate(cles, 1):
        if not isinstance(entree, dict):
            print(f"\nANOMALIE : la cle n°{rang} n'est pas un objet exploitable.")
            print("Ce controle n'a pas pu avoir lieu.")
            return 1
        for champ in ("departement", "cle_publique_hex"):
            if champ not in entree:
                print(f"\nANOMALIE : la cle n°{rang} annoncee par le serveur "
                      f"n'a pas de champ « {champ} ».")
                print("Aucun des controles ci-dessous ne peut avoir lieu. Ce "
                      "n'est pas\nune verification reussie : demandez une "
                      "explication ecrite.")
                return 1

    # --- 1. Une seule cle par groupe -----------------------------------------
    # LE CONTROLE DECISIF. Un serveur peut publier 500 couples (Marketing, cle_i)
    # : l'empreinte agregee sera parfaitement valide, et la desanonymisation
    # aussi. Le hachage fige la liste, il ne la valide pas.
    noms = [c["departement"] for c in cles]
    doublons = {n for n in noms if noms.count(n) > 1}
    print(f"Groupes declares : {len(noms)}   distincts : {len(set(noms))}")
    if doublons:
        anomalies.append(
            f"ANOMALIE GRAVE : plusieurs cles pour {', '.join(sorted(doublons))}. "
            "Un groupe n'a jamais qu'une cle legitime. Le serveur marque "
            "probablement les votants individuellement."
        )
    else:
        print("  OK : une seule cle par groupe.")

    # --- 2. Correspondance avec les groupes annonces --------------------------
    # Sans liste de reference d'origine independante, le controle precedent ne
    # detecte pas un serveur qui inventerait des groupes plausibles.
    if args.groupes:
        attendus = {g.strip() for g in args.groupes.split(",") if g.strip()}
        trouves = set(noms)
        if trouves != attendus:
            enTrop = trouves - attendus
            manquants = attendus - trouves
            detail = []
            if enTrop:
                detail.append(f"non annonces : {', '.join(sorted(enTrop))}")
            if manquants:
                detail.append(f"annonces mais absents : {', '.join(sorted(manquants))}")
            anomalies.append("ANOMALIE : groupes divergents -- " + " ; ".join(detail))
        else:
            print("  OK : les groupes correspondent a ceux annonces.")
    else:
        print("  (--groupes non fourni : correspondance non verifiee)")

    # --- 2ter. Parametres de publication -------------------------------------
    # Le seuil de 240 est ecrit dans le code source, mais rien ne disait quelle
    # valeur tournait REELLEMENT pendant la consultation. Un abaissement en
    # cours de route -- pour obtenir « des resultats par service » -- etait
    # indetectable de l'exterieur.
    # UN CHAMP ABSENT EST UNE ANOMALIE, PAS UN SILENCE.
    #
    # CONSTAT DU 29/08/2026, par un audit externe. Ces controles etaient
    # conditionnels : `if seuil is not None`. Un serveur qui OMETTAIT simplement
    # seuil_publication, epsilon_par_publication et invitations_emises ne
    # declenchait rien, et ce script concluait « Aucune anomalie detectee »,
    # code de sortie 0. Il n'avait alors verifie AUCUN des trois parametres que
    # le README lui attribue.
    #
    # C'est le defaut que static/vote.html documente avoir corrige : « une
    # defense de securite doit echouer en se fermant, pas en s'ouvrant ». Le
    # client avait ete mis au fail-closed ; l'outil du TIERS VERIFICATEUR --
    # celui que le guide envoie au delegue du personnel -- etait reste au
    # fail-open. Le delegue ne pouvait pas distinguer « rien a signaler » de
    # « le controle n'a pas eu lieu ».
    seuil = donnees.get("seuil_publication")
    eps = donnees.get("epsilon_par_publication")

    if seuil is None:
        anomalies.append(
            "ANOMALIE : le serveur n'annonce pas son seuil de publication. "
            "Ce controle n'a donc pas pu avoir lieu -- un serveur qui omet le "
            "champ echappe a la verification aussi surement qu'un serveur qui "
            "ment.")
    if eps is None:
        anomalies.append(
            "ANOMALIE : le serveur n'annonce pas son budget epsilon. Ce "
            "controle n'a donc pas pu avoir lieu.")

    if seuil is not None:
        print(f"\nSeuil de publication annonce par le serveur : {seuil}")
        if seuil != 240:
            anomalies.append(
                f"ANOMALIE : le seuil de publication vaut {seuil} et non 240. "
                "Un seuil abaisse permet de publier sur des groupes plus petits, "
                "ou chaque reponse pese davantage."
            )
        else:
            print("  OK : conforme a la valeur documentee (240).")
    if eps is not None:
        print(f"Epsilon par publication : {eps}")
        if abs(eps - 0.5) > 1e-9:
            anomalies.append(
                f"ANOMALIE : epsilon vaut {eps} et non 0,5. Un epsilon plus "
                "eleve signifie moins de bruit, donc une protection plus faible."
            )

    # --- 2bis. Invitations emises par groupe ---------------------------------
    # Le seuil de 240 reponses ne protege que si les 240 invitations
    # correspondent a de vraies personnes. C'est l'organisation qui compose les
    # groupes : elle peut en declarer un de 240 dont quinze seulement sont
    # reelles, voter 225 fois avec des reponses connues, soustraire, et lire le
    # profil des quinze. Comparer ce chiffre a l'effectif reel est le seul
    # controle possible, et il ne demande aucune competence technique.
    invitations = donnees.get("invitations_emises")
    if invitations is None:
        anomalies.append(
            "ANOMALIE : le serveur n'annonce pas le nombre d'invitations "
            "emises par groupe. C'est le seul controle qu'un representant du "
            "personnel puisse mener sans competence technique -- comparer ces "
            "nombres aux effectifs reels. Son absence le rend impossible.")
    invitations = invitations or {}
    if invitations:
        print("\nInvitations emises par groupe :")
        for nom in sorted(invitations):
            print(f"  {nom} : {invitations[nom]}")
        print("  -> comparez ces nombres aux effectifs reels que vous connaissez.")
        print("     Un ecart important doit etre justifie par ecrit.")

    # --- 3. Empreinte de l'ensemble ------------------------------------------
    try:
        recalcule = calculer_agregat(cles)
    except ChampManquant as e:
        print(f"\n{'=' * 64}")
        print(f"ANOMALIE : {e}")
        print("\nNe laissez pas la consultation se poursuivre sans explication.")
        return 1
    print(f"\nEmpreinte recalculee : {recalcule}")
    print(f"Empreinte annoncee   : {annonce}")
    if recalcule != annonce:
        anomalies.append(
            "ANOMALIE : le serveur annonce une empreinte qui ne correspond pas "
            "aux cles qu'il fournit."
        )
    else:
        print("  OK : le serveur est coherent avec lui-meme.")

    if args.attendu:
        # NORMALISER AVANT DE COMPARER.
        #
        # La comparaison etait `recalcule != args.attendu.strip()`. hexdigest()
        # rend des minuscules, et strip() ne retire que les blancs de bord : une
        # empreinte CORRECTE recopiee en majuscules, ou collee depuis un
        # proces-verbal avec un espace au milieu, etait declaree « ANOMALIE
        # GRAVE -- le jeu de cles a change ».
        #
        # Cout, releve par un audit externe le 03/09/2026 : soit le delegue
        # suspend une consultation saine, soit -- plus probable apres une
        # premiere fausse alerte -- il cesse de croire l'outil. Un controle qui
        # crie au loup ne protege plus personne.
        #
        # Une empreinte est un nombre en base 16 : sa casse et les espaces qui
        # l'entourent n'en font pas partie.
        def _normaliser(empreinte):
            return "".join(empreinte.split()).lower()

        if _normaliser(recalcule) != _normaliser(args.attendu):
            anomalies.append(
                "ANOMALIE GRAVE : l'empreinte ne correspond pas a celle publiee "
                "avant la distribution des liens. Le jeu de cles a change depuis."
            )
        else:
            print("  OK : conforme a l'empreinte publiee avant distribution.")
    else:
        print("\n  (--attendu non fourni : comparez cette empreinte a celle")
        print("   publiee par l'organisation AVANT l'envoi des invitations.")
        print("   Une empreinte publiee apres coup ne prouve rien.)")

    print("\n" + "=" * 64)
    if anomalies:
        for a in anomalies:
            print(a)
        print("\nNe laissez pas la consultation se poursuivre sans explication.")
        return 1

    print("Aucune anomalie detectee.")
    print()
    print("Rappel de portee : ce controle etablit que le serveur declare un jeu")
    print("de cles coherent et conforme a ce qui a ete publie. Il n'etablit pas")
    print("que le serveur execute le code publie -- aucune verification externe")
    print("ne le peut. Voir VERIFICATION_CLIENT.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
