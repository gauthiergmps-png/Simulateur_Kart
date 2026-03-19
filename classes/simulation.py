import json
import sys
import numpy as np
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_DIR / "Records"
sys.path.insert(0, str(PROJECT_DIR))
from classes.kart import Kart
from classes.user_interface import User_Interface
from classes.utils import vehicule2piste, piste2vehicule, norme_vecteur
from C_et_T.C_et_T_classes.circuit_et_trajectoire import Circuit, Trajectoire

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .kart import Kart

class SimulationCore:
    """Cœur d'une simulation dynamique du Kart, sans UI.
       recoit des commandes de type controle et paramètres du kart d'un environnement extérieur
       et propage l'état du kart.
       Pour l'instant on va se servir dans les variables de l'instance Kart pour les observables qu'on veut, à fignoler
    """
    kart: "Kart"

    def __init__(self, kart: "Kart"):
        self.kart = kart
        self.debug = False
        self.regul=False
        self.vold = 0.
        self.reset()
        self.trajectoire = None
        self.last_index_traj=0
    
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
            ass_d = simu_controls['ass_d']
            ass_d0 = simu_controls['ass_d0']
            ass_dgain_stat = simu_controls['ass_dgain_stat']
            ass_dgain_dyn = simu_controls['ass_dgain_dyn']
          
            # Régulateur vitesse
            if not self.regul and regul and V != 0.:
                # On vient de d'allumer le régulateur de vitesse
                self.regul = True
                self.vold = V
            elif self.regul and regul:
                # On continue à réguler la vitesse
                self.kart.vitesse = self.vold / V * self.kart.vitesse
            elif self.regul and not regul:
                # On vient de déconecter le régulateur de vitesse
                self.regul = False
                self.vold = 0.
            
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

    def load_trajectoire_from_json(self):
        """Ouvre le dialogue de chargement (Tk) et affecte la trajectoire chargée à ``self.trajectoire``.

        Annulation du dialogue ou erreur : ``self.trajectoire`` n'est pas modifié.
        """
        new_traj = Trajectoire.load_trajectory_dialog()
        if new_traj is not None:
            self.trajectoire = new_traj
            self.last_index_traj=0
    
    def ecart_trajectoire(self):
        """Calcule l'écart entre la position actuelle du Kart et la trajectoire cible
        """
        if self.trajectoire is None:
            return 0.

        pos_xy = self.kart.position[0:2]  # on ne garde donc que 2 coordonnées dans le vecteur pos_xy

        # depuis le dernier appel, le kart a du avancer, identifions le nouvel index du point fin le plus proche du kart
        # idx=self.last_index_traj
        # dist_last =np.linalg.norm(self.trajectoire.fine_points[idx] - pos_xy)
        # dist_next=np.linalg.norm(self.trajectoire.fine_points[idx+1] - pos_xy)
        # while dist_last > dist_next:
        #     idx+=1
        #     dist_last=dist_next
        #     dist_next=np.linalg.norm(self.trajectoire.fine_points[idx+1] - pos_xy)
        d_min=10000000
        idx=0
        for i in range(len(self.trajectoire.fine_points)):
            d=np.linalg.norm(self.trajectoire.fine_points[i] - pos_xy)
            if d < d_min:
                d_min=d
                idx=i
        self.last_index_traj=idx

        # maintenant calculons l'écart comme étant la projection point kart sur le vecteur normal à la trajectoire
        vect_pt_kart=pos_xy - self.trajectoire.fine_points[idx]
        normal=self.trajectoire.normals[idx]
        ecart=np.dot(vect_pt_kart, normal)
            
        return ecart

