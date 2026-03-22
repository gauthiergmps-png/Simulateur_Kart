# Structure du projet — Simulateur de Kart

Documentation de **toutes les classes Python du dépôt** (`classes/`, `C_et_T/`, `Agent_qlearning/`) et de leurs méthodes, avec liens vers les numéros de ligne.  


Les dossiers `__pycache__/` ne font pas partie du code source à documenter ici.

## Arborescence (fichiers utiles)

```
.
├── main_simul_manuelle_V1.0.py   # Point d’entrée principal du simulateur kart + UI
├── mainV0.12.py                  # Ancienne entrée (référence / historique)
├── test.py                       # Brouillon / tests rapides
├── .cursorrules                  # Conventions pour l’assistant (commentaires, format, messagebox)
├── .vscode/                      # launch.json, extensions.json
│
├── classes/                      # Cœur physique + UI du simulateur
│   ├── simulation.py             # SimulationCore + SimulationUI
│   ├── user_interface.py         # User_Interface (Tkinter)
│   ├── kart.py                   # Mobile, Kart
│   ├── kart_control.py           # Modes de pilotage (manuel, proportionnel, Q-learning, …)
│   ├── wheel.py                  # Roues
│   ├── utils.py                  # Repères, normes, rotations
│   └── __init__.py
│
├── C_et_T/                       # Édition / visualisation circuit & trajectoire (matplotlib + Tk)
│   ├── main_C_et_T.py            # Application CircuitSimulator
│   ├── requirements.txt
│   ├── C_et_T _TODO.md
│   ├── C_et_T_classes/
│   │   ├── circuit_et_trajectoire.py  # Circuit, Trajectoire, chargement JSON, dialogue
│   │   ├── profil.py                  # Profil (base géométrique)
│   │   └── image_background.py        # Fond d’image pour l’éditeur
│   └── C_et_T_files/             # JSON circuits/trajectoires, images, Excel, etc.
│
├── Agent_qlearning/              # RL et visualisation Q
│   ├── 0-kart_qulearning.py      # Environnement / boucle Q-learning kart
│   ├── main_explore_Q.py         # Explorateur Tkinter des tables Q (Records/)
│   └── __pycache__/              # (fichiers générés)
│
├── Records/                      # Données runtime : commandes, Q-tables, exports exploration ParaView, …
│
├── README_STRUCTURE.md           # Ce fichier
├── README_STRUCTURE_TARGET.md    # Cible / notes structure (si utilisé)
├── README_TODO.md
└── README_Agents.md              # Agents et Q-learning (détail)
```

---

## Détail des méthodes

## Dossier `classes/`

### `classes/__init__.py`
Package Python (fichier vide ou minimal).

### `classes/kart.py` — classe `Mobile`

**Propriétés typiques** : `masse`, `inertie_lacet`, `position`, `vitesse`, `angles`, `vitangul`, `force_cdg`, `moment_cdg`.

**Méthodes principales** :
- `__init__` — Construit le mobile avec masse et inertie de lacet ; appelle `init_state`.
- `init_state` — Initialise ou remet position, vitesse, angles, vitesses angulaires, forces et moments au CdG.
- `_update_dynamique` — Intègre un pas `dt` : position, angles, vitesse (repère véhicule), vitesses angulaires à partir de `force_cdg` et `moment_cdg`.
- `_update_force_et_moment_cdg` — Agrège des forces élémentaires (points en repère mobile) en résultante et moment au CdG, repère piste + gravité.

### `classes/kart.py` — classe `Kart` *(hérite de `Mobile`)*

**Méthodes principales** :
- `__init__` — Construit le kart (empattement, position CdG, voies avant/arrière) et instancie les quatre roues.
- `init_state` — Réinitialise l’état dynamique du kart (position, vitesse, angles, etc.) avec des valeurs par défaut ou passées en argument.
- `profil_absolu` *(property)* — Retourne les listes de points `(x, y)` du contour du véhicule en repère absolu pour l’affichage.
- `update_parametres` — Met à jour `h_cdg`, ouverture arrière et mode de transmission pendant la simulation.
- `_update_controles` — Applique volant, gaz et frein (braquage, puissance moteur, freinage).
- `set_forces_Z_roues` — Répartit le poids sur les roues (forces verticales).
- `set_vitesses_roues` — Calcule les vitesses des roues à partir du mouvement du châssis.
- `set_varbre` — Met à jour la vitesse de l’arbre moteur / couple disponible.
- `set_forces_roues` — Calcule les forces d’interaction roue / sol pour chaque roue.
- `_update_force_et_moment_cdg` — Recalcule force et moment résultants au CdG après les forces roues.
- `update_state` — Un pas physique complet : contrôles, forces roues, dynamique, mise à jour des grandeurs internes.

