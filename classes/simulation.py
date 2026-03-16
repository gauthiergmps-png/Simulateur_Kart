import json
import numpy as np
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .kart import Kart

RECORDS_DIR = Path(__file__).resolve().parent.parent / "Records"

try:
    from .user_interface import User_Interface
    from .utils import vehicule2piste, norme_vecteur
except ImportError:
    from user_interface import User_Interface
    from kart import Kart
    from utils import vehicule2piste, norme_vecteur


class SimulationCore:
    """Cœur d'une simulation dynamique du Kart, sans UI.
       recoit des commandes de type controle et paramètres du kart ou de la simulation,
       et propage l'état du kart.
       Pour l'instant on va se servir dans les variables de l'instance Kart pour les observables qu'on veut, à fignoler
    """
    kart: "Kart"

    def __init__(self, kart: "Kart"):
        self.kart = kart
        self.debug = False
        self.reset()
    
    def reset(self):
        """Initialise l'état interne de la simulation."""
        self.temps = 0.0
        self.pas_simul = 0 # index de l'état de la simulation
        self.kart.init_state()
    
    def step(self, dt, kart_controls, simu_controls=None,kart_parametres=None):
        """Un pas de simulation physique (API sans SimulationUI).

        kart_controls : dict commandes pilote (volant, gaz, frein).
        
        simu_controls (optionnel): dict régulateur / asservissement (regul, vold, ass_d, ass_d0, ass_dgain_stat, ass_dgain_dyn).

        kart_parametres (optionnel): dict réglages kart (h_cdg, ouverture, transm).

        Retourne un dict avec : pas_simul, temps, V, gaz, volant.
        """
        self.pas_simul += 1
        if dt != 0.:
            self.temps += dt

        # Mise à jour des paramètres du Kart pendant la simulation si ca nous amuse
        if kart_parametres is not None:
            h_cdg = kart_parametres['h_cdg']
            ouverture = kart_parametres['ouverture']
            transm = kart_parametres['transm']
            self.kart.update_parametres(h_cdg, ouverture, transm)


        volant = kart_controls['volant']
        gaz = kart_controls['gaz']
        frein = kart_controls['frein']

        # Propagation de l'état du kart par application des contrôles
        self.kart.update_state(dt, volant, gaz, frein)
        V = norme_vecteur(self.kart.vitesse)

        # Utilisation des asservissements pour la simulation interactive
        if simu_controls is not None:
            regul = simu_controls['regul']
            vold = simu_controls['vold']
            ass_d = simu_controls['ass_d']
            ass_d0 = simu_controls['ass_d0']
            ass_dgain_stat = simu_controls['ass_dgain_stat']
            ass_dgain_dyn = simu_controls['ass_dgain_dyn']
          
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
            'temps': self.temps,
            'V': V,
            'gaz': gaz,
            'volant': volant,
        }


