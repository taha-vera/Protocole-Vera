#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_epsilon_budget.py — Porte 4 du modele de menace VERA : composition
sequentielle. Empeche qu'un organisateur publie plusieurs resultats sur
la MEME cohorte (departement) au point que le budget de confidentialite
cumule devienne trop eleve pour rester protecteur.

Principe (composition sequentielle basique, Dwork & Roth) : si on publie
k resultats sur la meme population avec un budget epsilon chacun, le
budget cumule est k*epsilon (composition de base, pessimiste mais simple
et correcte -- pas besoin de composition avancee/Renyi pour ce volume).

Specifique au pipeline Consultation, distinct du budget du pipeline Radio
(qui suit le meme principe mais sur un objet different -- des requetes
d'agregation de signaux, pas des publications de resultats de sondage).
Construit independamment apres avoir constate que le fichier historique
(ancre_budget_ledger.py, pipeline Radio) n'etait pas exploitable depuis
cet environnement -- le principe est repris, pas le code.
"""

import threading


class BudgetEpuiseError(Exception):
    """Levee quand une publication depasserait le budget epsilon autorise
    pour ce departement."""

    def __init__(self, departement: str, epsilon_demande: float, epsilon_restant: float):
        self.departement = departement
        self.epsilon_demande = epsilon_demande
        self.epsilon_restant = epsilon_restant
        super().__init__(
            f"Budget epuise pour '{departement}': demande {epsilon_demande}, "
            f"restant {epsilon_restant}"
        )


class BudgetEpsilonParDepartement:
    """
    Suit un budget de confidentialite cumule par departement (cohorte).
    Chaque publication de resultat consomme une fraction du budget total
    autorise pour cette cohorte -- une fois epuise, refus dur, pas de
    degradation silencieuse.
    """

    # Tolerance sur les comparaisons de budget. Les epsilon sont des flottants
    # IEEE 754 : 0.5 - 0.4 vaut 0.09999999999999998, et 5 x 0.1 vaut
    # 0.5000000000000001. Sans tolerance, une publication legitime est
    # refusee, ou peut_publier et consommer se contredisent sur le meme etat.
    # 1e-9 est un milliardieme d'epsilon : aucune sequence reelle ne peut
    # l'exploiter pour depasser le plafond de facon significative.
    TOLERANCE_FLOTTANTE = 1e-9

    def __init__(self, epsilon_total_autorise: float = 0.5):
        self._verrou = threading.Lock()
        self._epsilon_total_autorise = epsilon_total_autorise
        self._epsilon_consomme: dict[str, float] = {}
        self._nombre_publications: dict[str, int] = {}

    def epsilon_restant(self, departement: str) -> float:
        with self._verrou:
            consomme = self._epsilon_consomme.get(departement, 0.0)
            return self._epsilon_total_autorise - consomme

    def peut_publier(self, departement: str, epsilon_requete: float) -> bool:
        # Un cout <= 0 n'a pas de sens (un cout nul autoriserait une infinite
        # de publications, un cout negatif "rembourserait" du budget).
        if epsilon_requete <= 0:
            return False
        with self._verrou:
            consomme = self._epsilon_consomme.get(departement, 0.0)
            # Meme forme et meme tolerance que consommer() : les deux methodes
            # doivent repondre pareil a la meme question, y compris au bord.
            return (consomme + epsilon_requete) <= (
                self._epsilon_total_autorise + self.TOLERANCE_FLOTTANTE
            )

    def consommer(self, departement: str, epsilon_requete: float) -> None:
        # Refus dur d'un cout <= 0 : un cout negatif rembourserait du budget
        # (permettant des publications supplementaires), un cout nul en
        # autoriserait une infinite. Les deux casseraient la garantie DP.
        if epsilon_requete <= 0:
            raise ValueError(f"Cout epsilon invalide (doit etre > 0) : {epsilon_requete}")
        with self._verrou:
            consomme = self._epsilon_consomme.get(departement, 0.0)
            # MEME FORME DE CALCUL QUE peut_publier, et meme tolerance.
            # Les deux methodes repondent a la meme question ; elles doivent
            # donc repondre pareil, y compris au bord.
            #
            # L'ancienne version comparait `epsilon_requete > total - consomme`.
            # Mathematiquement equivalent, numeriquement non : en IEEE 754,
            # 0.5 - 0.4 vaut 0.09999999999999998, donc une demande de 0.1
            # etait refusee alors que peut_publier l'autorisait. Cinq
            # consommations de 0.1 sur un budget de 0.5 echouaient a la
            # cinquieme -- une publication legitime rejetee sans raison
            # visible, et deux methodes en desaccord sur le meme etat.
            #
            # TOLERANCE_FLOTTANTE ne relache pas la garantie : elle vaut 1e-9,
            # soit un milliardieme d'epsilon. Aucune sequence de publications
            # reelles ne peut l'exploiter pour depasser le plafond de facon
            # significative, alors qu'une comparaison stricte rejette des cas
            # parfaitement valides.
            if (consomme + epsilon_requete) > (
                self._epsilon_total_autorise + self.TOLERANCE_FLOTTANTE
            ):
                restant = self._epsilon_total_autorise - consomme
                raise BudgetEpuiseError(departement, epsilon_requete, restant)

            self._epsilon_consomme[departement] = consomme + epsilon_requete
            self._nombre_publications[departement] = (
                self._nombre_publications.get(departement, 0) + 1
            )

    def etat(self, departement: str) -> dict:
        with self._verrou:
            consomme = self._epsilon_consomme.get(departement, 0.0)
            return {
                "epsilon_consomme": consomme,
                "epsilon_restant": self._epsilon_total_autorise - consomme,
                "epsilon_total_autorise": self._epsilon_total_autorise,
                "nombre_publications": self._nombre_publications.get(departement, 0),
            }
    def etat_apres_consommation(self, departement: str, epsilon_requete: float) -> dict:
        """Calcule l'etat qui RESULTERAIT d'une consommation, SANS la faire.
        Permet a l'appelant de persister d'abord et de ne muter la memoire
        qu'apres un commit reussi (voir consommer_si_persiste dans l'API).
        Sans cela, une panne d'ecriture laissait la memoire en avance sur la
        base : le departement apparaissait comme ayant publie alors que le
        resultat fige n'existait pas -> verrouillage ; ou, apres redemarrage,
        l'etat recharge ignorait la consommation -> republication et double
        consommation d'epsilon."""
        with self._verrou:
            consomme = self._epsilon_consomme.get(departement, 0.0)
            publications = self._nombre_publications.get(departement, 0)
            return {
                "epsilon_consomme": consomme + epsilon_requete,
                "nombre_publications": publications + 1,
            }

    def reset(self) -> None:
        """Remet le budget a zero pour TOUS les departements. Appelee a la
        cloture de consultation, en meme temps que les autres registres
        memoire.

        Correctif du 24/07 : la cloture vidait la table budget_epsilon et les
        registres memoire des compteurs, mais pas cet objet. Une nouvelle
        consultation reutilisant un nom de departement deja publie voyait donc
        nombre_publications > 0 -> deja_publie -> tentative de charger le
        resultat fige -> introuvable (table videe) -> publication refusee par
        securite. Le departement devenait definitivement non publiable jusqu'au
        prochain redemarrage, ce qui contredit la garantie "rouvre une
        consultation neuve pour un usage ulterieur". Scenario realiste : deux
        consultations successives dans une meme organisation, memes noms de
        departements, sans redemarrage entre les deux."""
        with self._verrou:
            self._epsilon_consomme.clear()
            self._nombre_publications.clear()

    def injecter_etat(self, departement: str, epsilon_consomme: float, nombre_publications: int) -> None:
        """
        Reinjecte un etat deja connu (rechargement depuis persistance, Porte 14) --
        contrairement a consommer(), n'applique aucune logique de refus et ne
        rejoue pas la sequence de publications, evite toute divergence si le
        montant par publication a change entre deux deploiements.
        """
        with self._verrou:
            self._epsilon_consomme[departement] = epsilon_consomme
            self._nombre_publications[departement] = nombre_publications