### `classes/wheel.py` — classe `Wheel`

**Méthodes / propriétés principales** :
- `__init__` — Attache la roue au kart (identifiant roue, références géométriques).
- `rayon`, `largeur`, `position` *(properties)* — Géométrie et position de la roue en repère véhicule.
- `profil` — Polygone de la roue pour le dessin du profil véhicule.
- `update_vsol` — Met à jour la vitesse relative au sol.
- `update_fz` — Met à jour la charge verticale sur la roue.
- `update_controles` — Passe arbre moteur, puissance appliquée, frein à la roue.
- `force` — Force d’adhérence / propulsion au contact sol (cas général).
- `force_roue_libre` — Cas roue sans entraînement forcé.
- `force_roue_V_force` — Cas avec vitesse de roue imposée.

### `classes/kart_control.py` — classe `Kart_control`

**Méthodes principales** :
- `list_available_controls` *(staticmethod)* — Liste des couples (valeur radio, libellé) pour le panneau « Commandes » de l’UI.
- `__init__` — Gains par défaut pour l’asservissement proportionnel.
- `set_gains` — Fixe les gains P1, P2, P3 utilisés en mode proportionnel.
- `control_proportionnel` — Calcule volant (écarts latéraux / vitesse latérale) à partir des commandes manuelles et de l’observation trajectoire.
- `control_qlearning`, `control_agent_3`, `control_agent_4` — Placeholders pour politiques automatisées (à brancher).
- `compute_controls` — Point d’entrée selon le mode (manuel géré ailleurs) : délègue au bon contrôleur et retourne `volant`, `gaz`, `frein`.

### `classes/simulation.py` — classe `SimulationCore`

**Méthodes principales** :
- `__init__` — Associe le kart, initialise temps, pas, trajectoire cible et bordures.
- `reset` — Remet temps et index ; repositionne le kart sur la trajectoire cible si chargée.
- `step` — Un pas de simulation : mise à jour paramètres kart, application des contrôles, `kart.update_state`, régulateur de vitesse optionnel.
- `load_T_or_C` — Dialogue Tk pour charger un JSON circuit ou trajectoire ; met à jour `traj_cible` et bordures.
- `ecarts_trajectoire` — Calcule index le plus proche, écart latéral, vitesse latérale, courbures pour l’asservissement et l’affichage.

### `classes/simulation.py` — classe `SimulationUI` *(hérite de `User_Interface`)*

**Méthodes principales** :
- `__init__` — Crée kart, `SimulationCore`, `Kart_control` et enchaîne le `reset` UI.
- `reset` — Remet simulation, curseurs, recorder et historiques d’affichage.
- `press_key` / `stop_key` — Gaz / frein clavier, volant, chargement T/C, touches diverses.
- `profil_circuit` — Interpole la position sur la trajectoire cible pour affichage du « rail ».
- `_handle_load_T_or_C` — Callback bouton : appelle `core.load_T_or_C` puis rafraîchit l’affichage.
- `dessin_canvas` — Redessine circuit, kart, vecteurs, arcs lacet, roues, indicateurs, compteur.
- `_trace_dyn_roues` — Cercles / forces par roue sur le canvas.
- `_trace_indicators_gaz_frein` — Barres gaz et frein.
- `_trace_compteur_vitesse` — Cadran vitesse.
- `_handle_record` — Démarre un enregistrement de commandes (surcharge pour logique pas_simul == 0).
- `read_commands` — Lit un fichier de commandes dans `Records/` pour le replay.
- `record_replay` — Active le mode replay à partir des commandes chargées.
- `update_telemetry` — Formate et envoie les trois lignes de télémesure (via `show_telemetry_*`).
- `_explore_combinations_gen` — Générateur des tuples `(cap_rad, vit, vol, gaz)` selon les cases EXPLORE ; remplit `explore_values` pour le JSON.
- `explore_states` — Démarre l’exploration : copie `simu_controls` / `kart_parametres`, enregistre pour export, lance `_explore_step`.
- `_explore_step` — Une combinaison : `next` du générateur, `init_state`, `core.step(0)`, enregistrement des forces pour VTK, enchaînement `after` ou fin (`StopIteration`).
- `_explore_write_paraview_vtk` — Écrit les `.vtk` par vitesse, le `.pvd` (temps = vit), le `.json` (paramètres + `explore_values`).
- `animation_step` — Boucle temps réel : lecture UI, `ecarts_trajectoire`, contrôles, `core.step`, dessin, télémesure, `after` ; si EXPLORE, délègue à `explore_states`.
- `start_simulation` — Premier `animation_step` puis `mainloop`.