class SimulationUI(User_Interface):
    """Classe gérant la simulation manuelle avec interfaces utilisateurs Via Tkinter."""
    kart: "Kart"

    def __init__(self, kart: "Kart"):
        """Initialise le gestionnaire de simulation avec UI."""
        super().__init__(kart)

        self.core = SimulationCore(kart)
        self.debug = False
        self.hist_xcdg = []
        self.hist_ycdg = []
        self.replay_status = False
        self.controls_recorded = []
        self.reset()
    
    def reset(self):
        """Initialise l'état de la simulation (UI + core)."""
        print("Reset de la simulation")
        
        # Reset du core
        self.core.reset()
        
        # Variables de controle de la simulation (Tk)
        self.t_cyclemax = 0.
        self.t_framemax = 0.
        self.pas_de_temps.set(25) 
        self.simul_pause = True # donc après un reset, on est en pause
        
        # Variables de commande du kart qui seront issues des interactions utilisateur
        self.volant = 0.
        self.volant_curseur.set(0)  # et volant droit
        self.gaz = 0.
        self.frein = 0

        # Variables du recorder
        self.record_status = False
        if not self.replay_status:
           self.controls_recorded = []
        self.btn_record.config(text="RECORD", state="normal")

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
        
        # Espace = pause simulation (même effet que le bouton PAUSE)
        if event.keysym == "space":
            self._handle_pause()
        
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
    
    def profil_circuit(self, x_cdg, y_cdg, type=0):
        """Retourne un profil complet x,y du circuit"""
        if type == 0:
            # type_circuit = 0: quadrillage 10 x 10 autour du kart
            Xo = np.array([10. * np.floor(x_cdg / 10.), 10. * np.floor(y_cdg / 10.)])
            H = np.array([10., 0.])
            V = np.array([0., 10.])
            
            X = np.array([Xo])
            X = np.append(X, [Xo - V, Xo - V - H, Xo - H, Xo + 2 * H, Xo + 2 * H - V, 
                            Xo + H - V, Xo + H + 2 * V, Xo + 2 * H + 2 * V, 
                            Xo + 2 * H + V, Xo - H + V, Xo - H + 2 * V, Xo + 2 * V], axis=0)
        elif type == 1:
            # type_circuit = 1: anneau de 50m de rayon
            x = np.linspace(0, 2 * np.pi, 100)
            R = 50.
            X = np.zeros((100, 2))
            X[:, 0] = R * np.cos(x)
            X[:, 1] = R * (-1 + np.sin(x))
        else:
            raise ValueError(f"Type de circuit non valide: {type}")

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
        x, y = self.profil_circuit(xcdg, ycdg, type=1)
        circuit = []
        for i in range(0, len(x)):
            circuit += [abs2canvas(x[i], y[i], origx, origy)]
        self.cnv.create_polygon(circuit, outline='black', fill='', width=2)
        
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
        f_cdg=self.kart.force_cdg
        self.cnv.create_line(abs2canvas(xcdg, ycdg, origx, origy),
                            abs2canvas(xcdg + kc / 10000 * f_cdg[0], ycdg + kc / 10000 * f_cdg[1], origx, origy),
                            width=3, fill="red", arrow="last", arrowshape=(18, 20, 3))
        
        # trace du petit arc indiquant le "moment lacet"
        TT1 = 20 / 100 * kc
        TT2 = -1
        m_cdg=self.kart.moment_cdg
        self.cnv.create_arc((abs2canvas(xcdg - TT1, ycdg - TT1, origx, origy), abs2canvas(xcdg + TT1, ycdg + TT1, origx, origy)),
                           outline="red", extent=min(max(-90, TT2 * m_cdg[2]), 90),
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

    def _handle_record(self):
        """Change le status de self.record_status et du bouton RECORD

        Surcharge de la méthode _handle_record de la classe User_Interface
        pour ne la déclencher qu'en début de simulation
        """
        if self.core.pas_simul == 0:        
            self.record_status = True
            # On commence un nouvel enregistrement :
            # - on vide les commandes précédentes
            # - on oublie d'éventuelles conditions initiales provenant d'un fichier de replay
            self.controls_recorded = []
            self.cond_t0_recorded = None
            self.btn_record.config(text="RECORDING", state="disabled")
 
    def read_commands(self):
        """Lit le fichier Records/commandes.txt et remplit controls_recorded + conditions_t0 (+ éventuels parametres) de replay."""
        path_cmd = RECORDS_DIR / "commandes.txt"
        try:
            with open(path_cmd, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Format JSON: contient les conditions initiales et les commandes sous la forme:
                # {"conditions_t0": {position, vitesse, angles, vitangul?, ...},
                #  "parametres": {h_cdg, ouverture, transm},
                #  "steps": [...]}
                # où un step est un dictionnaire: {"volant": x, "gaz": y, "frein": z}
                self.controls_recorded = data["steps"]
                self.cond_t0_recorded = data.get("conditions_t0", {})
                parametres = data.get("parametres")
                if isinstance(parametres, dict):
                    # Si des paramètres dynamiques sont fournis, on les applique via Kart.update_parametres
                    h_cdg = parametres.get("h_cdg", self.kart.h_cdg)
                    ouverture = parametres.get("ouverture", self.kart.ouverture)
                    transm = parametres.get("transm", self.kart.transm)
                    self.kart.update_parametres(h_cdg, ouverture, transm)
            print(f"Commandes lues depuis '{path_cmd}'.")
            # Des commandes sont disponibles : on autorise le bouton REPLAY
            self.btn_replay.config(state="normal")
        except FileNotFoundError:
            print(f"Fichier '{path_cmd}' introuvable, pas de lecture de commandes.")
            self.controls_recorded = []
            self.cond_t0_recorded = None
            # Pas de commandes : on désactive REPLAY
            self.btn_replay.config(state="disabled")

    def record_replay(self):
        """Action sur le bouton REPLAY: rejoue le contenu de self.controls_recorded (déjà renseigné)."""
        self.record_status = False
        # Si aucune commande n'est chargée, on ne lance pas de replay
        if not self.controls_recorded:
            print("Aucune commande enregistrée dans controls_recorded, lancer READ d'abord.")
            return

        # On indique qu'on est en mode replay avant le reset pour ne pas vider controls_recorded
        self.replay_status = True

        self.reset()

        # Initialiser le kart selon les conditions_t0 du fichier (état initial enregistré)
        p = getattr(self, "cond_t0_recorded", None)
        if p:
            position = np.array(p["position"]) if "position" in p else None
            vitesse = np.array(p["vitesse"]) if "vitesse" in p else None
            angles = np.array(p["angles"]) if "angles" in p else None
            vitangul = np.array(p["vitangul"]) if "vitangul" in p else None
            if position is not None or vitesse is not None or angles is not None or vitangul is not None:
                self.kart.init_state(position=position, vitesse=vitesse, angles=angles, vitangul=vitangul)
    
    def animation_step(self):
        """Effectue une étape d'animation (UI + core)
        Ne pas confondre une étape d'animation (L'affichage a lieu et se rafraichi, index N augmente
        Et une étape de simulation (le T simulation augmente de dt par pas))"""
        t0_frame = time.time()  # début du cycle (pour t_cyclemax = temps de frame réel)
        t_frame=0.
        # Récupération des contrôles et paramètres de la simulation à partir de l'interface utilisateur
        simu_controls = {
            'regul': bool(self.regul.get()),
            'vold': getattr(self, 'Vold', 0.),
            'ass_d': bool(self.ass_d.get()),
            'ass_d0': self.ass_d0.get(),
            'ass_dgain_stat': self.ass_dgain_stat.get(),
            'ass_dgain_dyn': self.ass_dgain_dyn.get(),
        }

        # Récupération des contrôles du kart à partir de l'enregistrement ou de l'interface utilisateur
        if self.replay_status and self.core.pas_simul < len(self.controls_recorded):
            kart_controls = self.controls_recorded[self.core.pas_simul]
        else:
            if self.replay_status:
                self.replay_status = False  # fin du replay
            kart_controls = {
                'volant': self.volant_curseur.get(),
                'gaz': self.gaz,
                'frein': self.frein,
            }
        kart_parametres = {
            'h_cdg': self.kart.empattement / 100. * self.H_cdg.get(),
            'ouverture': self.ouverture.get(),
            'transm': self.transm.get(),
        }

        # Si la simulation n'est pas en pause, on avance de dt
        dt = self.pas_de_temps.get() / 1000.
        if not self.simul_pause:     
            t0_cycle = time.time()

            # Enregistrement des oontroles si record on.On affiche le remplissage ou le vidage de la mémoire de commandes
            if self.record_status:
                self.controls_recorded.append(kart_controls)
                F_com=len(self.controls_recorded)
            elif self.replay_status:
                F_com=len(self.controls_recorded)-self.core.pas_simul
            else:
                F_com=0

            # Propagation de l'état du kart par application des contrôles
            state = self.core.step(dt, kart_controls, simu_controls = simu_controls, kart_parametres = kart_parametres)

            if self.core.temps > 1.:
                t_cycle = time.time() - t0_cycle # temps du step physique uniquement 
                self.t_cyclemax = max(t_cycle, self.t_cyclemax)
            V = state['V']
        else:
            t_cycle = 0.
            F_com = 0
            V = norme_vecteur(self.kart.vitesse)

        # Mise à jour position caméra
        self.scale = self.cam_alt.get()
        self.update_camera_position()
        
        # Affichage
        self.dessin_canvas(self.echelle_dyn.get())
        
        # Mise à jour télémesures
        # Temps de cycle max = temps réel d'une frame (step + caméra + dessin + télémesure), en secondes
        self.update_telemetry(self.core.pas_simul, self.core.temps, self.t_cyclemax, self.t_framemax, self.kart.force_cdg, self.kart.moment_cdg,
                            self.kart.position, self.kart.vitesse, self.kart.angles[0], V, self.gaz, F_com, self.kart.v_arbre, 0.)

        t_frame = time.time() - t0_frame
        if not self.simul_pause and self.core.temps > 1.:
            self.t_framemax = max(t_frame, self.t_framemax)

        # Programmation de la prochaine étape avec un délai pour aspect temps réel
        self.after(max(1, int((dt - t_frame) * 1000 -8)), self.animation_step)
    
    def start_simulation(self):
        """Démarre la simulation"""
        print("Lancement animation")
        self.animation_step()
        self.fenetre.mainloop()


