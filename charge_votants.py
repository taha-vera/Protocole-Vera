#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
charge_votants.py -- simule N votants complets sur une instance VERA.

CE QUE CE SCRIPT FAIT
Il exerce le VRAI parcours de vote, de bout en bout, pour chaque votant :
aveuglement du secret dans le "navigateur", demande de signature au serveur,
finalisation, puis depot. Ce n'est pas une simulation : les requetes HTTP sont
reelles, la cryptographie est reelle, la base est reellement ecrite.

CE QU'IL PERMET DE VERIFIER
- Le serveur tient la charge (worker unique, verrou global, PBKDF2).
- Le seuil K_MIN se declenche au bon moment.
- La publication fonctionne a l'echelle reelle.
- Le bruit differentiel donne un resultat exploitable a n=240.
- Aucun vote n'est perdu ni compte deux fois.

CE QU'IL NE PERMET PAS DE VERIFIER
Rien de ce qui touche a l'humain : est-ce qu'un agent ose repondre
franchement, est-ce qu'un RH comprend son tableau de bord, est-ce que les SMS
arrivent. Ces questions-la exigent de vraies personnes ; aucun script ni aucun
panel remunere n'y repond.

USAGE (sur le SANDBOX, jamais en production) :
    python3 charge_votants.py --votants 300 --departement "CHARGE" \\
        --url http://127.0.0.1:8002 --identifiant asso_acer