### `classes/user_interface.py` — classe `User_Interface`

**Méthodes principales** :
- `__init__` — Crée la fenêtre Tk, tous les panneaux, le canvas et les liaisons clavier.
- `_create_main_window` — Fenêtre titre, protocole fermeture.
- `_quit_application` — Quitte proprement `mainloop` et détruit la fenêtre (Windows).
- `_create_control_panel` — Assemble les frames (explore, propagation, caméra, boutons, circuit, volant, régulateur, commandes, transmission, télémesure).
- `_create_explore_states_frame` — Cases EXPLORE et bouton EXPLORE.
- `_create_command_frame` — Radios des modes de pilotage (`Kart_control.list_available_controls`).
- `_create_propagation_frame` — Pas de temps (ms), méthode numérique (Euler / RK4).
- `_create_dynamic_scale_frame` — Échelle d’affichage dynamique du canvas.
- `_create_camera_frame` — Altitude et vitesse de la « caméra drone ».
- `_create_control_buttons_frame` — Reset, pause, quit.
- `_create_recorder_buttons_frame` — Record, stop, replay.
- `_create_circuits_frame` — Chargement trajectoire / circuit cible.
- `_create_steering_frame` — Curseur volant, hauteur CdG.
- `_create_regulator_frame` — Régulateur de vitesse, gains asservissement proportionnel.
- `_create_transmission_frame` — Ouverture arrière, mode transmission.
- `_create_telemetry_zone` — Trois labels de télémesure sous le canvas.
- `_create_canvas` — Canvas d’animation.
- `_setup_key_bindings` — Focus canvas et bindings touches.
- `press_key` / `stop_key` — Hooks vides, à surcharger dans `SimulationUI`.
- `_handle_explore` — Passe `explore_status` à vrai pour déclencher l’exploration au prochain `animation_step`.
- `_handle_reset` / `_handle_pause` / `_handle_record` / `_handle_stop` / `_handle_replay` — Boutons UI (certaines méthodes abstraites ou surchargées dans la classe fille).
- `_handle_load_T_or_C` — Hook chargement (implémenté dans `SimulationUI`).
- `reset` / `read_commands` — *Abstractmethod* : implémentés dans `SimulationUI`.
- `show_telemetry_1` / `2` / `3` — Met à jour le texte des trois lignes (arguments déjà formatés côté appelant).
- `update_camera_position` — Filtre la position caméra pour suivre le kart en douceur.
- `mainloop` — Délègue à `fenetre.mainloop`.
- `after` — Programme un callback après `ms` ms, avec arguments optionnels (délégation à Tk).

### `classes/utils.py` — fonctions

- `tourne_vecteur` — Rotation 2D d’un ou plusieurs vecteurs par un angle donné.
- `vehicule2piste` / `piste2vehicule` — Passe un vecteur entre repère véhicule (lacet) et repère piste.
- `roue2vehicule` / `vehicule2roue` — Passe un vecteur entre repère roue (braquage) et repère véhicule.
- `norme_vecteur` — Norme euclidienne 3D.

---

## Dossier `C_et_T/`

### `C_et_T/C_et_T_classes/profil.py` — classe `Profil`

