Vocabulaire: un step = une action soit un pas de simul, un run = une séquence de simul.

# STEP 0: ALLER TOUT DROIT

15/03/2026: Premier test d'un Agent Qlearning, avec un état 10**3, donc 3 bins de 10.
J'observe y, lacet et omega (=vitesse lacet) et j'essaie d'aller tout droit avec une vitesse initiale 5m/s,
Y_MAX à 1m objectif max de 400 steps de 25ms soit 10 secondes.
reward = 1 - abs(y) à chaque step
5 actions de volant à -10, -5, 0, 5 , 10 degrés.

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
 


NEXT STEP: SUIVRE UN CIRCUIT VITESSE CONSTANTE

NEXT STEP: GARDER UNE GLISSE CONSTANTE DONC FCDG=POID
