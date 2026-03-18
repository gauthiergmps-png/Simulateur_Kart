Vocabulaire: un step = une action soit un pas de simul, un run = une séquence de simul.

# STEP 0: ALLER TOUT DROIT EN Q_LEARNING

15/03/2026: Premier test d'un Agent Qlearning, avec un état 10**3, donc 3 bins de 10.
J'observe y, lacet et omega (=vitesse lacet) et j'essaie d'aller tout droit avec une vitesse initiale 5m/s,
Y_MAX à 1m objectif max de 400 steps de 25ms soit 10 secondes.
reward = 1 - abs(y) à chaque step
5 actions de volant à -10, -5, 0, 5 , 10 degrés.

## Premiers résultats

Je me suis fait peur au début, car les 10 premiers runs (donc totalement aléatoires) sont meilleurs que les 100 suivants qui font pire...Mais en fait il faut passer les 500 runs pour qu'il commence à apprendre quelque chose.
A partir du run 2000, il semble ne faire que des runs complets de 10 secondes.
step 3000 reward d'environ 300, le max étant 1 par s. Je vois même passer un reward de 400 ou il n'a pas touché le volant pendant 400 Coups !
step 6000 encore beaucoup autour de 300, mais je vois passer quelque fois des 400.
6500: un progrès certain, beaucoup à plus de 350, donc sur 400 coup on a perdu que 50, soit 10cm d'écart typique par rapport au centre piste.
step 8000, on est plutot à 380 de moyenne
La courbe est très parlante, gros progrès à 6300, et à 7000 on a fini d'apprendre, plateau ensuite.

Quand je relance un learning avec le même Q, je repars avec un epsilon trop élevé, qui passe à moins de 3% uniquement au step 1000, donc il a le temps de pourrir ce que j'avais déjà appris, non ? A comprendre

Quand je relance pour un nouvel apprentissage de 10000 runs supplémentaire, la courbe d'apprentissage a un aspect surprenant:
On repart de bas avec un cycle périodique bon/mauvais de quelques centaines de runs, les deux en croissance régulière, et très brutalement vers 5000 cycles, il "trouve le truc" pour finir le nombre de max_cycles et en reste proche, avec une performance plutot en plateau et quelques explorations pitoyables.
 

Je code un premier programme d'exploration de Q pour voir ce qu'on a dedans après 20 000 runs. Je trouve
la matrice Q très disymétrique, ce qui me chagrine. Je passe 4 heures à valider la totale symétrie de mon kart, et je montre avec un programme test dédié que le Q_L qu'ou trouve est bien mirroir de Q_R quand on lance deux learning identiques avec des conditions initiales miroirs et graines identiques. Donc le résultat d'une matrice Q encore fortement dysymétrique est le résultat d'un apprentissage encore très imparfait, même après 20K runs...

## Conseils de réglage du Q_Learning:

1. exploration = epsilon:

La pratique standard est une décroissance exponentielle de ε :
epsilon = max(epsilon_min, epsilon * decay) avec 
epsilon_start = 1.0
epsilon_min   = 0.01
decay         = 0.995

2. réglage du learning rate alpha:
car Q_=Q + alpha (R+ gamma Q' -Q)
Interprétation :
α grand → apprentissage rapide mais bruité
α petit → apprentissage lent mais stable
viser 0.05 ≤ α ≤ 0.3

3. facteur gamma:

γ proche de 1 signifie que l’agent anticipe loin :
Si γ est trop petit : l’agent devient myope, il corrige tard la trajectoire.

4. Diagnostic de la convergence

Trois courbes sont très utiles :

norme de variation de Q  | Qt - Qt-1 |
reward moyenne par épisode
longueur des épisodes

Si la reward continue d’augmenter mais Q stagne, c’est souvent :
exploration trop faible, reward mal structurée.


5. Design de la reward
reward = + k0 * v_x - k1 * |erreur_latérale| - k2 * |angle| - k3 * steering^2
Exemple:   k0=1,  k1=2, k2=0.5, k3=0.05 
ou mettre directement k*(lateral + lambda * angle), plus physique

6. Méthode empirique pour trouver les bons paramètres

Je conseille souvent :

fixer γ

balayer α

balayer ε_decay

## Améliorations possibles

1. Initialiser Q avec un contrôleur simple (bootstrapping)

Au lieu de partir avec :Q(s,a) = 0, tu peux initialiser Q avec un contrôleur heuristique.
Par exemple :
y>0 → tourner à gauche
y<0 → tourner à droite
Cela correspond grossièrement à un contrôle proportionnel commande=-Y

2. Reward shaping
récompense basée sur un potentiel, basé sur la qualité de l
Et pénaliser l'usage de l'action pour éviter les oscillations:
- k * (steering_t - steering_{t-1})²

3. Curriculum learning
Commencer à vitesse faible, et ensuite accélerer, certes

4. Normaliser les états
Pour qu'ils soient tous dans [-1, 1]


5. Randomiser l'état initial
Sinon on apprend toujours la même séquence au début, en effet

6. Avoir un état en repère véhicule
Ce que je fait déjà, et ajouter des infos de courbure trajectoire cible à 2m et à 2 secondes

NEXT STEP: SUIVRE UN CIRCUIT VITESSE CONSTANTE


NEXT STEP: DEEP Q _LEARNING
Donc on passed'une version tabulée de Q(s,a) à une fonction Q(s,a) qui se doit d'être continue,
et qu'on produira par un réseau de neurone. 
Le DQ_learning permet d'apprendre sur des reruns stockés en mémoire


DEEEP DETERMINISTIC POLICY GRADIENT



SOFT ACTOR CRITIC




NEXT STEP: GARDER UNE GLISSE CONSTANTE DONC FCDG=POID


NEXT STEP: METHODE GAUTHIER FROM TRAJECTORY TO STATE
En fait mon kart doit toujours glisser, |gammaCdG|=poid n'est defini que par son cap, donc explorer tout les états possibles donnant tout les points d'un plan 2D (cap Gamma CdG,  MomentCdG).

Ensuite travailler en reverse à partir de la trajectoire optimale pour trouver une séquence de moment CdG qui la permet 