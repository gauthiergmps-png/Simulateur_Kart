 # HISTORIQUE ET REFLEXIONS STRATEGIQUES

- V0.0: animation d'un carré, GUI = Matplotlib
- V0.1: dessin voiture avec roues orientables
- v0.2 propagation d'état, j'impose une force à une roue
- v0.3: je passe l'animation en notation "objet" pour ajouter un cercle et une flèche
- v0.5: je passe tout avec un vecteur d'état vectoriel, axes SAE, angles de Bryant, et ajout des cercles et flèches roues
- v0.6: on tente de mettre des forces roue individuelles: pour l'instant opposées à la vitesse.
- v0.7: Changement de GUI pour Tkinter: gros progrès.
- v0.8: je corrige un bug de dynamique, je crois que je vois mon premier tete à queue, kart très instable !
- v0.9: J'attaque le pont arrière rigide.. pas simple...et j'ajoute un Z_cdg !
- v0.10 j'ai mis les freins
- v0.11: je met de l'ordre dans adher_roue
- V0.12 je passe en cursor...et je passe en classe la roue et le kart
- V0.13: Je passe en classe aussi la simulation et l'interface utilisateur.

- V1.0 - Mars 2026 - restructuration pour compatibilité RL: séparation Classes SimulationCore, SimulationUI, Kart, Mobile suivant le fichier STRUCTURE_TARGET et Main_simul_manuelle.py pour faire ce que je faisai jusqu'à présent avec ce programme.


# TODO

faire la classe "mobile" pour gérer l'état dynamique, dont la classe Kart hérite. Voir le chat "héritage de la classe simulation"

Supprimer l'asservissement vitesse lacet

reprendre les sorties de step


# EVOLUTIONS A FAIRE

Faire marcher un RL à vitesse constante sur un circuit donnée



 # REFLEXIONS STRATEGIQUES

Vision Long terme initiale:
 V1.0: kart rigide Z0 totalement débugé, etude impact differentiel sur quelques circuits tests
 V2.0 Kart rigide avec Zcdg, donc transferts de masse
 V3.0 Kart suspendu, donc amortisseurs
 V4.0 etude machine learning sur circuit

mi 2025: je vise runge kutta et lecture de fichier commande

- ajouter des commandes de forcage sur les variables d'état, pour faire des figures d'une note....

    - editeur de fichier commande à réflechir...
    - ajouter un modele de pneu Pacejka

    - repartiteur frein av/ar
    - valider la dynamique sur cas tests, avec adherence par roue
    - mettre un son moteur, voir Divers, je sais faire un bruit
    - bien faire marcher 4WD, avec Varbre calculé sur 4 roues
    - voir position du centre instantané de rotation ?

     - choisir entre plusieurs circuits
     - faire un editeur de scenario, avec scale temps, sur une trace circuit, choix scenario depart, type "virage easydrift"
     - Faire un asservissement volant sur un cercle, et mettre les gaz et voir comment ca se demerde
     - lire un fichier de commande à déclanchement sur seuil temps ou x ou y ... a réfléchir
     - intégrer un choix moteur, courbe puissance moteur, une boite sequentielle automatique
     - valider une visualisation dynamique des forces en pause - ca a l'air bon, reflechir aux stabilités lacet
     - lire un fichier de configuration
     - mesurer l'impact d'une reprogrammation sur un départ + ligne droite.


Mars 2026: On s'y remet, je suis un cours sur le reinforcement learning, très interessant. Il va donc falloir préparer ce code pour être utilisable en simulations headless, donc sans interface graphique, et donc redéfinir un peu mieux les classes de ce programme.
Ce programme marche très bien sans GIT pour l'instant, on va continuer un peu.

J

