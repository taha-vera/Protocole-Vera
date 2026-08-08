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


def calculer_agregat(cles):
    """Recalcule l'empreinte de l'ensemble, exactement comme le serveur.

    Tri par nom de groupe : la valeur ne depend pas de l'ordre de creation.
    Longueur avant contenu : sans cela, ("AB","C") et ("A","BC") donneraient
    la meme suite d'octets, donc la meme empreinte.
    """
    h = hashlib.sha256()
    for entree in sorted(cles, key=lambda c: c["departement"]):
        nom = entree["departement"].encode("utf-8")
        pub = bytes.fromhex(entree["cle_publique_hex"])
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

    # --- 3. Empreinte de l'ensemble ------------------------------------------
    recalcule = calculer_agregat(cles)
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
