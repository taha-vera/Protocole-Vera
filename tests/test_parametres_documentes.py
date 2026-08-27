#!/usr/bin/env python3
"""Les parametres cites dans la documentation doivent correspondre au code.

POURQUOI CE TEST EXISTE

Le 26/08/2026, `VERA_AUDIT_REFERENCE.md` -- presente dans le README comme
« Synthese et parametres » -- affichait encore l'etat du 31/07 : persistance en
`journal_mode=WAL`, duree de vie des cles a 48 h, bourrage du corps a 200
octets. Les trois etaient faux depuis des semaines, et le premier est
securitairement significatif : le journal WAL conservait un historique des
versions successives des compteurs, ce qui est precisement la raison de son
abandon le 13/08 (`LIMITS.md` §9).

Personne ne l'avait vu, parce qu'aucun test ne lit la documentation.

LA CLASSE, PAS LE CAS

Le probleme n'est pas ce document : c'est la duplication d'une table de
parametres hors du code. Chaque valeur recopiee ailleurs devient une divergence
en puissance, et le projet en a fait l'experience quatre fois cette semaine sur
d'autres sujets. Ce test parcourt donc TOUS les fichiers Markdown du depot et
echoue des qu'un parametre y est cite avec une valeur que le code contredit.

Il ne verifie pas que la documentation soit complete -- seulement qu'elle ne
mente pas.

CE QU'IL LAISSE PASSER

Les mentions historiques assumees, formulees au passe et signalees comme telles.
Un document a le droit de dire « la duree etait de 48 h jusqu'au 24/07 » : c'est
une trace, pas une affirmation sur l'etat courant. La distinction se fait sur la
presence d'un marqueur explicite dans la ligne (« jusqu'au », « etait »,
« abandonne », « perime », « avant le »).
"""

import pathlib
import re
import sys

# tests/ etant un sous-repertoire, la racine du depot est le parent.
RACINE = pathlib.Path(__file__).resolve().parent.parent

# Parametre -> (fichier source, motif d'extraction dans le code)
SOURCES = {
    "K_MIN": ("vera_consultation_api.py", r"^K_MIN\s*=\s*(\d+)"),
    "LONGUEUR_CIBLE_FIXE": ("static/vote.html",
                            r"LONGUEUR_CIBLE_FIXE\s*=\s*(\d+)"),
    "DUREE_VIE_CLE_SECONDES": ("vera_signature_manager.py",
                               r"DUREE_VIE_CLE_SECONDES\s*=\s*([\d\s*_]+)"),
}

# Marqueurs qui signalent une mention historique, donc legitime.
HISTORIQUE = ("jusqu'au", "jusqu'a", "etait", "était", "abandonn", "perime",
              "passee de", "passé de", "passee a", "passé à", "porte de",
              "périmé", "avant le", "ancienne", "anterieur", "antérieur",
              "n'est plus", "a change", "a changé", "remplace", "remplacé",
              "depuis le", "obsolete", "obsolète", "instantane", "instantané")

echecs = []


def valeur_dans_le_code(nom):
    fichier, motif = SOURCES[nom]
    chemin = RACINE / fichier
    if not chemin.exists():
        echecs.append(f"{fichier} est absent : impossible de lire {nom}.")
        return None
    texte = "\n".join(
        l for l in chemin.read_text(encoding="utf-8", errors="replace").splitlines()
        if not l.lstrip().startswith(("#", "//", "*", "/*")))
    m = re.search(motif, texte, re.MULTILINE)
    if not m:
        echecs.append(
            f"{nom} est introuvable dans {fichier}. Le motif d'extraction de "
            "ce test est perime -- le corriger, pas le contourner.")
        return None
    return m.group(1).strip()


attendus = {nom: valeur_dans_le_code(nom) for nom in SOURCES}

# --- journal_mode : cas particulier, valeur textuelle ---------------------
persistance = (RACINE / "vera_persistance.py")
mode_reel = None
if persistance.exists():
    # C'est le PRAGMA reellement execute qui fait foi, pas les commentaires --
    # lesquels citent l'ancien mode pour expliquer son abandon. Une premiere
    # version de ce test lisait le fichier entier et concluait « le code dit
    # WAL » : elle accusait la documentation d'une erreur qu'elle commettait
    # elle-meme.
    m = re.search(r'PRAGMA\s+journal_mode\s*=\s*(\w+)',
                  persistance.read_text(encoding="utf-8", errors="replace"))
    if m:
        mode_reel = m.group(1).upper()

# --- Balayage de la documentation ----------------------------------------

# Racine + docs/, jamais un rglob nu : node_modules/ contient des .md de
# dependances, qui n'engagent pas ce projet et feraient echouer le test
# sur des valeurs qui ne sont pas les siennes.
documents = sorted(RACINE.glob("*.md")) + sorted(RACINE.glob("docs/**/*.md"))

