"""Stratégies de commande du kart (manuel, proportionnel, agents, etc.).


Si elles sont appelées par la classe SimulationUI, elles recevront en paramètres les commandes demand&es par les
commandes "manuelles", et pourront soit s'en servir, soit les ignorer suivant leur code. SimulUI recevra alors
les trois commandes volant, gaz, frein issues de la méthode compute_controls() et les enverra à SimulationCore
quand le controle ne sera ni manuel ni un replay. 

"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np


class Kart_control:
    """Regroupe les modes de pilotage et les calculs de commandes associés."""

    # Indices alignés sur le IntVar ``commandes`` de l'interface
    MODE_MANUEL = 0
    MODE_PROPORTIONNEL = 1
    MODE_QLEARNING = 2
    MODE_AGENT_3 = 3
    MODE_AGENT_4 = 4

    @staticmethod
    def list_available_controls() -> List[Tuple[int, str]]:
        """Liste (valeur radio, libellé) pour le frame Commandes de l'UI."""
        return [
            (0, "Manuel"),
            (1, "Proportionnel"),
            (2, "Q-learning"),
            (3, "Agent 3"),
            (4, "Agent 4"),
        ]

    def __init__(self) -> None:
        # Gains P classiques (volant en °) — à affiner avec la piste / le véhicule
        self.kp_stat = 12.0   # ° par mètre d'écart latéral
        self.kp_dyn = 40.0   # ° par radian d'écart angulaire tangent / vitesse

    def set_gains(self, p1, p2, p3):
        """Définit les gains de l'asservissement P sur l'écart latéral et l'écart angulaire.
        Appelé par SimulUI en phase réglage"""
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3

    def control_proportionnel(self, manual_commands, observation):
        """Asservissement P sur l'écart latéral (m) et l'écart angulaire (rad).

        Convention type README_Agents : correction de volant opposée à l'écart latéral.
        Sans trajectoire, l'appelant peut éviter d'utiliser ce mode ou passer des zéros.
        """
        idx, ecart_lat, v_lat, curv, curv_N = observation
        # logique gauthier: on vise une vitesse latérale de rapprochement de gain*P3 m/s de signe opposé à l'écat_lat

        # si on est écarté de plus de p2 m, gain saturé à p1, sinon décroissant linéairement en dessous de p2
        gain=min(abs(ecart_lat),self.p2)/self.p2
        v_cible= - np.sign(ecart_lat)*self.p3*gain
        ecart_vlat=v_lat-v_cible

        volant =  - self.p1 * ecart_vlat  * gain
        
        volant = float(np.clip(volant, -45., 45.0))
        return {"volant": volant, "gaz": float(manual_commands['gaz']), "frein": float(manual_commands['frein'])}

    def control_qlearning(self, *args: Any, **kwargs: Any) -> Dict[str, float]:
        """Placeholder : politique Q-learning (à brancher)."""
        return {"volant": 0.0, "gaz": 0.0, "frein": 0.0}

    def control_agent_3(self, *args: Any, **kwargs: Any) -> Dict[str, float]:
        """Placeholder : agent 3 (à brancher)."""
        return {"volant": 0.0, "gaz": 0.0, "frein": 0.0}

    def control_agent_4(self, *args: Any, **kwargs: Any) -> Dict[str, float]:
        """Placeholder : agent 4 (à brancher)."""
        return {"volant": 0.0, "gaz": 0.0, "frein": 0.0}

    def compute_controls(self, mode: int, manual_commands: Dict[str, float], 
                                   observation: Tuple[int, float, float, float, float]) -> Dict[str, float]:
        """Point d'entrée pour les modes controlés (modes manuel et replay gérés dans SimulationUI)
           
           Arg:
                manual_commands: dictionnaire descommandes manuelles proposées par l'UI:
                                {"volant": 0.0, "gaz": 0.0, "frein": 0.0}
                observation: écarts à la trajectoire = (idx, ecart_lat, v_lat_traj, curv, curv_N)

           Return:
                kart_controls: commandes volant, gaz, frein à appliquer au kart
        """
        if mode == self.MODE_PROPORTIONNEL:
            return self.control_proportionnel(manual_commands, observation)
        if mode == self.MODE_QLEARNING:
            return self.control_qlearning(manual_commands, observation)
        if mode == self.MODE_AGENT_3:
            return self.control_agent_3(manual_commands, observation)
        if mode == self.MODE_AGENT_4:
            return self.control_agent_4(manual_commands, observation)
        return dict(manual_commands)