Le mot de passe est demande a la saisie, il n'apparait ni en clair dans la
commande ni dans l'historique du shell.
"""

import argparse
import getpass
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import vera_blind_sig as vbs
except ImportError:
    print("ERREUR : le module vera_blind_sig est introuvable.")
    print("Lancez ce script depuis le repertoire de l'application, avec le venv :")
    print("  /root/vera_blind_sig/.venv/bin/python3 charge_votants.py ...")
    sys.exit(1)

LONGUEUR_CIBLE_FIXE = 450  # doit correspondre a static/vote.html


# Le cookie de session est pose avec secure=True (protection voulue, cf.
# Porte 19). urllib refuse donc de le renvoyer sur une URL http://, alors
# qu'un navigateur accepte cette exception pour 127.0.0.1. On gere donc le
# cookie a la main : c'est le script qui s'adapte au serveur, jamais l'inverse.
SESSION = {"cookie": None}


def _entetes(avec_session):
    h = {"Content-Type": "application/json"}
    if avec_session and SESSION["cookie"]:
        h["Cookie"] = SESSION["cookie"]
    return h


def _capturer_cookie(reponse):
    for cle, valeur in reponse.getheaders():
        if cle.lower() == "set-cookie" and "session_vera=" in valeur:
            SESSION["cookie"] = valeur.split(";")[0]


def _post(url, donnees, session=False, timeout=30):
    corps = json.dumps(donnees).encode("utf-8")
    req = urllib.request.Request(url, data=corps, headers=_entetes(session),
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        _capturer_cookie(r)
        return r.status, json.loads(r.read().decode("utf-8") or "{}")


def _get(url, session=False, timeout=30):
    req = urllib.request.Request(url, headers=_entetes(session))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8") or "{}")


def voter(base, jeton, departement, reponse):
    """Parcours complet d'UN votant. Renvoie (succes, duree, message).

    Reproduit exactement ce que fait le navigateur dans static/vote.html :
    l'aveuglement et la finalisation ont lieu ici, cote client. Le serveur ne
    voit jamais le secret ni la signature finale.
    """
    t0 = time.time()
    try:
        # 1. Recuperer la cle publique du departement (comme la page de vote).
        url_pk = f"{base}/api/cle_publique?departement={urllib.parse.quote(departement)}"
        _s, pk_data = _get(url_pk)
        pk = bytes.fromhex(pk_data["cle_publique_hex"])

        # 2. Aveugler un secret tire localement. Le serveur ne le verra jamais.
        secret = bytes([random.getrandbits(8) for _ in range(32)])
        # PyO3 convertit les Vec<u8> de Rust en LISTES Python, pas en bytes.
        # Sans cette conversion, .hex() echoue avec AttributeError.
        aveugle, secret_blind, randomizer = (
            bytes(x) for x in vbs.aveugler_message(pk, secret)
        )

        # 3. Demander la signature. C'est ici que le jeton est CONSOMME.
        _s, sig_data = _post(
            f"{base}/api/signer_aveugle",
            {
                "jeton_autorisation": jeton,
                "message_aveugle_hex": aveugle.hex(),
            },
        )
        sig_aveugle = bytes.fromhex(sig_data["signature_aveugle_hex"])

        # 4. Finaliser cote client : le serveur ne voit pas cette signature.
        signature = bytes(vbs.finaliser_signature(
            pk, secret, aveugle, secret_blind, sig_aveugle, randomizer
        ))

        # 5. Deposer le vote, avec le bourrage a longueur constante.
        pad = "x" * max(0, LONGUEUR_CIBLE_FIXE - len(reponse) - len(departement))
        _s, _ = _post(
            f"{base}/api/repondre",
            {
                "pad": pad,
                "K_hex": secret.hex(),
                "randomizer_hex": randomizer.hex(),
                "signature_hex": signature.hex(),
                "reponse": reponse,
                "departement": departement,
            },
        )
        return True, time.time() - t0, ""
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            pass
        return False, time.time() - t0, f"HTTP {e.code} {detail}"
    except Exception as e:
        return False, time.time() - t0, f"{type(e).__name__}: {e}"


def main():
    p = argparse.ArgumentParser(description="Charge : N votants reels sur VERA.")
    p.add_argument("--url", default="http://127.0.0.1:8002",
                   help="Instance a tester. NE JAMAIS pointer la production.")
    p.add_argument("--votants", type=int, default=300)
    p.add_argument("--departement", default="CHARGE")
    p.add_argument("--identifiant", required=True, help="Compte RH")
    p.add_argument("--parallele", type=int, default=8,
                   help="Votants simultanes. Au-dela de 10, le rate-limit Nginx "
                        "(5 r/s) refusera des requetes -- c'est voulu.")
    args = p.parse_args()

    if "duckdns.org" in args.url or ":8001" in args.url:
        print("REFUS : cette URL ressemble a la PRODUCTION.")
        print("Ce script ecrit reellement en base. Utilisez le sandbox (port 8002).")
        return 1

    # VERA_TEST_MDP evite de retaper 40 caracteres hexadecimaux a l'aveugle.
    # La variable n'existe que le temps de la commande et n'est pas persistee.
    mdp = os.environ.get("VERA_TEST_MDP")
    if mdp:
        print("(mot de passe lu depuis VERA_TEST_MDP)")
    else:
        mdp = getpass.getpass(f"Mot de passe RH ({args.identifiant}) : ")

    print(f"\nCible      : {args.url}")
    print(f"Votants    : {args.votants}   Departement : {args.departement}")
    print(f"Parallele  : {args.parallele}")
    print("-" * 58)

    # Connexion RH
    try:
        _s, _ = _post(f"{args.url}/api/rh/connexion",
                      {"identifiant": args.identifiant, "mot_de_passe": mdp})
        if not SESSION["cookie"]:
            print("Connexion RH : ECHEC (aucun cookie de session recu)")
            return 1
        print("Connexion RH : OK")
    except Exception as e:
        print(f"Connexion RH : ECHEC ({e})")
        return 1

    # Generation des jetons -- c'est le RH qui les cree, comme en vrai.
    t0 = time.time()
    try:
        _s, gen = _post(f"{args.url}/api/rh/generer_autorisations",
                        {"departement": args.departement, "quantite": args.votants},
                        session=True, timeout=120)
    except Exception as e:
        print(f"Generation : ECHEC ({e})")
        return 1
    jetons = [a["jeton"] for a in gen["autorisations"]]
    print(f"Generation   : {len(jetons)} jetons en {time.time() - t0:.2f} s")

    # Repartition des reponses. Volontairement desequilibree : un resultat
    # 50/50 masquerait une erreur de comptage, un ecart net la revele.
    reponses = (["oui"] * int(len(jetons) * 0.55)
                + ["non"] * int(len(jetons) * 0.30))
    reponses += ["abstention"] * (len(jetons) - len(reponses))
    random.shuffle(reponses)
    verite = {r: reponses.count(r) for r in ("oui", "non", "abstention")}

    # Vote
    print(f"\nVote de {len(jetons)} participants...")
    t0 = time.time()
    ok, echecs, durees = 0, [], []
    with ThreadPoolExecutor(max_workers=args.parallele) as ex:
        futurs = {ex.submit(voter, args.url, j, args.departement, r): j
                  for j, r in zip(jetons, reponses)}
        for i, f in enumerate(as_completed(futurs), 1):
            succes, duree, msg = f.result()
            durees.append(duree)
            if succes:
                ok += 1
            else:
                echecs.append(msg)
            if i % 25 == 0 or i == len(jetons):
                print(f"  {i}/{len(jetons)}  reussis={ok}  echecs={len(echecs)}",
                      end="\r", flush=True)
    total = time.time() - t0
    print()

    print("-" * 58)
    print(f"Duree        : {total:.1f} s  ({len(jetons) / total:.1f} votes/s)")
    print(f"Reussis      : {ok}/{len(jetons)}")
    if durees:
        print(f"Latence      : mediane {statistics.median(durees) * 1000:.0f} ms, "
              f"max {max(durees) * 1000:.0f} ms")
    if echecs:
        print(f"Echecs       : {len(echecs)}")
        from collections import Counter
        for motif, n in Counter(echecs).most_common(5):
            print(f"   {n:4d} x {motif[:70]}")

    # Etat cote RH
    print("\n" + "-" * 58)
    try:
        _s, etat = _get(f"{args.url}/api/rh/etat_departements", session=True)
        e = etat.get(args.departement, {})
        print(f"Votes recus  : {e.get('votes_recus')}")
        print(f"Invitations  : {e.get('invitations_generees')}")
        print(f"Publiable    : {e.get('publiable')}  (seuil {e.get('seuil_k_min')})")
    except Exception as ex:
        print(f"Etat : {ex}")

    # Publication et comparaison au reel
    print("\n" + "-" * 58)
    print(f"Verite terrain : {verite}")
    try:
        _s, pub = _post(f"{args.url}/api/rh/publier",
                        {"departement": args.departement}, session=True)
        bruite = pub.get("resultats_bruits", {})
        print(f"Publie (bruite): {bruite}")
        ecarts = [abs(bruite.get(k, 0) - v) for k, v in verite.items()]
        somme = sum(bruite.values())
        print(f"Ecart max      : {max(ecarts)} voix "
              f"({max(ecarts) / max(1, ok) * 100:.1f} % de l'effectif)")
        print(f"Somme publiee  : {somme}  (doit egaler {ok})")
        if somme != ok:
            print("  ATTENTION : la somme ne correspond pas a l'effectif.")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            pass
        print(f"Publication refusee : HTTP {e.code} {detail}")
        print("  (normal si l'effectif est sous le seuil K_MIN)")

    print("\n" + "=" * 58)
    if ok == len(jetons):
        print("Tous les votes ont abouti.")
    else:
        print(f"{len(jetons) - ok} vote(s) n'ont pas abouti -- voir les motifs.")
    print("Pensez a cloturer la consultation de test dans le tableau de bord.")
    return 0 if ok == len(jetons) else 1


if __name__ == "__main__":
    sys.exit(main())
