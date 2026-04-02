
# VERSIONS

V0.3 - Fonctionnelle
V0.5: J'ai demandé de definir une super classe profil, et deux sous-classe circuit et trajectoire
    pour ces deux sous-classe, on a une version grossière, un calcul de fin par spline, un UI similaire....
    après deux jours de débug, ca marche comme avant.

V1.2 - Mars 2026: Importation dans le projet Kart Simulator, donc n° Version global.
       J'ai produit un fichier traj_1.json, qui me suffira pour l'instant pour travailler sur SimulUI.

Je supprime la classe File_manager pour avoir les méthodes load et save directement dans les classes Circuit et Trajectoire

V.1.2.3: Le nombre de fine_point est défini par la longueur du raw_circuit et on a au moins 1 pt/m
         L'affichage passe en +Y vers le bas, en cohérence avec le simulateur Kart


# TODOs

Finir validation des vitesses et temps au tour en fermé et ouvert:
Une discontinuité  vitesse sur traj_sougy à corriger


deplacer l'affichage avec les flèches

mettre des traj_data dans les fichiers des circuit, ca permet de jouer avec le centre piste

suppression du 5ème PDP: j'ai un crash d'index sur le plus proche dès fois, à comprendre








# EVOLUTIONS
refondre l'UI avec des menus déroulants, affichage alternatif circuit/trajectoire, des réglages
Bouton "optimise current PDP" qui optimise sa position dans un cercle par exemple
choix des couleurs des points

18 Mars 2026: je refond les fonctions d'enregistrement et chargement de circuit et trajectoire, pour l'instant comme
essentiellement des profils à suivre que je pourrai utiliser pour mes agents de controle. Mais la logique originelle
de ce programme est qu'une trajectoire est associées à un circuit, mais ils ont des profils différents, celui du circuit
est le centre piste, celui de la trajectoire est la trajectoire. Donc pour recharger, il faut bien recharger deux fichiers.








