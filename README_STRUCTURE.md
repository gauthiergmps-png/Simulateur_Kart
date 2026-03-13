# Structure du Code - Simulateur de Kart V0.13

## Fichier principal

### main_V0.13.py
- **Fonction principale** : [main()](main_V0.13.py#L12) - Initialise et démarre le simulateur
- **Imports** : Kart, Simulation

## Dossier classes/

### classes/__init__.py
- Fichier vide (package Python)

### classes/kart.py - Classe Kart
**Propriétés** :
- [profil](classes/kart.py#L73) - Profil du kart en repère véhicule
- [profil_absolu](classes/kart.py#L88) - Profil du kart en repère absolu

**Méthodes principales** :
- [__init__](classes/kart.py#L14) - Initialisation (empattement, pos_cdg, voie_av, voie_ar)
- [init_state()](classes/kart.py#L40) - Réinitialise l'état dynamique
- [update_position(dt)](classes/kart.py#L94) - Met à jour la position
- [update_angles(dt)](classes/kart.py#L98) - Met à jour les angles
- [update_vitesse(dt)](classes/kart.py#L103) - Met à jour la vitesse
- [update_vitangul(dt)](classes/kart.py#L109) - Met à jour les vitesses angulaires
- [update_controles(h_cdg, volant, gaz, frein, ouverture, transm)](classes/kart.py#L115) - Contrôles
- [set_forces_Z_roues()](classes/kart.py#L133) - Forces verticales sur roues
- [set_vitesses_roues()](classes/kart.py#L170) - Vitesses des roues
- [set_varbre(puis_mot)](classes/kart.py#L184) - Vitesse arbre arrière
- [set_forces_roues()](classes/kart.py#L246) - Forces d'interaction roue-piste
- [update_force_et_moment_cdg()](classes/kart.py#L292) - Forces et moments au centre de gravité

### classes/simulation.py - Classe Simulation
**Hérite de** : User_Interface

**Méthodes principales** :
- [__init__(kart)](classes/simulation.py#L13) - Initialisation
- [reset()](classes/simulation.py#L25) - Réinitialise la simulation
- [press_key(event)](classes/simulation.py#L51) - Gestion touches clavier
- [stop_key(event)](classes/simulation.py#L106) - Relâchement touches
- [profil_circuit(x_cdg, y_cdg)](classes/simulation.py#L110) - Profil du circuit
- [dessin(kc)](classes/simulation.py#L124) - Dessin du canvas
- [_trace_dyn_roues(kc, origx, origy, lacet)](classes/simulation.py#L216) - Infos dynamiques roues
- [_trace_indicators_gaz_frein()](classes/simulation.py#L241) - Indicateurs gaz/frein
- [_trace_compteur_vitesse()](classes/simulation.py#L249) - Compteur de vitesse
- [animation_step()](classes/simulation.py#L256) - Étape d'animation
- [start_simulation()](classes/simulation.py#L326) - Démarre la simulation

### classes/user_interface.py - Classe User_Interface
**Méthodes principales** :
- [__init__(kart)](classes/user_interface.py#L14) - Initialisation interface
- [_create_main_window()](classes/user_interface.py#L64) - Crée fenêtre principale
- [_create_control_panel()](classes/user_interface.py#L69) - Crée panneau de contrôle
- [_create_canvas()](classes/user_interface.py#L245) - Crée canvas d'animation
- [_setup_key_bindings()](classes/user_interface.py#L250) - Configure raccourcis clavier
- [press_key(event)](classes/user_interface.py#L259) - Gestion touches (à surcharger)
- [stop_key(event)](classes/user_interface.py#L264) - Relâchement touches (à surcharger)
- [_handle_reset()](classes/user_interface.py#L269) - Gestion bouton reset
- [_handle_pause()](classes/user_interface.py#L273) - Gestion bouton pause
- [reset()](classes/user_interface.py#L278) - Méthode abstraite à surcharger
- [pause()](classes/user_interface.py#L283) - Met en pause la simulation
- [update_telemetry(...)](classes/user_interface.py#L293) - Met à jour télémesures
- [update_camera_position()](classes/user_interface.py#L313) - Met à jour position caméra
- [mainloop()](classes/user_interface.py#L320) - Boucle principale
- [after(ms, callback)](classes/user_interface.py#L324) - Programmation d'appel

**Méthodes de création d'interface** :
- [_create_command_frame(frame)](classes/user_interface.py#L138) - Frame commandes
- [_create_propagation_frame(frame)](classes/user_interface.py#L147) - Frame propagation
- [_create_dynamic_scale_frame(frame)](classes/user_interface.py#L159) - Frame échelle dynamique
- [_create_camera_frame(frame)](classes/user_interface.py#L166) - Frame caméra
- [_create_control_buttons_frame(frame)](classes/user_interface.py#L178) - Boutons contrôle
- [_create_steering_frame(frame)](classes/user_interface.py#L184) - Frame volant
- [_create_regulator_frame(frame)](classes/user_interface.py#L196) - Frame régulateur
- [_create_dynamic_control_frame(frame)](classes/user_interface.py#L219) - Frame contrôle dynamique
- [_create_transmission_frame(frame)](classes/user_interface.py#L226) - Frame transmission
- [_create_telemetry_zone()](classes/user_interface.py#L238) - Zone télémesures

### classes/wheel.py - Classe Wheel
**Propriétés** :
- [rayon](classes/wheel.py#L31) - Rayon de la roue
- [largeur](classes/wheel.py#L42) - Largeur de la roue
- [position](classes/wheel.py#L52) - Position de la roue en repère véhicule

**Méthodes principales** :
- [__init__(which_roue, kart)](classes/wheel.py#L10) - Initialisation
- [profil()](classes/wheel.py#L69) - Profil de la roue
- [update_vsol(vsol)](classes/wheel.py#L81) - Met à jour vitesse par rapport au sol
- [update_fz(fz)](classes/wheel.py#L85) - Met à jour force verticale
- [update_controles(varbre, puis_app, frein)](classes/wheel.py#L90) - Met à jour contrôles
- [force()](classes/wheel.py#L101) - Force d'adhérence au sol
- [force_roue_libre()](classes/wheel.py#L118) - Force pour roue libre
- [force_roue_V_force(vf)](classes/wheel.py#L193) - Force pour roue à vitesse forcée

### classes/utils.py - Fonctions utilitaires
**Fonctions de rotation** :
- [tourne_vecteur(V, angle)](classes/utils.py#L6) - Rotation de vecteur(s)
- [vehicule2piste(V, lacet)](classes/utils.py#L17) - Conversion véhicule vers piste
- [piste2vehicule(V, lacet)](classes/utils.py#L18) - Conversion piste vers véhicule
- [roue2vehicule(V, braquage)](classes/utils.py#L19) - Conversion roue vers véhicule
- [vehicule2roue(V, braquage)](classes/utils.py#L20) - Conversion véhicule vers roue

**Fonctions utilitaires** :
- [norme_vecteur(V)](classes/utils.py#L22) - Norme d'un vecteur

## Architecture générale

Le simulateur suit une architecture en couches :
1. **User_Interface** : Interface graphique et contrôles
2. **Simulation** : Logique de simulation (hérite de User_Interface)
3. **Kart** : Modèle physique du véhicule
4. **Wheel** : Modèle des roues individuelles
5. **utils** : Fonctions mathématiques de base

Le flux principal : [main()](main_V0.13.py#L12) → Simulation → Kart → Wheel → utils
