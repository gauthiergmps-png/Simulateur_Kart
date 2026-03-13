"""
Simulateur de Kart - Version Refactorisée
Utilise les classes UI et Simulation pour une meilleure organisation du code
"""

import numpy as np
from classes.kart import Kart
from classes.simulation import SimulationUI



def main():
    """Fonction principale du simulateur"""
    print("Initialisation du simulateur de kart...")
    
    # Création des instances 
    kart = Kart()
    
    # Création du gestionnaire de simulation avec interface utilisateur
    simulation = SimulationUI(kart)
    
    # Démarrage de la simulation
    print("Démarrage de la simulation...")
    simulation.start_simulation()


if __name__ == "__main__":
    main()
