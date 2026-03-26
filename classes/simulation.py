import json
import sys
import numpy as np
import time
from pathlib import Path
from tkinter import TclError

PROJECT_DIR = Path(__file__).resolve().parent.parent
RECORDS_DIR = PROJECT_DIR / "Records"
sys.path.insert(0, str(PROJECT_DIR))
from classes.kart import Kart
from classes.kart_control import Kart_control
from classes.user_interface import User_Interface
from classes.utils import vehicule2piste, piste2vehicule, norme_vecteur
from C_et_T.C_et_T_classes.circuit_et_trajectoire import Circuit, load_C_or_T__dialog

from typing import TYPE_CHECKING, Iterator, Optional, Tuple, Any
if TYPE_CHECKING:
    from .kart import Kart


def _safe_tk_var_float(var: Any, default: float = 0.0) -> float:
    """Lit une Variable Tk (StringVar, IntVar, DoubleVar, etc.) sans lever si valeur absente ou invalide.
    Spinbox / Entry reliés à un IntVar peuvent provoquer TclError sur .get() pendant la saisie."""
    try:
        return float(var.get())
    except (TclError, ValueError, TypeError):
        return float(default)


class SimulationCore:
    """Cœur d'une simulation dynamique du Kart, sans UI.
       recoit des commandes de type controle et paramètres du kart d'un environnement extérieur
       et propage l'état du kart.
       L'environement extérieur doit donc:
          - propager l'état par la méthode step() de cette classe.
          - observer les écarts à la trajectoire cible par la méthode get_observations() de cette classe.
          - agir par la méthode de son choix sur les contrôles du kart.
    """
    def __init__(self, kart: "Kart"):
        self.kart = kart

        #: Trajectoire cible: None si on en pas chargé, sinon c'estl'instance d'une classe 
        # class:`Trajectoire` ou :class:`Circuit` dont la partie "profil" sera la trajectoire cible
        self.traj_cible = None

        #: Bordures du circuit (``circuit_data``), ou ``None`` si la traj_cible est une trajectoire seule.
        self.left_border = None   # None si la traj_cible est une trajectoire seule, sinon liste des points de la bordure gauche
        self.right_border = None  # None si la traj_cible est une trajectoire seule, sinon liste des points de la bordure droite
        self.reset()
    
    def reset(self):
        """Initialise l'état interne de la simulation.
        Si une trajectoire cible a été chargée, positionne le kart au premier point et l'orientation tangente."""
        self.temps = 0.0
        self.pas_simul = 0 # index de l'état de la simulation
        self.regul = False
        self.vold = 0.

        if self.traj_cible is not None and len(self.traj_cible.fine_points) > 0:
            position = np.zeros(3)
            position[0:2] = self.traj_cible.fine_points[0]
            lacet=np.arctan2(self.traj_cible.tangents[0][1], self.traj_cible.tangents[0][0])
            angles = np.array([lacet, 0., 0.])
        else:
            position = np.zeros(3)
            angles = np.array([0., 0., 0.])

        self.kart.init_state(position=position, angles=angles)
    
    def step(self, dt, kart_controls, simu_controls=None,kart_parametres=None):
        """Un pas de simulation physique (API sans SimulationUI).
           Arguments:
                  kart_controls : dict commandes pilote (volant, gaz, frein).
                  simu_controls (optionnel): dict régulateur / asservissement (regul, vold).
                  kart_parametres (optionnel): dict réglages kart (h_cdg, ouverture, transm, pos_cdg optionnel).

            Return: un dict avec : pas_simul, temps, V, gaz, volant.


        Simulcore offre une fonction régulation de  vitesse.
        """

        if dt != 0.:
            self.pas_simul += 1
            self.temps += dt

        # Mise à jour des paramètres du Kart pendant la simulation si ca nous amuse
        if kart_parametres is not None:
            h_cdg = kart_parametres['h_cdg']
            ouverture = kart_parametres['ouverture']
            transm = kart_parametres['transm']
            pos_cdg = kart_parametres.get('pos_cdg')
            self.kart.init_parametres(h_cdg=h_cdg, ouverture=ouverture, transm=transm, pos_cdg=pos_cdg)


        volant = kart_controls['volant']
        gaz = kart_controls['gaz']
        frein = kart_controls['frein']

        # Propagation de l'état du kart par application des contrôles
        self.kart.update_state(dt, volant, gaz, frein)
        V = norme_vecteur(self.kart.vitesse)

        # Utilisation des asservissements pour la simulation interactive
        if simu_controls is not None:
            regul = simu_controls['regul']
          
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
        
        return {'pas_simul': self.pas_simul,'temps': self.temps, 'V': V,'gaz': gaz,'volant': volant}

    def load_T_or_C(self):
        """Ouvre le dialogue de chargement (Tk), charge un JSON trajectoire ou circuit.

        - La partie profil devient ``self.traj_cible`` (ligne de référence pour écarts et reset).
        - Si c'est un :class:`Circuit`, copie ``left_border`` / ``right_border`` pour affichage ou usage ultérieur.
        - Annulation du dialogue : ``self.traj_cible`` et les bordures ne sont pas modifiés.
        """
        loaded = load_C_or_T__dialog()
        if loaded is not None:
            self.traj_cible = loaded
            if isinstance(loaded, Circuit):
                self.left_border = list(loaded.left_border) if loaded.left_border else []
                self.right_border = list(loaded.right_border) if loaded.right_border else []
            else:
                self.left_border = None
                self.right_border = None

        self.reset()

    def get_observations(self) -> Optional[Tuple[int, float, float, float, float, float]]:
        """Calcule les éléments observables suivant:
             - l'écart latéral entre la position actuelle du Kart et la trajectoire cible
             - la vitesse laterale du kart par rapport à la trajectoire
             - la vitesse longitudinale du kart par rapport à la trajectoire
             - la courbature de la trajectoire au plus proche du kart,
             - la courbature de la trajectoire à X secondes devant le kart

        Retour : ``(idx, ecart_lat, V_lat_traj, V_traj, curv, curv_N)``, ou ``None`` si aucune traj_cible n'est chargée.
        """

        pos_xy = self.kart.position[0:2]  # on ne garde donc que 2 coordonnées dans le vecteur pos_xy

        # Identification du point fin de la trajectoire le plus proche du kart
        d_min=10000000.
        idx=0
        for i in range(len(self.traj_cible.fine_points)):
            d=np.linalg.norm(self.traj_cible.fine_points[i] - pos_xy)
            if d < d_min:
                d_min=d
                idx=i

        # Calcul de l'écart latéral du Kart donné par la projection du cdg sur le vecteur normal à la trajectoire
        vect_pt_kart=pos_xy - self.traj_cible.fine_points[idx]
        normal=self.traj_cible.normals[idx]
        ecart=np.dot(vect_pt_kart, normal)

        # Calcul de la vitesse laterale du kart par rapport à la trajectoire
        vit_xy=vehicule2piste(self.kart.vitesse, self.kart.angles[0])[0:2]
        v_lat_traj= np.dot(normal, vit_xy)

        # Courbatures: point courant et courbature plus loin sur la trajectoire (avance d'arc ~ v_traj / X)
        curv = self.traj_cible.curvatures[idx]
        X = 2.0   # Donc un point qu'on attendra dans X secondes
        tangent=self.traj_cible.tangents[idx]
        v_traj=np.dot(tangent, vit_xy)
        dist_ahead = v_traj / X
        d_along = 0.0
        next_i = idx
        n_pts = len(self.traj_cible.fine_points)
        # distances[i] = longueur du segment i → i+1 ; au dernier point ouvert elle vaut 0 : il faut avancer
        # l'indice, sinon ``d_along`` ne bouge pas et la boucle ne termine pas.
        while d_along < dist_ahead and next_i < n_pts - 1:
            step = float(self.traj_cible.distances[next_i])
            if step < 1e-12:
                next_i += 1
                continue
            d_along += step
            next_i += 1
        curv_N = self.traj_cible.curvatures[min(next_i, n_pts - 1)]

        return int(idx), float(ecart), float(v_lat_traj), float(v_traj), float(curv), float(curv_N)

