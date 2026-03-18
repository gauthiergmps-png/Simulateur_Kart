"""
Simulateur de Kart - Version Refactorisée
Utilise les classes UI et Simulation pour une meilleure organisation du code
"""
from classes.simulation import SimulationUI

def main():
    """Fonction principale du simulateur"""
    print("Initialisation du simulateur de kart...")

    
    # Création du gestionnaire de simulation avec interface utilisateur
    simulation = SimulationUI()
    
    # Démarrage de la simulation
    print("Démarrage de la simulation...")
    simulation.start_simulation()


if __name__ == "__main__":
    main()