**Méthodes principales** :
- `__init__` — Nom, boucle fermée ou non, nombre de points fins pour l’échantillonnage.
- `reset_raw_points` — Vide ou réinitialise les points saisis.
- `insert_point` / `remove_point` — Édition de la poly ligne brute.
- `start_input` / `stop_input` — Active ou coupe la saisie interactive de points.
- `is_ready_for_calculation` — Indique si assez de points pour calculer le profil fin.
- `reset_fine_profile` — Remet à zéro le profil échantillonné et les paramètres dérivés.
- `closest_raw_point` / `closest_fine_point` — Trouve le point le plus proche d’un clic (seuil pixel).
- `calculate_fine_profile` — Lissage / échantillonnage (splines) des points bruts.
- `calculate_parameters` — Tangentes, longueurs, courbures le long du profil fin.
- `to_dict` / `from_dict` — Sérialisation JSON du profil.

### `C_et_T/C_et_T_classes/circuit_et_trajectoire.py` — classe `Circuit` *(hérite de `Profil`)*

**Méthodes principales** :
- `__init__` — Circuit avec largeur et points fins par défaut.
- `set_width` — Largeur piste pour les bordures.
- `calculate_borders` — Construit bord gauche / droit à partir de la ligne médiane.
- `reset_fine_profile` — Réinitialise aussi les bordures associées.
- `calculate_parameters` — Recalcule profil fin + bordures + paramètres géométriques.
- `is_point_inside` — Test intérieur / extérieur par rapport au ruban circuit.
- `to_dict` / `from_dict` — Sauvegarde / chargement JSON d’un circuit.
- `_save_circuit_csv` / `_save_circuit_json` — Écriture fichier ; `save_circuit_dialog` — dialogue utilisateur.
- `_load_circuit_csv` *(staticmethod)* — Charge un circuit depuis CSV.

### `C_et_T/C_et_T_classes/circuit_et_trajectoire.py` — classe `Trajectoire` *(hérite de `Profil`)*

**Méthodes principales** :
- `__init__` — Trajectoire avec bornes d’accélération et vitesse max pour l’optimisation.
- `reset_fine_profile` — Réinitialise aussi vitesses et temps au tour.
- `calculate_lap_time` — Estime le temps au tour à partir des vitesses le long du profil.
- `calculate_parameters` — Profil fin + paramètres cinématiques.
- `to_dict` / `from_dict` — Sérialisation JSON.
- `_save_trajectory_csv` / `_save_trajectory_json`, `save_trajectory_dialog` — Export et dialogue.
- `calculate_velocities` — Profil de vitesse le long de la ligne (optimisation).

### `C_et_T/C_et_T_classes/circuit_et_trajectoire.py` — fonctions du module

- `_dir_files_path`, `_is_within_dir_files`, `_force_into_dir_files` — Sécurisent les chemins sous `C_et_T_files`.
- `load_C_or_T__dialog` — Dialogue d’ouverture : retourne un `Circuit` ou `Trajectoire` (utilisé aussi par le simulateur kart).
- `optimize_vitesse` — Optimisation de vitesses à partir de courbures et distances.

### `C_et_T/C_et_T_classes/image_background.py` — classe `ImageBackgroundManager`

**Méthodes principales** :
- `__init__` — Références fenêtre, axe matplotlib, label d’info.
- `load_background_image` — Charge une image de fond pour caler le tracé sur un plan.
- `get_image_coordinates` — Saisie de points de calage image → monde.
- `get_single_point_coordinates` — Dialogue pour un point unique avec consigne utilisateur.
- `display_background_image` — Affiche ou met à jour l’image sur l’axe.
- `is_image_loaded` / `reset_image` — État et remise à zéro du fond.

### `C_et_T/main_C_et_T.py` — classe `CircuitSimulator`

