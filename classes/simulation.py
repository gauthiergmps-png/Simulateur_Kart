import numpy as np
import time
try:
    from .user_interface import User_Interface
    from .utils import tourne_vecteur, vehicule2piste, piste2vehicule, norme_vecteur
except ImportError:
    from user_interface import User_Interface
    from utils import tourne_vecteur, vehicule2piste, piste2vehicule, norme_vecteur


class SimulationCore:
    """Cœur de simulation sans Tkinter."""
    
    def __init__(self, kart):
        self.kart = kart
        self.debug = False
        self.reset()
    
    def reset(self):
        """Initialise l'état interne de la simulation."""
        self.temps = 0.0
        self.pas_simul = 0
        self.pas_com = 0
        self.force_cdg = np.array([0., 0., 0.])     #  A QUOI SERT CET ATTIRBUT DANS SIMULATION ?? 
        self.moment_cdg = np.array([0., 0., 0.])
        self.kart.init_state()
    
    def step(self, dt, controls):
        """Un pas de simulation physique.
        
        controls est un dict contenant les actions=commandes envoyées au Kart, et aussi des réglages :
          - h_cdg, volant, gaz, frein, ouverture, transm
          - regul, vold
          - ass_d, ass_d0, ass_dgain_stat, ass_dgain_dyn

          RETOURS A METTRE A JOUR DONC
        """
        self.pas_simul += 1
        if dt != 0.:
            self.pas_com += 1
            self.temps += dt
        
        h_cdg = controls['h_cdg']
        volant = controls['volant']
        gaz = controls['gaz']
        frein = controls['frein']
        ouverture = controls['ouverture']
        transm = controls['transm']
        regul = controls['regul']
        vold = controls['vold']
        ass_d = controls['ass_d']
        ass_d0 = controls['ass_d0']
        ass_dgain_stat = controls['ass_dgain_stat']
        ass_dgain_dyn = controls['ass_dgain_dyn']
        
        # Application des contrôles
        self.kart.update_controles(h_cdg, volant, gaz, frein, ouverture, transm)
        
        # Forces et moments avant propagation
        self.force_cdg = self.kart.force_cdg
        self.moment_cdg = self.kart.moment_cdg
        
        # Propagation de l'état du kart
        self.kart.update_position(dt)
        self.kart.update_angles(dt)
        self.kart.update_vitesse(dt)
        self.kart.update_vitangul(dt)
        self.kart.update_force_et_moment_cdg()
        
        V = norme_vecteur(self.kart.vitesse)
        
        # Régulateur vitesse
        if regul and V != 0.:
            self.kart.vitesse = vold / V * self.kart.vitesse
        
        # Asservissement V_lacet
        if ass_d:
            correction = (ass_dgain_stat * (ass_d0 - self.kart.vitangul[0]) -
                          ass_dgain_dyn * self.kart.vitangul[0])
            volant = max(min(volant + correction, +45.), -45.)
            # Correction appliquée au prochain pas via controls
        
        return {
            'pas_simul': self.pas_simul,
            'pas_com': self.pas_com,
            'temps': self.temps,
            'force_cdg': self.force_cdg,
            'moment_cdg': self.moment_cdg,
            'V': V,
            'gaz': gaz,
            'volant': volant,
        }