class SimulationUI(User_Interface):
    """Classe gérant la simulation manuelle avec interfaces utilisateurs Via Tkinter.
     Elle hérite de la classe User_interface donc de tous ses attributs et méthodes."""

    # Déclaration de type pour le linter
    kart: "Kart"


    def __init__(self):
        """Initialise le gestionnaire de simulation avec UI."""
        super().__init__()

        # Création des instances 
        self.kart = Kart()
        self.core = SimulationCore(self.kart)

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
    
    def profil_circuit(self, x_cdg, y_cdg):
        """Retourne un profil complet du circuit en coordonnées absolues
           Ne sert en fait qu'avec type_circuit = 0: quadrillage 10 x 10 autour du kart
           la trajectoire cible sera affichée par une autre fonction        
        """
        def profil_segment(P0, P2):
            L = np.linalg.norm(P2 - P0)
            n = int (L)
            x = np.linspace(P0[0], P2[0], n-1)
            y = np.linspace(P0[1], P2[1], n-1)
            return x, y

        def profil_arc(C, R, theta_start, theta_end):
            # attention, Y+ est vers le bas, donc les angles sont inversés par rapport au sens trigonométrique
            n = int (3.14 * R )
            t = np.linspace(theta_start, theta_end, n)[:-1]
            x = C[0] + R * np.cos(t)
            y = C[1] + R * np.sin(t)
            return x, y

        if self.circuit.get() == 0:
            # type_circuit = 0: quadrillage 10 x 10 autour du kart
            Xo = np.array([10. * np.floor(x_cdg / 10.), 10. * np.floor(y_cdg / 10.)])
            H = np.array([10., 0.])
            V = np.array([0., 10.])
            
            X = np.array([Xo])
            X = np.append(X, [Xo - V, Xo - V - H, Xo - H, Xo + 2 * H, Xo + 2 * H - V, 
                            Xo + H - V, Xo + H + 2 * V, Xo + 2 * H + 2 * V, 
                            Xo + 2 * H + V, Xo - H + V, Xo - H + 2 * V, Xo + 2 * V], axis=0)
        elif self.circuit.get() == 1:
            # type_circuit = 1: Axe_X, donc un segment 
            X = np.array([[-10., 0.], [10., 10.]])
        elif self.circuit.get() == 2:
            # type_circuit = 2: cercle de 50m de rayon
            x = np.linspace(0, 2 * np.pi, 100)
            R = 50.
            X = np.zeros((100, 2))
            X[:, 0] = R * np.cos(x)
            X[:, 1] = R * (-1 + np.sin(x))
        elif self.circuit.get() == 3:
            # type_circuit = 3: ligne droite 60m vers +X, puis demi cercle virage à gauche de rayon de 30m, 
            # donc vers -X, puis ligne droite de longeur 30m vers -X, puis quart de cerle à droite rayon de 30m, 
            # puis une ligne droite vers -Y de longueur 20m, puis demi cercle à gauche de 20 m de rayon, 
            # un bout de ligne droite de longueur 40m vers -Y (car +Y est orienté vers le bas), 
            # puis un quart de cercle à droite de rayon de 40m pour revenir sur l'origine
            # on vise un point par mêtre en gros

            # Point de départ et cap initial (vers +X)
            P0 = np.array([0., 0.])

            # 1) Segment de 60 m vers +X, on s'arrête un mêtre  avant d'arriver au point final
            P1 = P0 + np.array([60., 0.])
            x1, y1 = profil_segment(P0, P1)

            # 2) A partir de P1, Demi-cercle à gauche, rayon 30 m
            C = P1 + np.array([0., -30.])
            x2, y2 = profil_arc(C, 30.,np.pi / 2, -np.pi / 2)
        
            # 3) A partir de P2,Segment de 30 m vers -X, on s'arrête un mêtre  avant d'arriver au point final
            P2= C + np.array([0., -30.])
            P3 = P2 + np.array([-30., 0.])
            x3, y3 = profil_segment(P2, P3)

            # 4) A partir de P3, Quart de cercle à droite, rayon 30 m
            C = P3 + np.array([0., -30.])
            x4, y4 = profil_arc(C, 30., np.pi / 2, np.pi)

            # 5) A partir de P4, Ligne droite 20 m vers -Y, on s'arrête un mêtre  avant d'arriver au point final
            P4 = P3 + np.array([-30., -30.])
            P5 = P4 + np.array([0., -20.])
            x5, y5 = profil_segment(P4, P5)

            # 6) A partir de P5, Demi-cercle à gauche, rayon 20 m
            C = P5 + np.array([-20., 0.])
            x6, y6 = profil_arc(C, 20., 0. , -np.pi)

            # 7) A partir de P6, Ligne droite 40 m vers +Y, on s'arrête un mêtre  avant d'arriver au point final
            P6 = P5 + np.array([-40., 0.])
            P7 = P6 + np.array([0., 70.])
            x7, y7 = profil_segment(P6, P7)

            # # 8) A partir de P7, Quart de cercle à droite, rayon 40 m, pour revenir à proximité de l'origine (A DEFINIR précisément)
            C = P7 + np.array([40., 0.])
            x8, y8 = profil_arc(C, 40., np.pi, np.pi / 2)

            # Concaténation de tous les segments / arcs :
            # X_x est la juxtaposition des listes x1, x2, x3 (et idem pour Y)
            X_x = np.concatenate([x1, x2, x3, x4, x5, x6, x7, x8])
            X_y = np.concatenate([y1, y2, y3, y4, y5, y6, y7, y8])
            X = np.column_stack((X_x, X_y))
        else:
            raise ValueError(f"Type de circuit non valide: {type}")

        return list(X[:, 0]), list(X[:, 1])

    def _handle_load_traj(self):
        """Gère l'action de chargement de la trajectoire cible
        Sera chargé dans la classe SimulationUI"""
        self.core.load_trajectoire_from_json()
    
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
        circuit = [abs2canvas(x[i], y[i], origx, origy) for i in range(len(x))]
        self.cnv.create_polygon(circuit, outline='black', fill='', width=2)

        # TRACE DE LA TRAJECTOIRE CIBLE
        if self.core.trajectoire is not None:
            fp = np.asarray(self.core.trajectoire.fine_points, dtype=float)
            # `fine_points` est attendu sous forme (N, 2). Si ce n'est pas le cas,
            # on évite de planter et on ne dessine rien.
            if fp.ndim == 2 and fp.shape[1] >= 2 and len(fp) >= 2:
                trajectoire = [abs2canvas(fp[i, 0], fp[i, 1], origx, origy) for i in range(len(fp))]
                # Tkinter Canvas attend des points (x,y) séparés en arguments, ou une liste aplatie.
                self.cnv.create_line(*trajectoire, fill='red', width=2)
        
            # trace de la flèche "normale" à la trajectoire
            # pt_start = self.core.trajectoire.fine_points[self.core.last_index_traj]
            # traj_normal = self.core.trajectoire.normals[self.core.last_index_traj]
            # pt_end = pt_start + traj_normal
            # self.cnv.create_line(abs2canvas(pt_start[0], pt_start[1], origx, origy),
            #                 abs2canvas(pt_end[0], pt_end[1], origx, origy),
            #                 width=3, fill="blue", arrow="last", arrowshape=(18, 20, 3))
        
        # CALCUL ET TRACE DU KART
        x, y = self.kart.profil_absolu
        
        # dessin des cinq polygones chassis + roues
        couleurs = ['black', 'blue', 'orange', 'red', 'yellow']
        coul_roue = couleurs[:]
        
        chassis = [abs2canvas(x[i], y[i], origx, origy) for i in range(4)]
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
    
    def update_telemetry(self, V, F_com):
        """ Tous les calculs numériques sont faits ici, avant l'appel à show_telemetry de la classe User_Interface
        """

        f_cdg_vec = piste2vehicule(self.kart.force_cdg, self.kart.angles[0])
        norme_f_cdg = norme_vecteur(f_cdg_vec)

        # calcul du rayon de courbure de la trajectoire du kart à partir de la force appliquée au cdg
        radius = ( 1000000000.0 if norme_f_cdg < 0.00001 else self.kart.masse * V * V / norme_f_cdg)

        t_cyclemax_ms = int(self.t_cyclemax * 1000)
        t_framemax_ms = int(self.t_framemax * 1000)

        pos_x, pos_y, pos_z = self.kart.position
        vit_x, vit_y, _ = self.kart.vitesse
        lacet_deg = self.kart.angles[0] * 180.0 / np.pi
        V_kmh = V * 3.6
        f_cdg_x, f_cdg_y, f_cdg_z = f_cdg_vec
        moment_cdg_z = self.kart.moment_cdg[2]

        vold=self.core.vold
        idx=self.core.last_index_traj
        ecart=self.core.ecart_trajectoire()

        varbre = self.kart.v_arbre
        vstab = float(np.dot(f_cdg_vec, vehicule2piste(self.kart.vitesse, self.kart.angles[0])))

        self.show_telemetry(self.core.pas_simul, self.core.temps, t_cyclemax_ms, t_framemax_ms, F_com,
                              pos_x, pos_y, pos_z, vit_x, vit_y, lacet_deg, V, V_kmh, self.gaz, vold, idx, ecart,
                              f_cdg_x, f_cdg_y, f_cdg_z, norme_f_cdg, moment_cdg_z, radius, varbre, vstab)    

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
        self.update_camera_position(self.kart.position)
        
        # Affichage
        self.dessin_canvas(self.echelle_dyn.get())
        
        # Mise à jour télémesures
        self.update_telemetry(V, F_com)      

        # Temps de cycle max = temps réel d'une frame (step + caméra + dessin + télémesure), en secondes
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


