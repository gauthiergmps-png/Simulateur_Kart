# Structure cible (preparation Gymnasium)

Objectif : rendre la simulation utilisable en mode IA/RL (type Gymnasium), tout en gardant une UI optionnelle.

## Principes d'architecture

- Le coeur physique ne depend pas de Tkinter.
- L'UI consomme l'etat mais ne porte pas la logique metier.
- Une API d'environnement stable permet de brancher plus tard un agent de controle.
- Le meme coeur sert pour les modes UI, headless, tests et batch.

## Classes principales

### 1) `Mobile` (base physique generique)

Responsabilite : propagation d'etat d'un mobile en 2D (évolution future en 3D)

Attributs (base) :
- Etat observable: Vecteur 4x3 Float, etat[] `position`, `vitesse`, `angles`, `vitangul`
- Autres observables: `force_cdg`, `moment_cdg`
- paramètres: `masse`, `inertie_lacet` 
- contrôles: `forces`  , `points d'application` 

Methodes :
- `init_state()`
- `update_position(dt)`
- `update_angles(dt)`
- `update_vitesse(dt)`
- `update_vitangul(dt)`
- `compute_force_moment()` (hook abstrait/surcharge)

### 2) `Kart(Mobile)` (modele vehicule)

Responsabilite : physique specifique kart (pneus, transmission, braquage).

Attributs :
- geometrie : `empattement`, `pos_cdg`, `voie_av`, `voie_ar`, `axav`, `axar`, `lav`, `lar`
- roues : `roue_avg`, `roue_avd`, `roue_arg`, `roue_ard`
- paramètres: `ouverture`, `transm`, `h_cdg`
- controles : `volant`, `gaz`, `frein`
- sorties: forces d'interfaces roues/sol

Methodes :
- `update_controles(...)`
- `set_forces_Z_roues()`
- `set_vitesses_roues()`
- `set_varbre()`
- `set_forces_roues()`
- `profil` / `profil_absolu` (pour rendu UI seulement)

### 3) `SimulationCore` (coeur de simulation)

Responsabilite : orchestration d'un episode de simulation sans interface graphique.

Attributs:
- Target_Trajectory : donnée du circuit pour évaluer (conditions de fin, timeout, crash, sortie de piste)
- dt / dt_controle fréquence de progagation de la simulation et de mise à jour des contrôles 

API principales :

- `reset(seed=None, options=None) -> (obs, info)`
   Initialisation d'une nouvelle simulation
- `step(action) -> (obs, reward, terminated, truncated, info)`              A METTRE A JOUR DONC
   action = commandes envoyées au Kart et Step de propagation du mobile associé,
   calcule et retourne les observables, reward, et info sur le déroulement en cours:
   Observation typique: 
    - vitesse longitudinale et laterale
    - vitesse angulaire lacet
    - erreur laterale a la trajectoire cible
    - courbure trajectoire locale
    - courbure trajectoire future
   Reward typique:
    - Décroissant au fur et à mesure de l'écartement par rapport à la trajectoire
  `terminated`: fin "naturelle" (crash, objectif atteint)
  `truncated`: fin par horizon temps
  `info`: autres metriques affichables (erreur piste, forces roues, glisse, etc.)

- `close(save_file=None)`
   peut permettre la sauvegarde de la simul dans un fichier pour la visualiser via un outil interactif "SimulPlayer" 


### 4) `SimulationUI` (Tkinter, optionnelle)

Responsabilite : affichage + interactions clavier/souris pour lancer manuellement une simulation en pilotage "à la main"

Regles :
- contient `SimulationCore` (composition)
- ne fait pas de calcul physique de reference
- appelle `core.step(action)` dans la boucle `after(...)`

### 6) 'SimulationRunner" (execution)

Responsabilité: Enchainer des épisodes de simulation avec des environnements controlés et reproductible

- `HeadlessRunner` : batch, dataset, benchmark, tests automatiques
- `UIRunner` : lancement interactif Tkinter

## API Gymnasium cible (minimum)

Action space (exemple continu) :
- `action = [volant_norm, gaz_norm, frein_norm]` dans `[-1,1]` ou `[0,1]` selon choix



## Mapping de l'existant vers la cible

- `classes/kart.py`
  - garde la physique kart et herite de `Mobile`
- `classes/simulation.py`
  - extraire la logique non-UI vers `SimulationCore`
  - laisser rendu clavier/canvas dans `SimulationUI`
- `classes/user_interface.py`
  - devient vue/controleur UI (facade Tkinter)

## Plan de migration progressif (sans casser V0.13)

1. Creer `Mobile` et faire heriter `Kart` de `Mobile`.
2. Introduire `SimulationCore` avec `reset/step` (sans Tkinter).
3. Faire consommer `SimulationCore` par l'UI actuelle.
4. Ajouter `HeadlessRunner` pour lancer des episodes sans GUI.
5. Normaliser observation/action/reward pour compatibilite Gymnasium.
6. Ensuite seulement, ajouter un wrapper Gymnasium officiel si necessaire.

## Regles de conception importantes

- Eviter les dependances circulaires UI <-> physique.
- Garder des methodes pures pour observation/reward/termination quand possible.
- Rendre les episodes reproductibles (`seed`).
- Journaliser proprement (`info`) pour debug et apprentissage.
- Ecrire des tests unitaires sur `step()` avant d'integrer un agent.