# SYNTAXE FICHIER DE COMMANDE

Ce document présente les commandes que le programme saura lire dans un fichier. Elles sont indiquées après le caractère ">" ci dessous, mais ce caractère ne sera pas dans le fichier de commande.

**Commentaires :** sur n'importe quelle ligne de commande, tout ce qui suit le premier caractère ``#`` est ignoré (y compris sur les lignes ``at t= ...`` et les lignes d'initialisation). Une ligne vide ou ne contenant qu'un commentaire est ignorée.

1- Commandes d'initialisation: Le programme peut lire dans un ordre quelconque les commandes d'initialisation suivantes qui sont en tête du fichier, sur une seule ligne chacune:

>t0_position : [ 0.0, 0.1, 0.0]
>t0_vitesse :  [ 10.0, 0.0, 0.0]
>t0_lacet : 0.0
>param_h_cdg: 0.0
>param_ouverture: 0.0
>param_transm : 0
>param_pos_cdg: 0.4    # fraction 0 (AR) .. 1 (AV), comme le curseur UI (pourcent) / 100

2- Commandes de contrôle de simulation

Chaque ligne commence par ``at ``, puis le **temps**, puis la commande.

**Temps (après ``t=`` ou ``t+=``) :** toujours en **millisecondes**. Ex. ``at t=1500`` = 1,5 s après le début du replay ; ``at t+=250`` ajoute 250 ms à l’instant résolu de la ligne précédente (ordre du fichier). La première ligne peut utiliser ``t+=`` : la référence initiale est 0 ms. Un nombre décimal (ex. ``1500.5``) représente des millisecondes avec une fraction.

**Commandes** (après le temps). La valeur du volant / gaz / frein est en **absolu** avec ``=``, ou en **variation** avec ``+=`` / ``-=`` :

>at t=1500 volant = 20      # position volant (absolu) à t = 1,5 s
>at t=2000 gaz = 20        # gaz à t = 2 s
>at t=3000 gaz-= 2         # baisse le gaz de 2 (relatif)
>at t=4000 regul_on        # active le régulateur de vitesse
>at t=5000 pause           # met la simulation en pause

Exemple **relatif en millisecondes** :

>at t=1000 gaz = 10        # t = 1 s
>at t+=500 volant = 5      # à t = 1500 ms
>at t+=1000 frein = 1      # à t = 2500 ms

Un fichier produit par SAVE écrit le temps en **millisecondes entières** après ``t=``. Il ne contient une telle ligne que lorsqu'une commande de pilotage change ; il se termine toujours par une ligne ``at t=... pause`` à l’instant de fin d’enregistrement. La pause n'est pas enregistrée pendant RECORD, seulement écrite en fin de fichier et lisible au replay.
