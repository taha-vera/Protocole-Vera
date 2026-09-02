# Politique de securite -- VERA Consultation

## Versions supportees

| Version | Statut |
|---|---|
| Code actuel (branche `main`) | Supporte |
| Depots Zenodo v1.0 et v1.1 (12/06/2026) | **Non supportes** -- horodatage d'anteriorite uniquement |
| Toute autre version anterieure | Non supporte |

Les deux depots Zenodo cites dans le README existent pour dater l'anteriorite du
travail, pas pour etre installes ni audites. Ils decrivent un etat ou la
signature aveugle n'etait qu'un prototype. Un relecteur a releve le 03/09/2026
que les seules versions citables etaient formellement hors support : c'est
exact, et c'est voulu -- ce qui manquait etait de le dire.

## Signaler une vulnerabilite

N'ouvrez pas de ticket public sur GitHub pour un probleme de securite.

Contact : tahahouari@hotmail.fr

A inclure dans le rapport :
- Commit git concerne (SHA)
- Fichier(s) affecte(s)
- Preuve de concept ou etapes de reproduction
- Impact estime : fuite de donnees, contournement DP, epuisement du budget epsilon, falsification de token, etc.

Delai de reponse : accuse de reception sous 72h. Correction visee sous 7 jours pour les problemes critiques (contournement de la garantie epsilon-DP, forge de token valide, acces non autorise a la cle RSA).

## Perimetre

Dans le perimetre :
- vera_consultation_api.py -- logique API, authentification, endpoints
- vera_dp_noise.py -- mecanisme de bruit differentiel (Laplace, OpenDP)
- vera_epsilon_budget.py -- composition sequentielle, budget par population
- vera_signature_manager.py -- signature aveugle RSABSSA (RFC 9474)
- vera_persistance.py -- persistance SQLite chiffree (Fernet/AES-128)
- vera_blind_sig/ -- primitive de signature aveugle (Rust, RFC 9474)

Hors perimetre :
- Infrastructure Hetzner (reseau, systeme d'exploitation) -- signaler separement si pertinent
- Ingenierie sociale, acces physique au serveur
- Deni de service par epuisement de ressources reseau (hors perimetre applicatif)

## Modele de menace

Le modele de menace complet, avec l'etat verifie de chaque vecteur d'attaque identifie, est documente dans [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md). Toute vulnerabilite signalee sera evaluee au regard de ce document -- si elle correspond a une limite deja documentee et assumee, la reponse le precisera explicitement plutot que de la traiter comme une decouverte.

## Politique de divulgation

1. Rapport confidentiel par email
2. Confirmation, correction, puis publication du correctif avec preuve empirique dans VERA_THREAT_MODEL_COMPLETE.md
3. Mention du rapporteur dans l'historique git, sauf demande d'anonymat
4. Divulgation publique apres correction, delai a convenir selon la gravite

Pas de programme de prime pour le moment.

## Contact

Taha Houari -- tahahouari@hotmail.fr
Depot : https://github.com/taha-vera/projet-vera-consultations-
