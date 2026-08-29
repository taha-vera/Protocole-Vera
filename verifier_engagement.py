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
    python3 verifier_engagement.py https://vera-consultation.duckdns.org
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
    p.add_argument("url", help="Adresse du serveur, ex. https://vera-consultation.duckdns.org")
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
        print("Aucune cle : aucune consultation n'est ouverte sur ce serveur.")
        # Une empreinte fournie et jamais comparee doit se voir. Le script
        # sortait ici en code 0 sans dire que --attendu n'avait pas ete
        # examine : le verificateur croyait avoir controle (29/08).
        if args.attendu:
            print("\nATTENTION : l'empreinte fournie par --attendu n'a PAS ete "
                  "comparee,\nfaute de cle sur ce serveur. Ce n'est pas une "
                  "verification reussie.")
            return 1
        return 0

    anomalies = []

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
        if recalcule != args.attendu.strip():
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
