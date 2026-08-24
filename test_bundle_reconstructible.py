#!/usr/bin/env python3
"""Le bundle servi aux votants est reconstructible depuis ses sources.

POURQUOI CE TEST EXISTE

`VERIFICATION_CLIENT.md` publie l'empreinte SHA-256 de
`static/blindrsa-bundle.js`, et `test_empreintes_publiees.py` verifie que cette
empreinte decrit bien le fichier du depot. Mais aucun controle n'etablissait que
ce fichier corresponde a ses SOURCES.

La difference n'est pas theorique. Un bundle piege, commite tel quel au depot
avec son empreinte a jour, passait tous les controles existants : la chaine
allait de l'empreinte publiee au fichier, jamais du fichier au code qui l'a
produit. C'est exactement ce que LIMITS.md section 6 designait comme la limite
de la verification par un tiers.

CE QUE CE TEST ETABLIT

Il reconstruit le bundle depuis `chantier_crypto/entree_bundle.js` avec les
dependances figees par `package-lock.json`, puis compare octet par octet au
fichier servi. Verifie le 23/08/2026 : la reconstruction sur une autre machine,
avec un Node de version differente, redonne la meme empreinte
`08e678cc...baa66`. Le bundle n'est pas minifie, esbuild ordonne les modules par
le graphe d'imports et n'insere ni horodatage ni chemin absolu -- rien
n'introduit de variation d'un build a l'autre.

Ce que cela apporte : un tiers peut desormais recompiler lui-meme et constater
que le fichier execute dans son navigateur derive du code source public. Il ne
depend plus de la parole de l'operateur sur ce point precis.

CE QUE CELA N'APPORTE PAS

Un operateur qui sert delibererement un client modifie a un votant cible reste
indetectable par cette voie : qui sert la page sert aussi l'attribut qui la
certifie. La reproductibilite rend un ecart CONSTATABLE, elle ne l'empeche pas.
Voir LIMITS.md section 6.

CONDITIONS D'EXECUTION

Le test a besoin de `node`, et de `node_modules` installe par `npm ci` dans
`chantier_crypto/`. S'ils manquent, il ECHOUE plutot que de s'ignorer : un test
qui se saute en silence ne verifie rien, et celui-ci porte sur la seule chaine
qui relie le code source au code execute chez le votant.
"""

import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent
CHANTIER = RACINE / "chantier_crypto"
BUNDLE = RACINE / "static" / "blindrsa-bundle.js"
ENTREE = CHANTIER / "entree_bundle.js"

echecs = []


def sha256(chemin):
    return hashlib.sha256(pathlib.Path(chemin).read_bytes()).hexdigest()


for chemin, quoi in ((BUNDLE, "le bundle servi"),
                     (ENTREE, "le point d'entree du bundle"),
                     (CHANTIER / "package.json", "le manifeste npm"),
                     (CHANTIER / "package-lock.json", "le verrou de dependances")):
    if not chemin.exists():
        echecs.append(f"{quoi} est absent : {chemin.relative_to(RACINE)}")

if shutil.which("node") is None:
    echecs.append(
        "node est introuvable. Ce test reconstruit le bundle : sans Node, la "
        "chaine entre le code source et le fichier execute chez le votant "
        "n'est verifiee par rien.")

esbuild = CHANTIER / "node_modules" / ".bin" / "esbuild"
if not esbuild.exists():
    echecs.append(
        "esbuild est absent. Installer les dependances figees :\n"
        "        cd chantier_crypto && npm ci")

if not echecs:
    with tempfile.TemporaryDirectory(prefix="vera_bundle_") as repertoire:
        sortie = pathlib.Path(repertoire) / "reconstruit.js"
        r = subprocess.run(
            [str(esbuild), "entree_bundle.js", "--bundle", "--format=iife",
             f"--outfile={sortie}"],
            cwd=str(CHANTIER), capture_output=True, text=True, timeout=300)

        if r.returncode != 0:
            echecs.append(
                "la reconstruction a echoue :\n    "
                + (r.stderr or r.stdout).strip()[-400:])
        else:
            attendu = sha256(BUNDLE)
            obtenu = sha256(sortie)
            if attendu != obtenu:
                echecs.append(
                    "le bundle servi ne correspond pas a ce que produisent ses "
                    "sources.\n"
                    f"    servi       : {attendu}\n"
                    f"    reconstruit : {obtenu}\n"
                    "    -> soit le bundle a ete modifie sans passer par ses "
                    "sources, soit une dependance a bouge sans que le verrou "
                    "suive. Reconstruire :\n"
                    "        cd chantier_crypto && npm ci && npm run build")

            # Un second build doit donner le meme resultat que le premier :
            # sans quoi la propriete verifiee ci-dessus serait un coup de
            # chance, et un tiers qui recompilerait obtiendrait autre chose.
            sortie2 = pathlib.Path(repertoire) / "reconstruit2.js"
            r2 = subprocess.run(
                [str(esbuild), "entree_bundle.js", "--bundle", "--format=iife",
                 f"--outfile={sortie2}"],
                cwd=str(CHANTIER), capture_output=True, text=True, timeout=300)
            if r2.returncode == 0 and sha256(sortie2) != obtenu:
                echecs.append(
                    "deux reconstructions successives donnent des fichiers "
                    "differents : le build n'est pas deterministe, et "
                    "l'empreinte publiee ne veut alors rien dire pour un tiers "
                    "qui recompile.")

if echecs:
    print("ECHEC : le bundle servi n'est pas reconstructible depuis ses "
          "sources.\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)

print("OK : le bundle servi est reconstruit a l'identique depuis ses sources, "
      "deux fois de suite.")
sys.exit(0)