class SimulationUI(User_Interface):
    """Classe gérant la simulation manuelle avec interfaces utilisateurs Via Tkinter.
     Elle hérite de la classe User_interface donc de tous ses attributs et méthodes.
     
     Les méthodes Explore permettent un mode specifique permettant de tabuler sur tous les états possibles du Kart
     et d'enregistrer les résultats dans un fichier lisible par Paraview"""

    # Déclaration de type pour le linter
    kart: "Kart"

    def __init__(self):
        """Initialise le gestionnaire de simulation avec UI."""
        super().__init__()

        # Création des instances 
        self.kart = Kart()
        self.core = SimulationCore(self.kart)
        self.kart_control = Kart_control()

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
        self.explore_status = False
        
        # Variables de commande du kart qui seront issues des interactions utilisateur
        self.volant = 0.
        self.gaz = 0.
        self.frein = 0

        # Variables du recorder
        self.record_status = False
        if not self.replay_status:
           self.controls_recorded = []
        if self.btn_record:
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
        if event.keysym == "Right":
            self.volant = min(self.volant + 5., 45.)
        if event.keysym == "l":
            self.volant = max(self.volant - 1., -45.)
        if event.keysym == "m":
            self.volant = min(self.volant + 1., 45.)
        
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

    def _handle_load_T_or_C(self):
        """Gère l'action de chargement de la trajectoire cible
        Sera chargé dans la classe SimulationUI"""
        self.core.load_T_or_C()
    
    def dessin_canvas(self,kc):
        """Fonction de dessin du canvas à chaque pas"""
        # on efface tout, et on calcule l'origine d'affichage
        self.cnv.delete('all')
        
        def abs2canvas(x, y, origx, origy):
            """Conversion de coordonnées absolues en coordonnées canvas"""
            # attention, c'est subtil, ca retourne un tuple de 2 éléments
            return int(origx + self.scale * x), int(origy + self.scale * y)
        
        # les axes d'affichages sont les mêmes axes que kart.position, à translation et échelle près
        # offset_y = -100 pour affichage confortable sur portable
        offset_y = -100
        origx, origy = int(900 - self.scale * self.xcam), int(500 - self.scale * self.ycam + offset_y)
        xcdg, ycdg, _ = list(self.kart.position)
        lacet = self.kart.angles[0]
        
        # CALCUL ET TRACE DU CIRCUIT OU FOND DE PISTE
        if self.scale>49:
            x, y = self.profil_circuit(xcdg, ycdg)
            circuit = [abs2canvas(x[i], y[i], origx, origy) for i in range(len(x))]
            self.cnv.create_polygon(circuit, outline='black', fill='', width=2)

        # Bordures circuit (si chargement JSON circuit avec circuit_data)
        if self.core.left_border is not None and len(self.core.left_border) >= 2:
            lb = np.asarray(self.core.left_border, dtype=float)
            if lb.ndim == 2 and lb.shape[1] >= 2:
                pts = [abs2canvas(lb[i, 0], lb[i, 1], origx, origy) for i in range(len(lb))]
                self.cnv.create_line(*pts, fill='gray35', width=2)
        if self.core.right_border is not None and len(self.core.right_border) >= 2:
            rb = np.asarray(self.core.right_border, dtype=float)
            if rb.ndim == 2 and rb.shape[1] >= 2:
                pts = [abs2canvas(rb[i, 0], rb[i, 1], origx, origy) for i in range(len(rb))]
                self.cnv.create_line(*pts, fill='gray35', width=2)

        # TRACE DE LA TRAJECTOIRE CIBLE (axe profil)
        if self.core.traj_cible is not None:
            fp = np.asarray(self.core.traj_cible.fine_points, dtype=float)
            # `fine_points` est attendu sous forme (N, 2). Si ce n'est pas le cas,
            # on évite de planter et on ne dessine rien.
            if fp.ndim == 2 and fp.shape[1] >= 2 and len(fp) >= 2:
                trajectoire = [abs2canvas(fp[i, 0], fp[i, 1], origx, origy) for i in range(len(fp))]
                # Tkinter Canvas attend des points (x,y) séparés en arguments, ou une liste aplatie.
                self.cnv.create_line(*trajectoire, fill='red', dash=(4,2), width=1)

                # # trace de la flèche "normale" à la trajectoire cible
                # nfp = len(self.core.traj_cible.fine_points)
                # idx_n = min(self.idx, nfp - 1) if nfp else 0
                # if nfp > 0 and len(self.core.traj_cible.normals) > idx_n:
                #     pt_start = self.core.traj_cible.fine_points[idx_n]
                #     traj_normal = self.core.traj_cible.normals[idx_n]
                #     pt_end = pt_start + np.asarray(traj_normal, dtype=float)
                #     self.cnv.create_line(abs2canvas(pt_start[0], pt_start[1], origx, origy),
                #                     abs2canvas(pt_end[0], pt_end[1], origx, origy),
                #                     width=3, fill="blue", arrow="last", arrowshape=(18, 20, 3))
        
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
        
        # Créer la queue de points pour le dessin (1 point sur 5 : moins de segments, dash lisible)
        queue = []
        hist_n = len(self.hist_xcdg)
        for i in range(0, hist_n, 5):
            queue += [abs2canvas(self.hist_xcdg[i], self.hist_ycdg[i], origx, origy)]
        if hist_n > 0 and (hist_n - 1) % 5 != 0:
            queue += [abs2canvas(self.hist_xcdg[-1], self.hist_ycdg[-1], origx, origy)]
        
        # Dessiner la traînée si on a au moins 2 points
        if len(queue) > 1:
            self.cnv.create_line(*queue, fill='yellow', dash=(2, 200), width=1)
        
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
        
        # # trace du petit arc indiquant le "moment lacet" - ancienne version
        # TT1 = 20 / 100 * kc   # l'arc s'incrit donc dans un carré de coté 2*TT1
        # TT2 = -1              # gain sur moment affiché, saturé à 90° pour lisibilité, donc ici 10° d'arc = 10 rd/sec²
        # m_cdg=self.kart.moment_cdg
        # self.cnv.create_arc((abs2canvas(xcdg - TT1, ycdg - TT1, origx, origy), abs2canvas(xcdg + TT1, ycdg + TT1, origx, origy)),
        #                    outline="red", extent=min(max(-90, TT2 * m_cdg[2]), 90),
        #                    start=-180. * lacet / np.pi, fill='', width=3, style="arc")

        # trace des arcs donnant la vitesse lacet et l'acceleration lacet
        TT1 = 25 / 100 * kc
        TT2 = - 1.         # gain sur vitesse lacet affiché, saturé à 160° pour lisibilité, donc ici 12° d'arc = 12 deg/sec
        v_lacet_deg=self.kart.vitangul[0] * 180. / np.pi 
        if abs(v_lacet_deg) > 3. :
            extent=min(max(-160, TT2 * v_lacet_deg), 160)  # longeur de l'arc signée en degrés
            self.cnv.create_arc((abs2canvas(xcdg - TT1, ycdg - TT1, origx, origy), abs2canvas(xcdg + TT1, ycdg + TT1, origx, origy)),
                            outline="blue", extent=extent,start=-180. * lacet / np.pi, fill='', width=3, style="arc")

        TT1 = 20 / 100 * kc
        TT2 = -1        # gain sur accel_lacet affiché, saturé à 160° pour lisibilité, donc ici 12° d'arc = 12 deg/sec²
        a_lacet=self.kart.moment_cdg[2] / self.kart.inertie_lacet *180. / np.pi   # donc a_lacet en deg/sec²
        if abs(a_lacet) > 3. :
            extent=min(max(-160, TT2 * a_lacet), 160)  # longeur de l'arc signée en degrés
            self.cnv.create_arc((abs2canvas(xcdg - TT1, ycdg - TT1, origx, origy), abs2canvas(xcdg + TT1, ycdg + TT1, origx, origy)),
                           outline="red", extent=extent, start=-180. * lacet / np.pi, fill='', width=3, style="arc")


        # Affichage info dynamiques des roues
        self._trace_dyn_roues(kc, origx, origy, lacet)
        
        # affichage indicateurs gaz/frein, compte tour et vitesse, volant
        self._trace_indicators_gaz_frein()
        self._trace_compteur_vitesse()
        self._trace_volant()
    
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
        self.cnv.create_arc((200, 50), (270, 120), outline="cyan", extent=max(-240, -2 * V), start=210,
                           fill='', width=15, style="arc")
        self.cnv.create_text(233, 80, text=str(int(V)), font="Arial 18", fill="white")

    
    def _trace_volant(self):
        """Dessine le volant"""
        self.cnv.create_arc((100, 40), (170, 110), outline="grey", extent=359.9, start=0,
                           fill='', width=12, style="arc")
        self.cnv.create_arc((100, 40), (170, 110), outline="red", extent=12, 
                           start=int(85-2*self.volant),
                           fill='', width=12, style="arc")
        self.cnv.create_text(133, 75, text=str(int(self.volant)), font="Arial 18", fill="white")

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
 
    def _handle_stop(self):
        """Arrête l'enregistrement ; active REPLAY si la mémoire contient au moins un pas."""
        super()._handle_stop()
        if len(self.controls_recorded) > 0:
            self.btn_replay.config(state="normal")
        else:
            self.btn_replay.config(state="disabled")

    def read_commands(self):
        """Lit le fichier Records/commandes.txt et remplit controls_recorded + conditions_t0 (+ éventuels parametres) de replay."""
        path_cmd = RECORDS_DIR / "commandes.txt"
        try:
            with open(path_cmd, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Format JSON: contient les conditions initiales et les commandes sous la forme:
                # {"conditions_t0": {position, vitesse, angles, vitangul?, ...},
                #  "parametres": {h_cdg, ouverture, transm, pos_cdg?},
                #  "steps": [...]}
                # où un step est un dictionnaire: {"volant": x, "gaz": y, "frein": z}
                self.controls_recorded = data["steps"]
                self.cond_t0_recorded = data.get("conditions_t0", {})
                parametres = data.get("parametres")
                if isinstance(parametres, dict):
                    # Si des paramètres dynamiques sont fournis, on les applique via Kart.init_parametres
                    h_cdg = parametres.get("h_cdg", self.kart.h_cdg)
                    ouverture = parametres.get("ouverture", self.kart.ouverture)
                    transm = parametres.get("transm", self.kart.transm)
                    pos_cdg = parametres.get("pos_cdg")
                    self.kart.init_parametres(h_cdg=h_cdg, ouverture=ouverture, transm=transm, pos_cdg=pos_cdg)
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
    
    def update_telemetry(self, V, F_com, observations):
        """ Tous les calculs numériques sont faits ici, avant l'appel à show_telemetry de la classe User_Interface
        """
        idx, ecart_lat, v_lat, v_traj, curv, curv_N = observations
        f_cdg_vec = piste2vehicule(self.kart.force_cdg, self.kart.angles[0])
        norme_f_cdg = norme_vecteur(f_cdg_vec)

        # calcul du rayon de courbure de la trajectoire du kart à partir de la force appliquée au cdg
        radius = ( 1000000000.0 if norme_f_cdg < 0.00001 else self.kart.masse * V * V / norme_f_cdg)

        t_cyclemax_ms = int(self.t_cyclemax * 1000)
        t_framemax_ms = int(self.t_framemax * 1000)

        pos_x, pos_y, _ = self.kart.position
        vit_x, vit_y, _ = self.kart.vitesse
        lacet_deg = self.kart.angles[0] * 180.0 / np.pi
        v_lacet_deg = self.kart.vitangul[0] * 180.0 / np.pi
        V_kmh = V * 3.6    
        f_cdg_x, f_cdg_y, f_cdg_z = f_cdg_vec
        moment_cdg_z = self.kart.moment_cdg[2]
        varbre = self.kart.v_arbre
        
        self.show_telemetry_1(self.core.pas_simul, self.core.temps, t_cyclemax_ms, t_framemax_ms, F_com)

        self.show_telemetry_2(pos_x, pos_y, vit_x, vit_y, lacet_deg, v_lacet_deg, V, V_kmh, 
                             self.core.vold, idx, ecart_lat ,v_traj, curv, curv_N)
        self.show_telemetry_3(f_cdg_x, f_cdg_y, f_cdg_z, norme_f_cdg, moment_cdg_z, radius, varbre, 0.)    

    def _explore_combinations_gen(self) -> Iterator[Tuple[float, int, int, int]]:
        """Genérateur produisant les combinaisons demandées du tuple (cap, vit, volant, gaz) 
           en bouclant sur les ranges des états cochés pour appeler explore_state_step
           et enregister le résultat
        """
        # cap = angle entre la vitesse et l'axe x du Kart
        cap_values = list(range(-90, 90, 10)) if self.exp_cap.get() \
                                                  else [_safe_tk_var_float(self.forcage_cap)]

        # vit = vitesse du Kart en m/s
        vit_values = (0, 5, 10, 15, 20, 25, 30, 35, 40,45, 50) \
                               if self.exp_vit.get() else [_safe_tk_var_float(self.forcage_v)]

        # vol = angle entre le volant et l'axe x du Kart
        vol_values = list(range(-45, 50, 5)) if self.exp_vol.get() else [0]

        # gaz = commande frein ou gaz suivant le signe
        gaz_values = (-4, -3, -2, -1, 0, 10, 20, 30, 40, 50, 60, 70, 80) if self.exp_gaz.get() else [0]

        self.explore_values = {
            'cap': cap_values,
            'vit': vit_values,
            'vol': vol_values,
            'gaz': gaz_values,
        }

        for cap in cap_values:
            print (f"cap={cap}.....")
            cap_rad = float(np.radians(cap))
            for vit in vit_values:
                for vol in vol_values:
                    for gaz in gaz_values:

                        yield cap_rad, vit, vol, gaz

    def explore_states(self):
        """Actionné par le bouton EXPLORE de l'interface utilisateur, cette fonction va explorer tous les  
           états possibles demandés du Kart (avec les cases cochées) et va enregistrer les résultats
           dans un fichier lisible par Paraview
        """

        # Écriture en fin de parcours : Records/kart_explore_YYYYMMDD_HHMMSS_vit*.vtk + même préfixe .pvd (temps = vit)
        # et ``kart_explore_... .json`` (simu_controls, kart_parametres — pas dans les VTK).

        # Récupération des contrôles et paramètres de la simulation à partir de l'interface utilisateur
        simu_controls = {
            'regul': bool(self.regul.get()),
            'vold': getattr(self, 'Vold', 0.),
        }
        # Paramètres du kart (hauteur CdG, ouverture arrière, mode transmission) — lus sur l'UI
        kart_parametres = {
            'h_cdg': self.kart.empattement / 100. * self.H_cdg.get(),
            'ouverture': self.ouverture.get(),
            'transm': self.transm.get(),
            'pos_cdg': self.pos_cdg.get() / 100.,
        }
        self._explore_simu_controls = dict(simu_controls)
        self._explore_kart_parametres = dict(kart_parametres)
        self._explore_records = []
        self._explore_gen = self._explore_combinations_gen()
        self._explore_step(simu_controls, kart_parametres)

    def _explore_step(self, simu_controls, kart_parametres):
        """Une combinaison (cap, vit, vol, gaz) puis programmation de la suivante via after.
           J'ai mis en commentaire les lignes qui permettent de visualiser les changements d'état du kart
           dans l'interface utilisateur, il suffit de voir défiler les valeurs de cap dans la console.
           
           """

        # si on fait un RESET pendant l'exploration, on arrête et on revient en mode simulation.
        if not self.explore_status:
            self._explore_gen = None
            self._explore_records = []
            self.after(1, self.animation_step)
            return

        # sinon on continue l'exploration
        try:
            # si on épuise le générateur next, on partira vers except StopIteration:
            cap_rad, vit, vol, gaz = next(self._explore_gen)

            vitesse = np.array([vit * np.cos(cap_rad), vit * np.sin(cap_rad), 0.])
            self.kart.init_state(vitesse=vitesse)

            if gaz >= 0:
                self.gaz = gaz
                self.frein = 0
            else:
                self.frein = -gaz
                self.gaz = 0

            kart_controls = {'volant': float(vol),'gaz': self.gaz,'frein': self.frein}

            # Calcul de l'état du kart après application des contrôles
            state = self.core.step(0., kart_controls, simu_controls = simu_controls, kart_parametres = kart_parametres)

            self._explore_records.append({
                'cap_deg': float(np.degrees(cap_rad)),
                'vit': float(vit),
                'vol': float(vol),
                'gaz': float(gaz),
                'Fcdg_x': float(self.kart.force_cdg[0]),
                'Fcdg_y': float(self.kart.force_cdg[1]),
                'Moment_cdg_z': float(self.kart.moment_cdg[2]),
            })
            
            # Affichage
            #self.dessin_canvas(self.echelle_dyn.get())
            
            # Mise à jour télémesures
            #self.update_telemetry(state['V'], 0)      

            self.after(1, self._explore_step, simu_controls, kart_parametres)


        except StopIteration:
            self.explore_status = False
            # si on explorait les quatres dimensions, on sauvegarde dans un fichier vtk
            if self.exp_cap.get() and  self.exp_vit.get() and self.exp_vol.get() and self.exp_gaz.get():
                self._explore_write_paraview_vtk()
            elif self.exp_vol.get() and self.exp_gaz.get():
                # si on exploirait que deux dimensions, on va afficher la carte des états explorés
                self._explore_display_map()
            else:
                print("Aucune exploration demandée")

            self._explore_gen = None
            self._explore_records = []
            self.after(1, self.animation_step)

    def _explore_display_map(self):
        """Carte (vol, gaz) des états explorés : affiche un graphique matplolib 
        dans une nouvelle fenetre dont les données sont dans la liste self.explore_records. 
        Un élément de cette liste est un point coloré dans un plan 'volant'/'gaz'
        noir si la norme de Fcg inférieure à 80% du poid du kart, 
        sinon rouge si Moment_cdg est négatif, vert s'il est positif
        
        Chaque enregistrement contient les données suivantes:
        cap_deg: angle entre la vitesse et l'axe x du Kart
                'vit': float(vit),  
                'vol': float(vol),
                'gaz': float(gaz),
                'Fcdg_x': float(self.kart.force_cdg[0]),
                'Fcdg_y': float(self.kart.force_cdg[1]),
                'Moment_cdg_z': float(self.kart.moment_cdg[2]),
        """
        import matplotlib.pyplot as plt

        recs = getattr(self, "_explore_records", None) or []
        if not recs:
            return

        poids = float(self.kart.masse) * 9.81
        seuil_norme = 0.8 * poids

        xs, ys, colors = [], [], []
        fxs, fys, mzs = [], [], []
        for r in recs:
            fx = float(r["Fcdg_x"])
            fy = float(r["Fcdg_y"])
            norme_f = float(np.hypot(fx, fy))
            mz = float(r["Moment_cdg_z"])
            if norme_f < seuil_norme:
                c = "black"
            elif mz < 0.0:
                c = "red"
            else:
                c = "green"
            xs.append(float(r["vol"]))
            gaz = float(r["gaz"])
            gaz = 10.*gaz if gaz < 0 else gaz
            ys.append(gaz)
            colors.append(c)
            fxs.append(fx)
            fys.append(fy)
            mzs.append(mz)

        def _arctan_fy_over_fx_deg(fx_i: float, fy_i: float) -> float:
            if abs(fx_i) < 1e-15:
                if abs(fy_i) < 1e-15:
                    return float("nan")
                return 90.0 if fy_i > 0 else -90.0
            return float(np.degrees(np.arctan(fy_i / fx_i)))

        fig, ax = plt.subplots(figsize=(8, 6))
        sc = ax.scatter(xs, ys, c=colors, s=150, edgecolors="none", picker=True, pickradius=14)
        ax.set_xlabel("vol")
        ax.set_ylabel("gaz")
        ax.set_title("États explorés (noir : ‖Fcdg_xy‖ < 80 % du poids ; sinon rouge/vert selon Moment_cdg_z)")
        ax.grid(True, alpha=0.3)

        info = ax.text(
            0.02, 0.98, "",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.85),
        )

        def _explore_map_point_label(i: int) -> str:
            ang = _arctan_fy_over_fx_deg(fxs[i], fys[i])
            ang_s = f"{ang:.2f}°" if np.isfinite(ang) else "—"
            return f"Cap_F = {ang_s}\nMoment_Z = {mzs[i]:.6g}"

        def _on_explore_map_mouse(event):
            if event.inaxes != ax:
                info.set_text("")
                fig.canvas.draw_idle()
                return
            ok, props = sc.contains(event)
            if ok and len(props.get("ind", [])) > 0:
                idx = int(props["ind"][0])
                info.set_text(_explore_map_point_label(idx))
            else:
                info.set_text("")
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", _on_explore_map_mouse)
        fig.canvas.mpl_connect("button_press_event", _on_explore_map_mouse)

        fig.tight_layout()
        # Référence forte pour éviter la fermeture par le GC ; fenêtre indépendante, non bloquante pour Tk.
        self._explore_map_figure = fig
        plt.show(block=False)

    def _explore_write_paraview_vtk(self):
        """Écrit des VTK Legacy PolyData (ASCII) + un .pvd pour ParaView + un .json (même nom que le .pvd).

        Coordonnées 3D des points : (cap°, volant, gaz). La vitesse ``vit`` (m/s) est le pas temps
        de la collection : ouvrir le ``.pvd`` dans ParaView et utiliser la barre temporelle.

        Les paramètres utilisés pour la simulation enregistrés dans le .json sont:
        ``simu_controls`` et ``kart_parametres`` et les ranges "explore_values"
        """
        recs = getattr(self, '_explore_records', None) or []
        if not recs:
            return
        RECORDS_DIR.mkdir(parents=True, exist_ok=True)
        stem = f"kart_explore_{time.strftime('%Y%m%d_%H%M%S')}"
        simu = self._explore_simu_controls
        kp = self._explore_kart_parametres

        vit_values = sorted({float(r['vit']) for r in recs})

        def write_poly_subset(fpath: Path, subset: list) -> None:
            n = len(subset)
            vit_ts = float(subset[0]['vit']) if n else 0.0
            lines = [
                "# vtk DataFile Version 3.0",
                "Kart explore — axes cap, volant, gaz ; temps = vit (voir .pvd)",
                "ASCII",
                "DATASET POLYDATA",
                f"POINTS {n} float",
            ]
            for r in subset:
                lines.append(f"{r['cap_deg']} {r['vol']} {r['gaz']}")
            lines.append(f"VERTICES {n} {2 * n}")
            for i in range(n):
                lines.append(f"1 {i}")
            lines.append(f"POINT_DATA {n}")

            def add_scalar(name, values):
                lines.append(f"SCALARS {name} float 1")
                lines.append("LOOKUP_TABLE default")
                lines.extend(str(float(v)) for v in values)

            add_scalar("vitesse", (vit_ts,) * n)
            add_scalar("Fcdg_x", (r['Fcdg_x'] for r in subset))
            add_scalar("Fcdg_y", (r['Fcdg_y'] for r in subset))
            add_scalar("Moment_cdg_z", (r['Moment_cdg_z'] for r in subset))

            fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")

        vtk_basenames = []
        for vk in vit_values:
            subset = [r for r in recs if float(r['vit']) == vk]
            if not subset:
                continue
            vit_tag = str(int(vk)) if vk == int(vk) else str(vk).replace(".", "p")
            fname = f"{stem}_vit{vit_tag}.vtk"
            vtk_basenames.append((vk, fname))
            write_poly_subset(RECORDS_DIR / fname, subset)

        pvd_path = RECORDS_DIR / f"{stem}.pvd"
        pvd_lines = [
            '<?xml version="1.0"?>',
            '<VTKFile type="Collection" version="0.1" byte_order="LittleEndian">',
            "  <Collection>",
        ]
        for vk, fname in vtk_basenames:
            pvd_lines.append(f'    <DataSet timestep="{vk}" file="{fname}"/>')
        pvd_lines.extend(["  </Collection>", "</VTKFile>"])
        pvd_path.write_text("\n".join(pvd_lines) + "\n", encoding="utf-8")

        json_path = RECORDS_DIR / f"{stem}.json"
        explore_meta = {
            "simu_controls": {
                "regul": bool(simu.get("regul", False)),
                "vold": float(simu.get("vold", 0.)),
            },
            "kart_parametres": {
                "h_cdg": float(kp.get("h_cdg", 0.)),
                "ouverture": int(kp.get("ouverture", 0)),
                "transm": int(kp.get("transm", 0)),
                "pos_cdg": float(kp.get("pos_cdg", 0.)),
            },
            "explore_values": self.explore_values,
        }
        json_path.write_text(json.dumps(explore_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(f"Exploration enregistrée : ParaView {pvd_path} ; métadonnées {json_path}")

    def show_controls(self, kart_controls):
        """Affiche les commandes du kart définies par un mode non manuel dans l'UI"""
        self.volant = kart_controls['volant']
        self.gaz = kart_controls['gaz']
        self.frein = kart_controls['frein']

    def animation_step(self):
        """Effectue une étape d'animation (UI + core)
        Ne pas confondre une étape d'animation (L'affichage a lieu et se rafraichi, index N augmente
        Et une étape de simulation (le T simulation augmente de dt par pas))        
        """
        # si on lance le mode exploration des états du kart, on sort de cette boucle usuelle d'animation temps réel
        if self.explore_status:
            self.explore_states()
            return

        # début du cycle et on enregistre t0 pour le calcul ultérieur du temps de frame réel)
        t0_frame = time.time()  
        t_frame=0.

        # 1 - RECUPERATION DES CONTROLES DE SIMULATION ET PARAMETRES DU KART
        # contrôles de la simulation à partir de l'interface utilisateur
        simu_controls = {'regul': bool(self.regul.get()), 'vold': getattr(self, 'Vold', 0.),}
        # Paramètres du kart (hauteur CdG, ouverture arrière, mode transmission) — lus sur l'UI
        kart_parametres = { 'h_cdg': self.kart.empattement / 100. * self.H_cdg.get(),
                        'ouverture': self.ouverture.get(),
                           'transm': self.transm.get(),
                           'pos_cdg': self.pos_cdg.get() / 100., }
 
        # Écarts trajectoire (tuple attendu par Kart_control ; pas de trajectoire → zéros)
        if self.core.traj_cible is not None and len(self.core.traj_cible.fine_points) > 0:
            observations = self.core.get_observations()
        else:
            observations = (0, 0., 0., 0., 0., 0.)

        # 2 - CONSTRUCTION DU CONTROLE DU KART
        #  Si on est en mode replay, à partir de l'enregistrement
        if self.replay_status and self.core.pas_simul < len(self.controls_recorded):
            kart_controls = self.controls_recorded[self.core.pas_simul]
            self.show_controls(kart_controls)

        else:
            # sinon, lisons déjà les commandes demandées à partir de l'interface utilisateur
            if self.replay_status:
                # si on sort juste du mode replay par épuisement de controls_recorded, 
                # on arrête le replay et on met la simulation en pause
                self.replay_status = False
                self.simul_pause = True

            # Mode de contrôle demandé par l'utilisateur: Manuel ou agent de pilotage ?
            mode = int(self.commandes.get())
            manual_commands = {'volant': float(self.volant),'gaz': self.gaz,'frein': self.frein}

            if mode == Kart_control.MODE_MANUEL:
                # mode manuel: on applique directement les commandes demandées par l'utilisateur
                kart_controls = manual_commands
            elif mode == Kart_control.MODE_PROPORTIONNEL:
                # mode proportionnel: on applique les gains demandés dans l'UI
                self.kart_control.set_gains(self.ass_p1.get(), self.ass_p2.get(), self.ass_p3.get())
                kart_controls = self.kart_control.compute_controls(mode, manual_commands, observations)
                self.show_controls(kart_controls)
            else:
                kart_controls = self.kart_control.compute_controls(mode, manual_commands, observations)
                self.show_controls(kart_controls)

        # 3 - ENREGISTREMENT DES CONTROLES, FORCAGE VITESSE POSSIBLE EN PAUSE
        if not self.simul_pause:     
            # Enregistrement des oontroles si record on
            if self.record_status:
                self.controls_recorded.append(kart_controls)
                # F_com permet d'afficher le remplissage ou le vidage de la mémoire de commandes
                F_com=len(self.controls_recorded)
            elif self.replay_status:
                F_com=len(self.controls_recorded)-self.core.pas_simul
            else:
                F_com=0
        else:
            F_com=0
            # En pause, on peut forcer le vecteur vitesse si c'est demandé avec une vitesse non nulle
            forcage_v = _safe_tk_var_float(self.forcage_v)
            if forcage_v > 0.1:
                forcage_cap = _safe_tk_var_float(self.forcage_cap)
                cap_rad=np.radians(forcage_cap)
                vitesse = np.array([forcage_v * np.cos(cap_rad), forcage_v * np.sin(cap_rad), 0.])
                self.kart.init_state(position=self.kart.position, angles=self.kart.angles, vitesse=vitesse)

        # 4 - AVANCEMENT DE LA SIMULATION, NOUVEL ETAT DU KART
        # On avance de dt, mis à zero si la simulation est en pause
        dt = self.pas_de_temps.get() / 1000. if not self.simul_pause else 0.
        t0_cycle = time.time()

        # Evolution de l'état du kart par application des contrôles (dt=0 en pause)
        state = self.core.step(dt, kart_controls, simu_controls = simu_controls, kart_parametres = kart_parametres)
        V = state['V']

        if self.core.temps > 1.:
            t_cycle = time.time() - t0_cycle # temps du step physique uniquement 
            self.t_cyclemax = max(t_cycle, self.t_cyclemax)

        # 5 - MISE A JOUR DE L'AFFICHAGE 
        self.scale = self.cam_alt.get()
        self.update_camera_position(self.kart.position)
        self.dessin_canvas(self.echelle_dyn.get())
        self.update_telemetry(V, F_com, observations) 

        # 6 - PROGRAMMATION DE LA PROCHAINE ETAPE
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
