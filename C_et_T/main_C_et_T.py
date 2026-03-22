import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Doit être fait avant pyplot / backends pour un 2e lancement fiable dans le même terminal (Windows).
import matplotlib

matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.interpolate import splprep, splev
import json
import math
import time

# Import des nouvelles classes
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from C_et_T.C_et_T_classes.circuit_et_trajectoire import Circuit, Trajectoire, load_C_or_T__dialog
from C_et_T.C_et_T_classes.image_background import ImageBackgroundManager

class CircuitSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulateur de Circuit - Optimisation de Temps au Tour")
        self.root.geometry("1400x900")
        
        # Variables circuit - maintenant utilisant la classe Circuit
        self.circuit = Circuit("Circuit Principal", is_closed=True, width=10.0)
        
        # Variables trajectoire - maintenant utilisant la classe Trajectoire
        self.trajectory = Trajectoire("Trajectoire", is_closed=True)
        
        # Gestionnaire de fichiers: supprimé (sauvegarde/chargement via Circuit et Trajectoire)
        
        # Variables graphiques
        self.zoom_level = 1.0            # Niveau de zoom
        self.pan_x, self.pan_y = 0, 0   # Déplacement de la vue
        
        # Variables pour le drag and drop des points
        self.dragging_point = False
        self.dragged_point_index = None
        self.closest_raw = None
        self.closest_fine = None
        self.clicked_raw = None

        # Variables pour le déplacement de vue
        self.dragging_view = False
        self.drag_start = None
        self.drag_xlim = None
        self.drag_ylim = None
        
        # Variables pour le drag and drop des PDP
        self.dragging_pdp = False
        self.dragged_pdp_index = None
        
        # Variables pour l'image de fond
        self.image_manager = None  # Sera initialisé après setup_plot()
        self.view_width = 120.
        self.current_xlim = None
        self.current_ylim = None
        self.setup_ui()
        self.setup_plot()


        # Initialiser le gestionnaire d'image après la création de self.ax
        self.image_manager = ImageBackgroundManager(self.root, self.ax, self.info_label)

    def _reset_model_background_image(self):
        """Efface l'image modèle (nouveau circuit ou chargement d'un autre fichier). Hors saisie, l'image reste en mémoire pour réaffichage."""
        if self.image_manager:
            self.image_manager.reset_image()

    def load_background_image(self):
        """Wrapper pour charger l'image de fond"""
        if not self.circuit.input_mode:
            return
        if self.image_manager:
            success = self.image_manager.load_background_image()
            if success and self.image_manager.image_extent is not None:
                ext = self.image_manager.image_extent
                # Vue carrée englobant l'image (même échelle X/Y, cohérent avec zoom / aspect 1:1)
                x0, x1, y0, y1 = ext[0], ext[1], ext[2], ext[3]
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                half = max(abs(x1 - x0), abs(y1 - y0)) / 2
                self.current_xlim = (cx - half, cx + half)
                self.current_ylim = (cy - half, cy + half)
            if success:
                self.update_plot(False)
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame gauche pour les contrôles
        control_frame = ttk.LabelFrame(main_frame, text="Contrôles", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Contrôles du circuit
        circuit_frame = ttk.LabelFrame(control_frame, text="Circuit -----------------", padding=5)
        circuit_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(circuit_frame, text="Nouveau Circuit", command=self.new_circuit).pack(fill=tk.X, pady=2)
        self.circuit_input_button = ttk.Button(circuit_frame, text="Saisie Circuit", command=self.toggle_circuit_input)
        self.circuit_input_button.pack(fill=tk.X, pady=2)
        self.image_button = ttk.Button(
            circuit_frame, text="Charger Image Modèle", command=self.load_background_image, state="disabled"
        )
        self.image_button.pack(fill=tk.X, pady=2)
        ttk.Button(circuit_frame, text="Recentrer Vue", command=self.recenter_view).pack(fill=tk.X, pady=2)
        ttk.Button(circuit_frame, text="Charger Circuit", command=self.load_circuit).pack(fill=tk.X, pady=2)
        self.circuit_save_button=ttk.Button(circuit_frame, text="Sauvegarder Circuit", command=self.save_circuit)
        self.circuit_save_button.pack(fill=tk.X, pady=2)
        
        ttk.Label(circuit_frame, text="Largeur circuit (m):").pack(anchor=tk.W, pady=(10, 0))
        self.width_var = tk.DoubleVar(value=self.circuit.width)
        width_entry = ttk.Entry(circuit_frame, textvariable=self.width_var, width=10)
        width_entry.pack(fill=tk.X, pady=2)
        width_entry.bind('<Return>', lambda e: self.update_circuit_width())
        
        self.closed_var = tk.BooleanVar(value=self.circuit.is_closed)
        ttk.Checkbutton(circuit_frame, text="Circuit fermé", variable=self.closed_var, 
                       command=self.new_circuit).pack(anchor=tk.W, pady=2)
        self.circuit_info_label = ttk.Label(circuit_frame, text="", wraplength=200)
        self.circuit_info_label.pack(fill=tk.X, pady=2)
        
        # Contrôles de la trajectoire
        trajectory_frame = ttk.LabelFrame(control_frame, text="Trajectoire", padding=5)
        trajectory_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(trajectory_frame, text="Nouvelle Trajectoire", command=self.new_trajectory).pack(fill=tk.X, pady=2)
        self.pdp_input_button = ttk.Button(trajectory_frame, text="Saisie PDP", command=self.toggle_pdp_input)
        self.pdp_input_button.pack(fill=tk.X, pady=2)
        ttk.Button(trajectory_frame, text="Calculer Trajectoire", command=lambda: self.calculate_trajectory(stop=True)).pack(fill=tk.X, pady=2)
        ttk.Button(trajectory_frame, text="Optimiser Trajectoire", command=self.optimisation_method).pack(fill=tk.X, pady=2)
        ttk.Button(trajectory_frame, text="Charger Trajectoire", command=self.load_trajectory).pack(fill=tk.X, pady=2)
        self.traj_save_button= ttk.Button(trajectory_frame, text="Sauvegarder Trajectoire", command=self.save_trajectory)
        self.traj_save_button.pack(fill=tk.X, pady=2)
        ttk.Button(trajectory_frame, text="Create circuit test", command=self.def_circuit_test).pack(fill=tk.X, pady=2)

        self.trajectory_info_label = ttk.Label(trajectory_frame, text="", wraplength=200)
        self.trajectory_info_label.pack(fill=tk.X, pady=2)
        
        # Informations générales
        info_frame = ttk.LabelFrame(control_frame, text="Informations", padding=5)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.info_label = ttk.Label(info_frame, text="Prêt à créer un circuit", wraplength=200)
        self.info_label.pack(fill=tk.X, pady=2)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(control_frame, text="Instructions", padding=5)
        instructions_frame.pack(fill=tk.X)
        
        self.instructions_label = ttk.Label(instructions_frame, text="", wraplength=200, justify=tk.LEFT)
        self.instructions_label.pack(fill=tk.X, pady=2)
        
        # Frame droite pour le graphique
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas matplotlib
        self.fig, self.ax = plt.subplots(figsize=(12, 9))
        # Après plt.subplots(), ajustez les marges :
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        self.canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Bind des événements
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.get_tk_widget().bind('<KeyPress>', self.on_key_press)
        self.canvas.get_tk_widget().focus_set()
        
    def setup_plot(self):
        """Configure le graphique matplotlib"""
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_title('Simulateur de Circuit')
        
        # Limites par défaut
        self.setup_view()

    def setup_view(self):
        view_width = self.view_width
        half = view_width / 2
        # Même étendue en X et Y : échelle 1:1 (1 m horizontal = 1 m vertical à l'écran).
        self.current_xlim = (-half, half)
        self.current_ylim = (-half, half)
        self.ax.set_xlim(self.current_xlim)
        self.ax.set_ylim(self.current_ylim)
        self.ax.set_aspect("equal")

        
    def on_scroll(self, event):
        """Gère le zoom avec la molette de la souris"""
        if event.inaxes != self.ax:
            return

        xdata = event.xdata
        ydata = event.ydata
        
        if event.button == 'up':
            scale_factor = 0.9
        elif event.button == 'down':
            scale_factor = 1.1
        else:
            scale_factor = 1
            
        x_span = self.current_xlim[1] - self.current_xlim[0]
        y_span = self.current_ylim[1] - self.current_ylim[0]
        if x_span <= 0 or y_span <= 0:
            return
        span = max(x_span, y_span) * scale_factor

        relx = (self.current_xlim[1] - xdata) / x_span
        rely = (self.current_ylim[1] - ydata) / y_span

        self.current_xlim = [xdata - span * (1 - relx), xdata + span * relx]
        self.current_ylim = [ydata - span * (1 - rely), ydata + span * rely]
        self.ax.set_xlim(self.current_xlim)
        self.ax.set_ylim(self.current_ylim)
        self.ax.set_aspect("equal")
        
        self.canvas.draw()
        
    def on_key_press(self, event):
        """Gère les touches du clavier"""
        if event.char == 'r':
            self.recenter_view()
        elif event.char == 'c':
            self.new_circuit()
        elif event.char == 't':
            self.new_trajectory()
        elif event.char == 'o':
            self.load_circuit()
        elif event.char == 's':
            self.save_circuit()
        elif event.char == 'Escape':
            self.update_plot()
            
    def update_closest_points(self, event):
        """ mise à jour des points grossier et fin les plus proche du point courant"""
        # on détermine le point cliqué ou le plus proche de ce qu'on est en train de saisir, circuit ou trajectoire
        x, y = event.xdata, event.ydata
        self.closest_raw, self.closest_fine, self.clicked_raw = None, None, None
        if self.circuit.input_mode and self.trajectory.input_mode: raise RuntimeError("Problème !! Deux saisies actives")
        if self.circuit.input_mode:
            self.closest_raw=self.circuit.closest_raw_point(x, y, threshold=1000)
            self.clicked_raw = self.circuit.closest_raw_point(x, y, threshold=1)
        elif self.trajectory.input_mode:
            self.closest_raw = self.trajectory.closest_raw_point(x, y, threshold=1000)
            self.clicked_raw = self.trajectory.closest_raw_point(x, y, threshold=1)
        else:
            self.closest_fine = self.trajectory.closest_fine_point(x, y, threshold=10)
        
    def on_press(self, event):
        """Gère le clic de souris"""
        if event.inaxes != self.ax:
            return
        # on détermine le point cliqué ou le plus proche de ce qu'on est en train de saisir, circuit ou trajectoire
        x, y = event.xdata, event.ydata
        self.update_closest_points(event)
        
        if event.button == 1:  # Clic gauche
            if self.circuit.input_mode:  # Si on est en mode saisie circuit
                if self.clicked_raw is not None:    # si on clique sur un point grossier existant du circuit, on peut le deplacer
                    self.dragging_point = True
                    self.dragged_point_index = self.clicked_raw
                elif self.closest_raw is not None or len(self.circuit.raw_points)==0:
                      # sinon, on ajoute un point après le plus proche
                    self.add_raw_point(x, y, self.closest_raw)
                    self.update_closest_points(event)
            elif self.trajectory.input_mode:  # Si on est en mode saisie trajectoire
                # Mode normal - vérifier si on clique sur un PDP
                if self.clicked_raw is not None:       # si on clique sur un PDP de la trajectoire, on peut le deplacer
                    self.dragging_point = True
                    self.dragged_point_index = self.clicked_raw
                else:                         # si on clique sur un point quelconque = ajout de point PDP
                    self.add_raw_point(x, y, self.closest_raw)
                    self.update_closest_points(event)
            else:       
                if self.closest_fine is not None:   # si on clique sur un point de trajectoire fine, on affiche ses infos
                    self.update_trajectory_info(self.closest_fine)
                else:                      # si on clique sur un point quelconque = deplacement de la vue
                    self.dragging_view = True
                    self.drag_start = (x,y)
                    self.drag_xlim = self.current_xlim
                    self.drag_ylim = self.current_ylim
        elif event.button == 2:  # Clic milieu - déplacement de vue
            self.dragging_view = True
            self.drag_start = (x,y)
            self.drag_xlim = self.current_xlim
            self.drag_ylim = self.current_ylim
        elif event.button == 3:  
            # En mode saisie circuit ou trajectoire, clic droit = supprimer le point grossier le plus proche
            if (self.circuit.input_mode or self.trajectory.input_mode) and self.closest_raw is not None:
                self.remove_raw_point(self.closest_raw)
                self.update_closest_points(event)
        self.update_plot()
        return
            
    def on_motion(self, event):
        """Gère le mouvement de la souris"""
        if event.inaxes != self.ax:
            return
        x, y = event.xdata, event.ydata
        if self.dragging_point and self.dragged_point_index is not None:
            # Déplacement en cours d'un point du circuit ou de la trajectoire
            if self.circuit.input_mode:
                self.circuit.raw_points[self.dragged_point_index] = [x, y]

            elif self.trajectory.input_mode:
                if self.circuit.is_point_inside(x, y):
                    self.trajectory.raw_points[self.dragged_point_index] = [x, y]
                self.update_plot(True)
            else:
                Warning("Erreur Bizarre inattendue dans on_motion")
            self.update_plot(True)    
        elif self.dragging_view and self.drag_start is not None:
            # Déplacement en cours de la vue
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.current_xlim = (self.drag_xlim[0] - dx, self.drag_xlim[1] - dx)
            self.current_ylim = (self.drag_ylim[0] - dy, self.drag_ylim[1] - dy)
            self.ax.set_xlim(self.current_xlim)
            self.ax.set_ylim(self.current_ylim)
            self.ax.set_aspect("equal")
            #self.update_plot(True)   
            self.canvas.draw_idle()  
        elif self.circuit.input_mode:
            # Mettre à jour la couleur du point de saisie le plus proche
            self.closest_raw = self.circuit.closest_raw_point(x, y, threshold=1000)
            self.update_plot(True)  
        elif self.trajectory.input_mode:
            # Mettre à jour la couleur du point de saisie le plus proche
            self.closest_raw = self.trajectory.closest_raw_point(x, y, threshold=1000)
            self.update_plot(True)   
        elif not(self.dragging_point) and not(self.dragging_view) and \
             x is not None and y is not None and not self.circuit.input_mode and len(self.trajectory.fine_points) > 0:
            traj_idx = self.trajectory.closest_fine_point(x, y , threshold=10)
            if traj_idx is not None:   # si on passe sur un point de trajectoire fine, on affiche ses infos
                self.update_trajectory_info(traj_idx)
        else:
            Warning("Erreur inattendue dans on_motion")

        return
            
    def on_release(self, event):
        """Gère le relâchement de la souris"""
        if event.button == 1:  # Clic gauche
            if self.dragging_point:
                self.dragging_point = False
                self.dragged_point_index = None
                # Recalculer le circuit fin si possible
                if self.circuit.is_ready_for_calculation():
                    self.calculate_circuit_fin(False)
                # Recalculer la trajectoire si possible
                if self.trajectory.is_ready_for_calculation():
                    self.calculate_trajectory(False)
            elif self.dragging_view:
                self.dragging_view = False
                self.drag_start = None
                self.drag_xlim = None
                self.drag_ylim = None
                    
        elif event.button == 2:  # Clic milieu
            self.dragging_view = False
            self.drag_start = None
            self.drag_xlim = None
            self.drag_ylim = None
        self.update_plot()   

    def def_circuit_test(self):
        """Crée un circuit test"""
        for i in range(0, 20):
            teta = i*2*np.pi/20
            self.circuit.raw_points.append([50*np.cos(teta), 50*np.sin(teta)])
        self.circuit.calculate_fine_profile()
        self.circuit.calculate_parameters()
        self.circuit.calculate_borders()
        self.update_plot()
        self.circuit_info_label.config(text=f"Circuit test créé: {len(self.circuit.raw_points)} points")

    def update_trajectory_info(self, idx):
        """Met à jour les informations de trajectoire pour le point idx"""
    
        info = f"Point n° {idx}: "
        try:
            # Vitesse
            v = self.trajectory.velocities[idx]
            info += f"Vitesse: {v*3.6:.0f} km/h, "
                
            # Paramètre de position
            # param = self.trajectory.ecarts[idx]
            # info += f"Ecart: {param:.2f}, "
                
            # Courbure
            curv = self.trajectory.curvatures[idx]
            if curv != 0:
                info += f"\nRayon: {1/curv:.2f}m"
            else:
                info += f"\nRayon: infini"
        except Exception as e:
            info += f"\nErreur: {e}"
        self.info_label.config(text=info)
        
    def new_trajectory(self):
        """Crée une nouvelle trajectoire"""
        self.trajectory = Trajectoire("Trajectoire", is_closed=self.circuit.is_closed)
        self.circuit.stop_input()
        self.trajectory.start_input()
        self.trajectory.reset_raw_points()
        self.update_plot()
            
    def add_raw_point(self, x, y, idx):
        """Ajoute un point grossier au profil en cours de saisie, circuit ou trajectoire"""

        if self.circuit.input_mode:
            self.circuit.insert_point(x, y, idx)
            if self.circuit.is_ready_for_calculation():
                self.calculate_circuit_fin(False)
            else:
                self.update_plot(False)
                self.circuit_info_label.config(text=f"Point ajouté. Circuit: {len(self.circuit.raw_points)} points")
    
        elif self.trajectory.input_mode:
            if self.circuit.is_point_inside(x, y, add=True):
                self.trajectory.insert_point(x,y,idx)
                self.calculate_trajectory(motion=False, stop=False)
                self.update_plot(False)
                self.trajectory_info_label.config(text=f"PDP ajouté. Trajectoire: {len(self.trajectory.raw_points)} points")
            else:
                self.trajectory_info_label.config(text=f"Point hors circuit")

    def remove_raw_point(self, idx):
        """Supprime le point grossier idx du circuit ou de la trajectoire"""
        if self.circuit.input_mode:
            if self.circuit.remove_point(idx):  # Appel de la méthode métier
                if self.circuit.is_ready_for_calculation():
                    self.calculate_circuit_fin(False)
                if self.circuit.input_mode:
                    self.circuit_info_label.config(text=f"Point supprimé. Circuit: {len(self.circuit.raw_points)} points")
            else:
                self.circuit_info_label.config(text="Impossible de supprimer le point (circuit verrouillé)")
        elif self.trajectory.input_mode:
            if self.trajectory.remove_point(idx):  # Appel de la méthode métier
                if self.trajectory.is_ready_for_calculation():
                    self.calculate_trajectory(motion=False, stop=False)
                self.trajectory_info_label.config(text=f"PDP supprimé. Trajectoire: {len(self.trajectory.raw_points)} points")
            else:
                self.trajectory_info_label.config(text="Impossible de supprimer le PDP (trajectoire verrouillée)")
        else:
            RuntimeError("Erreur inattendue dans remove_raw_point")        
            
    def calculate_circuit_fin(self, motion=False, warning=False, stop=False):
        """Calcule et affiche le circuit fin, rapidement si motion=True"""
        if not self.circuit.is_ready_for_calculation():
            if warning: messagebox.showerror("Erreur", "Il faut au moins 3 points pour créer un circuit")
            return

        self.circuit.calculate_fine_profile()
        self.circuit.calculate_parameters()
        # Désactiver le mode saisie circuit après calcul
        if stop:
            self.circuit.stop_input()
        self.update_plot(motion)
        self.circuit_info_label.config(text=f"Circuit fin calculé: {len(self.circuit.fine_points)} points, "
                                    f"Longueur: {self.circuit.length:.1f}m")

    def calculate_trajectory(self, motion=False, warning=False, stop=False):
        """Calcule et affiche la trajectoire, rapidement si motion=True"""
        if warning:
            """Demande utilisateur de calcul de la trajectoire"""
            if len(self.circuit.fine_points) == 0:
                messagebox.showerror("Erreur", "Créez d'abord un circuit fin")
                return
            elif not self.trajectory.is_ready_for_calculation():
                messagebox.showerror("Erreur", "Il faut plus de points de passage")
                return
        elif self.trajectory.is_ready_for_calculation():
            if stop: self.trajectory.stop_input()
            self.trajectory.calculate_fine_profile()
            self.trajectory.calculate_parameters()

            # Mettre à jour l'état des boutons après le calcul (trajectoire verrouillée)
            self.update_plot(motion)
        else:
            RuntimeError("Erreur inattendue dans calculate_trajectory")
            
    def recenter_view(self):
        """Recentrer la vue sur le circuit"""
        if not self.circuit.raw_points:
            self.setup_view()
        else:
            points = np.array(self.circuit.raw_points)
            x_min, x_max = points[:, 0].min(), points[:, 0].max()
            y_min, y_max = points[:, 1].min(), points[:, 1].max()
            
            # Ajouter une marge ; fenêtre carrée en données pour aspect 1:1
            margin = min(max(x_max - x_min, y_max - y_min) * 0.2, 10)
            cx = (x_min + x_max) / 2
            cy = (y_min + y_max) / 2
            half_wx = (x_max - x_min) / 2 + margin
            half_wy = (y_max - y_min) / 2 + margin
            half = max(half_wx, half_wy)
            self.current_xlim = (cx - half, cx + half)
            self.current_ylim = (cy - half, cy + half)
            self.ax.set_xlim(self.current_xlim)
            self.ax.set_ylim(self.current_ylim)
            self.ax.set_aspect("equal")

        self.canvas.draw()
        
    def update_circuit_width(self):
        """Met à jour la largeur du circuit"""
        new_width = self.width_var.get()
        if new_width > 0:
            self.circuit.set_width(new_width)
            if self.circuit.is_ready_for_calculation():
                self.calculate_circuit_fin(False)
            self.circuit_info_label.config(text=f"Largeur du circuit mise à jour: {new_width}m")
        else:
            messagebox.showerror("Erreur", "La largeur doit être positive")

    def new_circuit(self):
        """Crée un nouveau circuit"""
        self._reset_model_background_image()
        self.circuit = Circuit("Circuit Principal", is_closed=True, width=self.width_var.get())
        self.circuit.is_closed = self.closed_var.get()
        self.trajectory = Trajectoire("Trajectoire", is_closed=self.circuit.is_closed)  # Nouvelle trajectoire
        self.setup_view()
        self.update_plot(False)
        self.circuit_info_label.config(text="Nouveau circuit créé")
        
    def save_circuit(self):
        """Sauvegarde le circuit (Circuit dialog JSON/CSV)."""
        if self.circuit.input_mode:
            messagebox.showerror("Erreur", "Le circuit est en mode saisie")
            return
        if self.circuit.save_circuit_dialog():
            self.circuit_info_label.config(text=f"Circuit sauvegardé")

    def save_trajectory(self):
        """Sauvegarde la trajectoire (Trajectoire dialog JSON/CSV)."""
        if self.trajectory.save_trajectory_dialog():
            self.trajectory_info_label.config(text=f"Trajectoire sauvegardée")
                
    def load_trajectory(self):
        """Charge la trajectoire (dialogue commun circuit / trajectoire)."""
        loaded = load_C_or_T__dialog()
        if loaded is None:
            return
        if isinstance(loaded, Trajectoire):
            self.trajectory = loaded
            self.update_plot(False)
            self.trajectory_info_label.config(text="Trajectoire chargée")
        else:
            messagebox.showerror(
                "Erreur",
                "Le fichier choisi est un circuit. Chargez une trajectoire (JSON avec 'traj_data').",
            )

    def load_circuit(self):
        """Charge un circuit (dialogue commun circuit / trajectoire)."""
        loaded = load_C_or_T__dialog()
        if loaded is None:
            return
        if isinstance(loaded, Circuit):
            self._reset_model_background_image()
            self.circuit = loaded
            self.width_var.set(self.circuit.width)
            self.closed_var.set(self.circuit.is_closed)
            self.trajectory.reset_fine_profile()
            self.update_plot(False)
            self.circuit_info_label.config(text="Circuit chargé")
        else:
            messagebox.showerror(
                "Erreur",
                "Le fichier choisi est une trajectoire. Chargez un circuit (JSON avec 'circuit_data' ou CSV).",
            )

    def toggle_circuit_input(self):
        """Bascule le mode saisie circuit"""
        if self.circuit.input_mode: # ON arrête la saisie du circuit
            self.circuit.stop_input()
            if self.circuit.is_ready_for_calculation():
                self.calculate_circuit_fin(False)
            self.info_label.config(text="Mode saisie circuit désactivé")
        else: # On démarre la saisie du circuit, donc on vide la trajectoire
            self.circuit.start_input()
            self.trajectory.reset_raw_points(True)
            if self.circuit.is_ready_for_calculation():
                self.calculate_circuit_fin(False)
            self.info_label.config(text="Mode saisie circuit activé. Cliquez pour ajouter des points")
        self.update_instructions_and_buttons()
        
    def toggle_pdp_input(self):
        """Bascule le mode saisie trajectoire"""
        if len(self.circuit.fine_points) == 0:
            messagebox.showerror("Erreur", "Créez d'abord un circuit fin")
            return

        if self.trajectory.input_mode:   # ON arrête la saisie de la trajectoire
            self.trajectory.stop_input()
            if self.trajectory.is_ready_for_calculation():
                self.calculate_trajectory(motion=False, stop=True)
            self.info_label.config(text="Mode saisie PDP désactivé")
        else:                            # On démarre ou redemarre la saisie de la trajectoire
            self.circuit.stop_input()
            self.trajectory.start_input()
            # if self.trajectory.is_ready_for_calculation():
            #     self.calculate_trajectory(motion=False, stop=True)
            self.info_label.config(text="Mode saisie PDP activé. Cliquez pour ajouter des points de passage")
        self.update_plot()
        
    def update_instructions_and_buttons(self):
        """Met à jour les instructions et l'état des boutons"""
        if self.trajectory.is_ready_for_calculation():
            self.trajectory_info_label.config(text=f"Trajectoire calculée: {len(self.trajectory.fine_points)} points "
                                      f"\nLongueur:    : {self.trajectory.length:.2f} m"
                                      f"\nType d'optimisation: {self.trajectory.optimization_type}"
                                      f"\nTemps au tour: {self.trajectory.lap_time:.2f} s")
        if self.circuit.input_mode:
            self.circuit_save_button.config(state='disabled')
            self.image_button.config(state='normal')
            self.circuit_input_button.config(text="Arrêter Saisie Circuit")
            if not self.circuit.is_ready_for_calculation():
                self.circuit_input_button.config(state='disabled')
            else:
                self.circuit_input_button.config(state='normal')
            self.instructions_label.config(text="Cliquez pour ajouter des points au circuit.\n"
                                                "Clic droit pour effacer le dernier point.\n"
                                                "Echap pour annuler.")
        else:
            self.image_button.config(state='disabled')
            self.circuit_input_button.config(text="Saisie Circuit")
            self.circuit_save_button.config(state='normal')
            self.info_label.config(text=f"RIEN A DIRE")
            if self.trajectory.input_mode:
                self.circuit_input_button.config(state='disabled')
            else:
                self.circuit_input_button.config(state='normal')
            self.instructions_label.config(text="Circuit verrouillé. Cliquez pour déverrouiller.")

        if self.trajectory.input_mode:
            self.traj_save_button.config(state='disabled')
            self.pdp_input_button.config(text="Arrêter Saisie PDP")
            self.instructions_label.config(text="Cliquez pour ajouter des points de passage.\n"
                                               "Clic droit pour effacer le dernier point.\n"
                                               "Echap pour annuler.")
        else:
            self.pdp_input_button.config(text="Saisie PDP")
            self.traj_save_button.config(state='normal')
            if self.circuit.input_mode:
                self.pdp_input_button.config(state='disabled')
            else:
                self.pdp_input_button.config(state='normal')
            self.instructions_label.config(text="Trajectoire verrouillée. Cliquez pour déverrouiller.")
            
    def optimisation_method(self):
        """Selection du type d'optimisation de a trajectoire"""
        if len(self.circuit.fine_points) == 0:
            messagebox.showerror("Erreur", "Créez d'abord un circuit fin")
            return
        
        # Créer une fenêtre de dialogue pour choisir le type d'optimisation
        dialog = tk.Toplevel(self.root)
        dialog.title("Choix du type d'optimisation")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        
        # Centrer la fenêtre
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = ttk.Label(main_frame, text="Choisissez le type d'optimisation :", 
                               font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Variable pour stocker le choix
        optimization_type = tk.IntVar(value=self.trajectory.optimization_type)
        
        # Types d'optimisation disponibles
        optimization_types = [
            ("Optimisation 1 - Vmax = sqrt (g / R)", 1),
            ("Optimisation 2 - plus limitation 1g", 2),
            ("Optimisation 3 - plus limitation 120 ch", 3), 
            ("Optimisation 4 - plus limitation 80 ch", 4),   
            ("Optimisation 5 - plus limitation 40 ch", 5), 

        ]
        
        # Créer les boutons radio
        for text, value in optimization_types:
            radio_button = ttk.Radiobutton(main_frame, text=text, variable=optimization_type, 
                                         value=value)
            radio_button.pack(anchor=tk.W, pady=5)
        
        # Frame pour les boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Bouton Annuler
        cancel_button = ttk.Button(button_frame, text="Annuler", 
                                 command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Bouton Valider
        def validate_choice():
            self.trajectory.optimization_type = optimization_type.get()
            dialog.destroy()
            self.trajectory.calculate_parameters()
        
        validate_button = ttk.Button(button_frame, text="Valider", 
                                   command=validate_choice)
        validate_button.pack(side=tk.RIGHT)
        
        # Focus sur le bouton Valider
        validate_button.focus_set()
        
        # Bind Enter pour valider
        dialog.bind('<Return>', lambda e: validate_choice())
        
        # Attendre que la fenêtre soit fermée
        dialog.wait_window()
        
        # Mettre à jour le graphique et les informations après optimisation
        self.update_plot(False)
            
    def update_plot(self, motion=False):
        """Met à jour le graphique, de manière allégée si motion=True"""
        static = not motion

        self.update_instructions_and_buttons()
        self.ax.clear()
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_title('Simulateur de Circuit')
        self.ax.set_xlim(self.current_xlim)
        self.ax.set_ylim(self.current_ylim)
        
        # Image modèle géoréférencée (mode saisie circuit uniquement)
        self.image_manager.display_background_image(self.circuit.input_mode)
        
        # Afficher le circuit grossier (polygone et points) quand on est en mode saisie circuit
        if self.circuit.raw_points and self.circuit.input_mode:
            points = np.array(self.circuit.raw_points)
            if self.circuit.is_closed and len(points) >= 3:
                points = np.vstack([points, points[0]])
            self.ax.plot(points[:, 0], points[:, 1], 'k--', alpha=0.5)

            # Colorer différemment selon si le circuit est prêt ou pas
            (color, size) = ('green', 50) if self.circuit.is_ready_for_calculation() else ('red', 50)
            self.ax.scatter(points[:, 0], points[:, 1], c=color, s=size, zorder=5)
            if self.closest_raw is not None : # colorer le point le plus proche du clic
                self.ax.scatter(points[self.closest_raw, 0], points[self.closest_raw, 1], c='blue', s=size, zorder=5)
            
            # Afficher les numéros des points grossiers
            if len(points) > 0:
                nbpt = len(points) if len(points) <3 else len(points) -1 # pour circuit fermé en fait,  A FAIRE
                for i in range(nbpt):
                    self.ax.text(points[i,0]+1, points[i,1]+1, f'{i+1}', fontsize=10, weight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
        # Afficher le circuit fin
        if len(self.circuit.fine_points) > 0:
            points = np.array(self.circuit.fine_points)
            if self.circuit.is_closed : points = np.vstack([points, points[0]])
            # Centre du circuit
            self.ax.plot(points[:, 0], points[:, 1], 'b:', linewidth=0.5)
            
            # Bords gauche et droit
            if self.circuit.left_border:
                left_border = np.array(self.circuit.left_border)
                if self.circuit.is_closed : left_border = np.vstack([left_border, left_border[0]])
                self.ax.plot(left_border[:, 0], left_border[:, 1], 'r-', linewidth=1)
                           
            if self.circuit.right_border:
                right_border = np.array(self.circuit.right_border)
                if self.circuit.is_closed : right_border = np.vstack([right_border, right_border[0]])
                self.ax.plot(right_border[:, 0], right_border[:, 1], 'g-', linewidth=1)
                           
        # Afficher la trajectoire grossière = es points de passage
        if self.trajectory.raw_points and self.trajectory.input_mode:
            pdp_points = np.array(self.trajectory.raw_points)
            self.ax.scatter(pdp_points[:, 0], pdp_points[:, 1], c='orange', s=100, marker='s', zorder=6)
            if self.closest_raw is not None:    # colorer le point le plus proche du clic
                if self.closest_raw >= len(pdp_points): print(f"Debug: closest_raw = {self.closest_raw} >= len(pdp_points) = {len(pdp_points)}") 
                self.ax.scatter(pdp_points[self.closest_raw, 0], pdp_points[self.closest_raw, 1], 
                          c='blue', s=100, marker='s', zorder=6)        
                     
            # Afficher les numéros des points grossiers
            if len(pdp_points) > 0:
                nbpt = len(pdp_points) # if len(pdp_points) <3 else len(pdp_points) -1 # pour circuit fermé en fait,  A FAIRE
                for i in range(nbpt):
                    self.ax.text(pdp_points[i,0]+1, pdp_points[i,1]+1, f'{i+1}', fontsize=10, weight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))   

        # Afficher la trajectoire s'il y en a une (en cours de saisie ou calculée)
        if len(self.trajectory.fine_points) > 0:
            traj_points = np.array(self.trajectory.fine_points)
            if self.trajectory.is_closed : 
                traj_points_ext = np.vstack([traj_points, traj_points[0]])
            else:
                traj_points_ext = traj_points
            self.ax.plot(traj_points_ext[:, 0], traj_points_ext[:, 1], 'b-', linewidth=1)
            # Affiche les points de trajectoires colorés selon la vitesse, plus quelques vitesses
            if static and len(self.trajectory.velocities) > 0:
                # Mapping des types d'accélération vers les couleurs
                color_map = {
                    0: 'blue',    # Vitesse constante
                    1: 'brown',   # Accélération limitée par adhérence (=patinage)
                    2: 'green',   # Accélération limitée par puissance (=grip)
                    3: 'grey',    # Levée de pied
                    4: 'red'      # Freinage
                }
                colors = [color_map.get(v) for v in self.trajectory.type_accel]  
                        
                self.ax.scatter(traj_points[:, 0], traj_points[:, 1], c=colors, s=30, zorder=7)
                
                # Afficher quelques vitesses maximales
                step = max(1, len(traj_points) // 10)
                for i in range(0, len(traj_points), step):
                    if i < len(self.trajectory.velocities):
                        v_kmh = self.trajectory.velocities[i] * 3.6
                        self.ax.annotate(f'{v_kmh:.0f} km/h', (traj_points[i, 0], traj_points[i, 1]),
                                       xytext=(5, 5), textcoords='offset points', fontsize=8, alpha=0.8)
                      
        # Ne jamais changer automatiquement les limites - seulement les restaurer si elles existent
        self.ax.set_xlim(self.current_xlim)
        self.ax.set_ylim(self.current_ylim)
        self.ax.set_aspect("equal")

        self.canvas.draw()


def main():
    root = tk.Tk()
    app = CircuitSimulator(root)

    def on_closing():
        # Libère Matplotlib avant de détruire le canvas Tk (évite état backend / Tcl bloqué au prochain run).
        try:
            plt.close("all")
        except Exception:
            pass
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    try:
        root.mainloop()
    finally:
        try:
            plt.close("all")
        except Exception:
            pass


if __name__ == "__main__":
    main()