class SimulationUI(User_Interface):
    """Classe gérant la simulation manuelle avec interfaces utilisateurs Via Tkinter."""
    
    def __init__(self, kart):
        """Initialise le gestionnaire de simulation avec UI."""
        super().__init__(kart)

        self.core = SimulationCore(kart)
        self.debug = False
        self.hist_xcdg = []
        self.hist_ycdg = []
        self.reset()
    
    def reset(self):
        """Initialise l'état de la simulation (UI + core)."""
        print("Initialisation de l'état de la simulation")
        
        # Reset du core
        self.core.reset()
        
        # Variables de controle de la simulation (Tk)
        self.temps.set(self.core.temps)
        self.pas_simul.set(self.core.pas_simul)
        self.t_cyclemax = 0.
        self.pas_com.set(self.core.pas_com)
        self.dtold = 25
        self.pas_de_temps.set(0)  # donc après un reset, on est en pause
        
        # Variables de commande du kart qui seront issues des interactions utilisateur
        self.volant = 0.
        self.volant_curseur.set(0)  # et volant droit
        self.gaz = 0.
        self.frein = 0
        
        # Variables des forces et moments qui seront affichés
        self.force_cdg = [0., 0., 0.]
        self.moment_cdg = [0., 0., 0.]
        
        # Historique trajet
        self.hist_xcdg = []
        self.hist_ycdg = []
    
    def press_key(self, event):
        """Gère les pressions de touches"""
        # q/w = modification vitesse forcés
        if event.keysym == "d":
            self.kart.vitesse = 1.05*self.kart.vitesse
        if event.keysym == "c":
            self.kart.vitesse = 0.95*self.kart.vitesse
        
        # Volant = Gauche/Droite variations +/- 5°, saturé à 45° - réglage fin = l,m
        if event.keysym == "Left":
            self.volant = max(self.volant - 5., -45.)
            self.volant_curseur.set(self.volant)
        if event.keysym == "Right":
            self.volant = min(self.volant + 5., 45.)
            self.volant_curseur.set(self.volant)
        if event.keysym == "l":
            self.volant = max(self.volant - 1., -45.)
            self.volant_curseur.set(self.volant)
        if event.keysym == "m":
            self.volant = min(self.volant + 1., 45.)
            self.volant_curseur.set(self.volant)
        
        # s/x = gaz up/down - reglage fin avec majuscule
        if event.keysym == "s":
            self.frein = 0
            self.gaz = min(self.gaz + 10, 80)
        if event.keysym == "S":
            self.frein = 0
            self.gaz = min(self.gaz + 1, 80)
        if event.keysym == "x":
            self.gaz = max(0, self.gaz - 10)
        if event.keysym == "X":
            self.gaz = max(0, self.gaz - 1)
        
        # d/c = frein up/down
        if event.keysym == "q":
            self.gaz = 0
            self.frein = min(self.frein + 1, 4)
        if event.keysym == "w":
            self.frein = max(0, self.frein - 1)
        
        # Espace = pause simulation
        if event.keysym == "space":
            self.pause()
        
        # Up/Down: accelleration/ralentissement de la simulation
        if event.keysym == "Up":
            self.pas_de_temps.set(self.pas_de_temps.get() + 5)
        if event.keysym == "Down":
            self.pas_de_temps.set(self.pas_de_temps.get() - 5)
        
        # Appui continu sur t: mode debug
        if event.keysym == "t":
            self.debug = True
    
    def stop_key(self, event):
        """Gère le relâchement des touches"""
        self.debug = False
    
    def profil_circuit(self, x_cdg, y_cdg):
        """Retourne un profil complet x,y du circuit"""
        # type_circuit = 0: quadrillage
        Xo = np.array([10. * np.floor(x_cdg / 10.), 10. * np.floor(y_cdg / 10.)])
        H = np.array([10., 0.])
        V = np.array([0., 10.])
        
        X = np.array([Xo])
        X = np.append(X, [Xo - V, Xo - V - H, Xo - H, Xo + 2 * H, Xo + 2 * H - V, 
                          Xo + H - V, Xo + H + 2 * V, Xo + 2 * H + 2 * V, 
                          Xo + 2 * H + V, Xo - H + V, Xo - H + 2 * V, Xo + 2 * V], axis=0)
        
        return list(X[:, 0]), list(X[:, 1])
    
    def dessin_canvas(self,kc):
        """Fonction de dessin du canvas à chaque pas"""
        # on efface tout, et on calcule l'origine d'affichage
        self.cnv.delete('all')
        
        def abs2canvas(x, y, origx, origy):
            """Conversion de coordonnées absolues en coordonnées canvas"""
            # attention, c'est subtil, ca retourne un tuple de 2 éléments
            return int(origx + self.scale * x), int(origy + self.scale * y)
        
        # les axes d'affichages sont les mêmes axes que kart.position, à translation et échelle près
        origx, origy = int(900 - self.scale * self.xcam), int(500 - self.scale * self.ycam) 
        xcdg, ycdg, _ = list(self.kart.position)
        lacet = self.kart.angles[0]
        
        # CALCUL ET TRACE DU CIRCUIT OU FOND DE PISTE
        x, y = self.profil_circuit(xcdg, ycdg)
        circuit = []
        for i in range(0, len(x)):
            circuit += [abs2canvas(x[i], y[i], origx, origy)]
        self.cnv.create_polygon(circuit, outline='black', fill='', width=1)
        
        # CALCUL ET TRACE DU KART
        x, y = self.kart.profil_absolu
        
        # dessin des cinq polygones chassis + roues
        couleurs = ['black', 'blue', 'orange', 'red', 'yellow']
        coul_roue = couleurs[:]
        
        chassis = []
        for i in range(0, 4):
            chassis += [abs2canvas(x[i], y[i], origx, origy)]
        self.cnv.create_polygon(chassis, outline='black', fill=couleurs[self.kart.coul_chassis], width=1)
        
        coul_roue[1] = couleurs[self.kart.gavg]
        coul_roue[2] = couleurs[self.kart.gavd]
        coul_roue[3] = couleurs[self.kart.garg]
        coul_roue[4] = couleurs[self.kart.gard]
        
        for roue in range(1, 5):
            polygone = []
            for point in range(0, 4):
                i = 4 * roue + point
                polygone += [abs2canvas(x[i], y[i], origx, origy)]
            self.cnv.create_polygon(polygone, outline='black', fill=coul_roue[roue], width=1)
        
        # ENREGISTREMENT ET TRACE D'UNE QUEUE DE TRAJECTOIRE
        self.hist_xcdg.append(xcdg)
        self.hist_ycdg.append(ycdg)
        
        # Limiter l'historique à 50 points
        if len(self.hist_xcdg) > 50:
            self.hist_xcdg.pop(0)
            self.hist_ycdg.pop(0)
        
        # Créer la queue de points pour le dessin
        queue = []
        for i in range(len(self.hist_xcdg)):
            queue += [abs2canvas(self.hist_xcdg[i], self.hist_ycdg[i], origx, origy)]
        
        # Dessiner la traînée si on a au moins 2 points
        if len(queue) > 1:
            self.cnv.create_line(*queue, fill='red', dash=(2, 20), width=1)
        
        # CALCUL ET TRACE DES INFORMATIONS DYNAMIQUES
        # trace de la flèche "vitesse"
        vitesse = vehicule2piste(self.kart.vitesse, lacet)
        self.cnv.create_line(abs2canvas(xcdg, ycdg, origx, origy),
                            abs2canvas(xcdg + kc / 10 * vitesse[0], ycdg + kc / 10 * vitesse[1], origx, origy),
                            width=3, fill="blue", arrow="last", arrowshape=(18, 20, 3))
        
        # trace de la flèche "force cdg"
        self.cnv.create_line(abs2canvas(xcdg, ycdg, origx, origy),
                            abs2canvas(xcdg + kc / 10000 * self.force_cdg[0], ycdg + kc / 10000 * self.force_cdg[1], origx, origy),
                            width=3, fill="red", arrow="last", arrowshape=(18, 20, 3))
        
        # trace du petit arc indiquant le "moment lacet"
        TT1 = 20 / 100 * kc
        TT2 = -1
        self.cnv.create_arc((abs2canvas(xcdg - TT1, ycdg - TT1, origx, origy), abs2canvas(xcdg + TT1, ycdg + TT1, origx, origy)),
                           outline="red", extent=min(max(-90, TT2 * self.moment_cdg[2]), 90),
                           start=-180. * lacet / np.pi, fill='', width=3, style="arc")
        
        # Affichage info dynamiques des roues
        self._trace_dyn_roues(kc, origx, origy, lacet)
        
        # affichage indicateurs gaz/frein
        self._trace_indicators_gaz_frein()
        
        # affichage compte tour et vitesse
        self._trace_compteur_vitesse()
    
    def _trace_dyn_roues(self, kc, origx, origy, lacet):
        """Trace les informations dynamiques des roues"""
        def trace_dyn(position, poid, force, rayonstat):
            rayon = -rayonstat * force[2] / poid
            self.cnv.create_oval(self.scale * (position[0] - rayon) + origx, self.scale * (position[1] - rayon) + origy,
                                self.scale * (position[0] + rayon) + origx, self.scale * (position[1] + rayon) + origy,
                                outline="green", width=3)
            if force[2] != 0.:
                self.cnv.create_line(self.scale * position[0] + origx, self.scale * position[1] + origy,
                                   self.scale * (position[0] - rayon * force[0] / force[2]) + origx,
                                   self.scale * (position[1] - rayon * force[1] / force[2]) + origy,
                                   width=3, fill="green", arrow="last")
        
        r_av = self.kart.roue_avg.rayon
        r_ar = self.kart.roue_arg.rayon
        
        trace_dyn(self.kart.position + vehicule2piste(self.kart.roue_avg.position, lacet),
                 self.kart.pavg, vehicule2piste(self.kart.favg, lacet), kc * r_av)
        trace_dyn(self.kart.position + vehicule2piste(self.kart.roue_avd.position, lacet),
                 self.kart.pavd, vehicule2piste(self.kart.favd, lacet), kc * r_av)
        trace_dyn(self.kart.position + vehicule2piste(self.kart.roue_arg.position, lacet),
                 self.kart.parg, vehicule2piste(self.kart.farg, lacet), kc * r_ar)
        trace_dyn(self.kart.position + vehicule2piste(self.kart.roue_ard.position, lacet),
                 self.kart.pard, vehicule2piste(self.kart.fard, lacet), kc * r_ar)
    
    def _trace_indicators_gaz_frein(self):
        """Trace les indicateurs de gaz et frein"""
        self.cnv.create_rectangle(30, 30, 50, 110, fill='white', outline='black')
        self.cnv.create_rectangle(30, int(110 - self.frein * 20), 50, 110, fill='red', outline='')
        self.cnv.create_rectangle(60, 30, 80, 110, fill='white', outline='black')
        self.cnv.create_rectangle(60, int(110 - self.gaz * 80. / 100.), 80, 110, fill='springgreen', outline='')
        self.cnv.create_text(68, 100, text=str(int(self.gaz)), font="Arial 10", fill="black")
    
    def _trace_compteur_vitesse(self):
        """Trace le compteur de vitesse"""
        V = 3.6 * norme_vecteur(self.kart.vitesse)
        self.cnv.create_arc((100, 40), (190, 130), outline="cyan", extent=max(-240, -2 * V), start=210,
                           fill='', width=20, style="arc")
        self.cnv.create_text(143, 80, text=str(int(V)), font="Arial 18", fill="white")
    
    def animation_step(self):
        """Effectue une étape d'animation (UI + core)"""
        start = time.time()
        
        dt = self.pas_de_temps.get() / 1000.
        
        controls = {
            'h_cdg': self.kart.empattement / 100. * self.H_cdg.get(),
            'volant': self.volant_curseur.get(),
            'gaz': self.gaz,
            'frein': self.frein,
            'ouverture': self.ouverture.get(),
            'transm': self.transm.get(),
            'regul': bool(self.regul.get()),
            'vold': getattr(self, 'Vold', 0.),
            'ass_d': bool(self.ass_d.get()),
            'ass_d0': self.ass_d0.get(),
            'ass_dgain_stat': self.ass_dgain_stat.get(),
            'ass_dgain_dyn': self.ass_dgain_dyn.get(),
        }
        
        state = self.core.step(dt, controls)
        
        self.pas_simul.set(state['pas_simul'])
        self.pas_com.set(state['pas_com'])
        self.temps.set(state['temps'])
        self.force_cdg = state['force_cdg']
        self.moment_cdg = state['moment_cdg']
        V = state['V']
        self.gaz = state['gaz']
        self.volant = state['volant']
        self.volant_curseur.set(self.volant)
        
        # Mise à jour position caméra
        self.scale = self.cam_alt.get()
        self.update_camera_position()
        
        # Affichage
        self.dessin_canvas(self.echelle_dyn.get())
        
        # Mise à jour télémesures
        self.update_telemetry(self.pas_simul.get(), self.temps.get(), self.t_cyclemax, self.force_cdg, self.moment_cdg,
                            self.kart.position, self.kart.vitesse, self.kart.angles[0], V, self.gaz, self.F_com, self.kart.v_arbre, 0.)
        
        # Calcul du temps de cycle
        t_cycle = time.time() - start
        if state['temps'] > 1.:
            self.t_cyclemax = max(t_cycle, self.t_cyclemax)
        
        # Programmation de la prochaine étape
        self.after(max(1, int((dt - t_cycle) * 1000)), self.animation_step)
    
    def start_simulation(self):
        """Démarre la simulation"""
        print("Lancement animation")
        self.animation_step()
        self.fenetre.mainloop()