# Les COMMENTAIRES Python sont scrutes au meme titre que la documentation.
#
# Constat du 27/08/2026 : le commentaire qui justifie K_MIN au lecteur du code
# annoncait « n=100 : 9% » la ou la mesure donne 12 % -- il citait le cas le
# plus favorable pour justifier un seuil. Ce test ne lisait que les .md : un
# commentaire pouvait contredire la constante situee trois lignes plus bas.
#
# Seules les lignes de commentaire sont examinees ; le code, lui, est la
# reference et ne peut pas se contredire lui-meme.
commentaires_py = []
for chemin in sorted(RACINE.glob("*.py")) + sorted(RACINE.glob("tests/*.py")):
    lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    for numero, ligne in enumerate(lignes, 1):
        nu = ligne.lstrip()
        if nu.startswith("#"):
            commentaires_py.append((chemin, numero, ligne))

for chemin, numero, ligne in commentaires_py:
    minuscule = ligne.lower()
    if any(marqueur in minuscule for marqueur in HISTORIQUE):
        continue
    for nom, attendu in attendus.items():
        if attendu is None or nom not in ligne:
            continue
        # \d+ et non [\d_ ]+ : « K_MIN : seuil MESURE » n'annonce aucune
        # valeur, et un motif qui accepte le vide produit des faux positifs.
        for t in re.findall(rf"{re.escape(nom)}\s*(?:=|vaut|:)\s*(\d[\d_ ]*)", ligne):
            if t.strip().replace("_", "").replace(" ", "") != \
                    attendu.replace("_", "").replace(" ", ""):
                echecs.append(
                    f"{chemin.relative_to(RACINE)}:{numero} — le commentaire "
                    f"dit {nom} = {t.strip()}, le code dit {attendu}.\n    "
                    + ligne.strip()[:120])

for chemin in documents:
    lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    for numero, ligne in enumerate(lignes, 1):
        minuscule = ligne.lower()
        if any(marqueur in minuscule for marqueur in HISTORIQUE):
            continue

        # Parametres numeriques nommes explicitement.
        for nom, attendu in attendus.items():
            if attendu is None or nom not in ligne:
                continue
            trouves = re.findall(rf"{re.escape(nom)}\s*(?:=|vaut|:)\s*([\d_ ]+)",
                                 ligne)
            for t in trouves:
                if t.strip().replace("_", "").replace(" ", "") != \
                        attendu.replace("_", "").replace(" ", ""):
                    echecs.append(
                        f"{chemin.relative_to(RACINE)}:{numero} — {nom} y vaut {t.strip()}, "
                        f"le code dit {attendu}.\n    " + ligne.strip()[:120])

        # Mode de journalisation SQLite.
        if mode_reel and "journal_mode" in ligne:
            cites = re.findall(r"journal_mode\s*=\s*(\w+)", ligne)
            for c in cites:
                if c.upper() != mode_reel:
                    echecs.append(
                        f"{chemin.relative_to(RACINE)}:{numero} — journal_mode y vaut {c}, "
                        f"le code dit {mode_reel}. Le mode WAL conservait un "
                        "historique des compteurs : la difference est "
                        "securitaire, pas cosmetique.\n    "
                        + ligne.strip()[:120])

# --- Les constantes du mecanisme ne sont declarees qu'a UN endroit --------
#
# CONSTAT DU 27/08/2026. `validation_opendp.py` -- le fichier qui porte la
# preuve formelle -- redeclarait DELTA_INT, SCALE et les bornes du domaine,
# annotes « = prod ». La borne superieure y valait 10 000 alors que la
# production applique 10 000 000 depuis la recalibration du 04/07 : un facteur
# mille, huit semaines durant, dans le document qui certifie le mecanisme.
#
# La consequence numerique etait nulle -- epsilon = Delta_1 / scale ne depend
# pas des bornes -- mais la preuve portait sur un mecanisme qui, deploye,
# aurait la branche dependante des donnees que l'elargissement a supprimee.
#
# Le probleme n'est pas ce fichier : c'est qu'une valeur recopiee cree une
# seconde source qui derive. Ce controle interdit la duplication elle-meme.

DECLARATIONS_UNIQUES = {
    "DELTA_INT": "vera_dp_noise.py",
    "SCALE": "vera_dp_noise.py",
    "BOUNDS": "vera_dp_noise.py",
    "K_MIN": "vera_consultation_api.py",
}

for nom, proprietaire in DECLARATIONS_UNIQUES.items():
    motif_decl = re.compile(rf"^{re.escape(nom)}\s*=", re.MULTILINE)
    for chemin in sorted(RACINE.glob("*.py")):
        if chemin.name == proprietaire:
            continue
        texte = chemin.read_text(encoding="utf-8", errors="replace")
        code_seul = "\n".join(
            l for l in texte.splitlines() if not l.lstrip().startswith("#"))
        if motif_decl.search(code_seul):
            echecs.append(
                f"{chemin.name} declare {nom}, qui appartient a "
                f"{proprietaire}.\n    Une valeur recopiee devient fausse au "
                f"premier changement : importer depuis {proprietaire} plutot "
                f"que redeclarer.")

if echecs:
    print("ECHEC : la documentation contredit le code.\n")
    for e in echecs:
        print("  - " + e)
    print("\nUne valeur recopiee hors du code devient fausse au premier "
          "changement.\nCorriger le document, ou marquer la mention comme "
          "historique (« etait », « jusqu'au »).")
    sys.exit(1)

print("OK : aucun parametre documente ne contredit le code.")
sys.exit(0)