**Méthodes principales** :
- `__init__` — Fenêtre Tk, instances `Circuit`, `Trajectoire`, figure matplotlib embarquée.
- `_reset_model_background_image` / `load_background_image` — Gestion du fond via `ImageBackgroundManager`.
- `setup_ui` / `setup_plot` / `setup_view` — Construction de l’interface et du graphe.
- `on_scroll` — Zoom à la molette.
- `on_key_press` — Raccourcis clavier (navigation, modes).
- `update_closest_points` — Surlignage du point brut le plus proche du curseur.
- `on_press` / `on_motion` / `on_release` — Souris : ajout / déplacement de points, sélection.
- `def_circuit_test` — Circuit de démonstration rapide.
- `update_trajectory_info` — Affichage des infos au point courant sur la trajectoire.
- `new_trajectory` / `new_circuit` — Nouveaux objets métier.
- `add_raw_point` / `remove_raw_point` — Édition des points via l’UI.
- `calculate_circuit_fin` / `calculate_trajectory` — Lance les calculs de fin de circuit ou de ligne avec messages utilisateur.
- `recenter_view` — Recadre les axes sur les données.
- `update_circuit_width` — Met à jour la largeur depuis l’UI.
- `save_circuit` / `save_trajectory` / `load_circuit` / `load_trajectory` — I/O fichiers.
- `toggle_circuit_input` / `toggle_pdp_input` — Bascule modes de saisie (contour circuit vs points de passage).
- `update_instructions_and_buttons` — Cohérence des libellés et de l’état des boutons.
- `optimisation_method` — Lance l’optimisation de temps au tour / vitesses.
- `update_plot` — Rafraîchit le tracé matplotlib (mouvement ou statique).

**Fonction** : `main` — Point d’entrée Tk ; fermeture propre matplotlib (`on_closing`).

---

## Dossier `Agent_qlearning/`

### `Agent_qlearning/0-kart_qulearning.py` — classe `SimuKart`

**Méthodes principales** :
- `__init__` — Environnement simplifié autour d’un `Kart` pour le RL.
- `reset` — Remet l’épisode (option miroir / dernier état).
- `step` — Applique une action discrète, retourne observation, récompense, fin d’épisode.
- `close` — Libère les ressources si nécessaire.

**Fonctions principales** :
- `max_dict` — Argmax sur un dictionnaire action → valeur.
- `create_bins` — Discrétisation des observations.
- `assign_bins` — Bins pour un vecteur d’observation continu.
- `get_state_as_string` / `get_all_states_as_string` — Clés d’état pour la table Q.
- `initialize_Q` — Table Q initiale.
- `play_one_game` — Un épisode d’apprentissage / évaluation.
- `save_last_commandes` — Sauvegarde commandes et métadonnées dans `Records/`.
- `load_Q_from_file` — Charge une table Q pickle.
- `play_many_games` — Boucle d’épisodes ; option enregistrement.
- `plot_running_avg` — Courbe de la moyenne glissante des récompenses.

### `Agent_qlearning/main_explore_Q.py` — classe `QExplorerApp`

**Méthodes principales** :
- `__init__` — Fenêtre Tk et état de l’explorateur.
- `_build_ui` / `_build_command_panel` — Construction des zones commande, info, affichage 10×10.
- `load_q_from_file` — Dialogue fichier Q dans `Records/`.
- `update_info_label` — Chemin chargé et paramètres de coupe.
- `increment_slice` / `decrement_slice` — Change l’indice de coupe sur la dimension d’état.
- `update_display` — Coloration des cases (visité / non visité) et valeurs Q moyennes.

**Fonction** : `main` — Lance l’application Tk.

---

## `Records/`

Données runtime : commandes enregistrées, tables Q, exports d’exploration (`kart_explore_*.{vtk,pvd,json}`), etc.

---

## Architecture générale (simulateur manuel)

1. **`User_Interface`** — Tkinter, télémesures, panneaux.  
2. **`SimulationUI`** — canvas, record/replay, EXPLORE, liaison `SimulationCore` + `Kart` + `Kart_control`.  
3. **`SimulationCore`** — `step`, écarts trajectoire, chargement T/C.  
4. **`Kart` / `Wheel`** — physique.  
5. **`utils`** — repères et normes.  
6. **`C_et_T`** — définition / export des lignes utilisées comme trajectoire cible.

Flux : `main_simul_manuelle_V1.0.py` → `SimulationUI.start_simulation()` → `animation_step()` (boucle `after`).

**Outil Circuit & Trajectoire** : `C_et_T/main_C_et_T.py` → `CircuitSimulator` → `Circuit` / `Trajectoire` / `Profil`, fond `ImageBackgroundManager`.

**Agents Q** : `SimuKart` et fonctions d’épisodes dans `0-kart_qulearning.py` ; visualisation avec `QExplorerApp` (détail dans `README_Agents.md`).

---

# MODE d'emploi CE CHAPITRE NE DOIT ABSOLUMENT PAS ËTRE MODIFIE PAR CURSOR

Je lance le code et ca marche.
