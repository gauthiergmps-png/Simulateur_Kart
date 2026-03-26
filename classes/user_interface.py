import tkinter as tk
from abc import abstractmethod
import numpy as np
from tkinter import (Tk, Canvas, Frame, Button, LEFT, RIGHT, TOP, BOTTOM, 
                     CENTER, HORIZONTAL, VERTICAL, ARC, LAST, Label, Scale,
                     Checkbutton, Radiobutton, IntVar, StringVar, W, N, S, Entry,
                     Spinbox)

from classes.kart_control import Kart_control

class User_Interface:
    """Classe gérant l'interface utilisateur Tkinter du simulateur de kart
       A noter que cette classe ne connait pas encore le Kart, qui sera instancié
       dans la classe SimulationUI qui est une classe qui hérite ce celle-ci
       
       Donc l'idée est de mettre ici tout ce qui ne dépend pas du Kart
       
       """
    
    def __init__(self):
        """         Initialise l'interface utilisateur"""
        
        # Variables d'état de l'interface
        self.fenetre = None
        self.cnv = None
        self.telemesure1 = None
        self.telemesure2 = None
        self.telemesure3 = None
        
        # Variables de contrôle
        self.pas_de_temps = None
        self.echelle_dyn = None
        self.H_cdg = None
        self.ouverture = None
        
        # Variables d'état (initialisées après création de la fenêtre)
        self.commandes = None
        self.command_radiobuttons = []
        self.circuit = 0
        self.regul = None
        self.transm = None
        
        # Variables de simulation
        self.F_com = []
        self.t_cyclemax = 0.
        self.simul_pause=True

        # variable d'enregistrement et de replay
        self.record_status = False
        self.replay_status = False

        # Mode d'exploration des états possibles
        self.explore_status = False
        # exp_cap / exp_vit / exp_vol / exp_gaz : IntVar créés dans _create_control_panel (cases EXPLORE)
        
        # Variables de caméra
        self.xcam = 0.
        self.ycam = 0.
        self.cam_alt0 = 100
        self.cam_speed0 = 5
        self.cam_speedmax = 20
        
        # Variables d'affichage
        self.hist_xcdg = []
        self.hist_ycdg = []
        self.coul_chassis = 4
        
        self._create_main_window()
        self._create_control_panel()
        self._create_canvas()
        self._setup_key_bindings()
    
    def _create_main_window(self):
        """Crée la fenêtre principale"""
        self.fenetre = Tk()
        self.fenetre.title("Simulateur Sprint Car by Laurent Gauthier - V1.2")
        self.fenetre.protocol("WM_DELETE_WINDOW", self._quit_application)

    def _quit_application(self):
        """Sort proprement de mainloop() puis détruit la fenêtre (nécessaire sur Windows)."""
        self.fenetre.quit()
        self.fenetre.destroy()
    
    def _create_control_panel(self):
        """Crée le panneau de contrôle avec tous les widgets"""
        # Initialisation des variables Tkinter après création de la fenêtre
        self.commandes = IntVar()
        self.circuit = IntVar()
        self.regul = IntVar()
        self.transm = IntVar()
        self.exp_cap = IntVar(value=0)
        self.exp_vit = IntVar(value=0)
        self.exp_vol = IntVar(value=0)
        self.exp_gaz = IntVar(value=0)
        self.forcage_cap=IntVar(value=0)
        
        # Bandeau principal
        bandeau = Frame(self.fenetre, width=1800, height=100, highlightbackground="red", highlightthickness=2)
        bandeau.pack()
        
        # Création des frames
        frames = {}
        frame_names = ['frameB', 'frameA', 'frame0', 'frame1', 'frame2B', 'frame2', 
                      'frame3', 'frame4', 'frame5', 'frame6', 'frame7', 'frame8']
        
        for i, name in enumerate(frame_names):
            frames[name] = Frame(bandeau, width=200, height=100, 
                               highlightbackground="black", highlightthickness=1)
            frames[name].pack(side=LEFT)
        
        # Frame B - Tabulation des états possibles
        self._create_explore_states_frame(frames['frameB'])
        
        
        # Frame A - Contrôle propagation
        self._create_propagation_frame(frames['frameA'])
        
        # Frame 0 - LIBRE
        self._create_frame0(frames['frame0'])
        
        # Frame 1 - Contrôle drone caméra
        self._create_dyn_and_camera_frame(frames['frame1'])
        
        # Frame 2 - Boutons RESET, PAUSE, QUIT
        self._create_control_buttons_frame(frames['frame2'])
        
        # Frame 2B - Boutons RECORD, STOP, REPLAY
        self._create_recorder_buttons_frame(frames['frame2B'])

        # Frame 3 - Circuit et Trajectoire cible
        self._create_circuits_frame(frames['frame3'])
        
        # Frame 4 - Volant et hauteur CdG
        self._create_balancing_frame(frames['frame4'])

        # Frame 5 - Régulateur et asservissement
        self._create_regulator_frame(frames['frame5'])
        
        # Frame 6 - Agent de Controles
        self._create_command_frame(frames['frame6'])
        
        # Frame 7 - Ouverture et transmission
        self._create_transmission_frame(frames['frame7'])
        
        # Frame 8 - Espace réservé
        frames['frame8'].pack()
        
        # Zone télémesures
        self._create_telemetry_zone()
    
    def _create_explore_states_frame(self, frame):
        """Crée le frame de tabulation des états possibles"""
        Label(frame, text="""États possibles:""", justify=LEFT, padx=20).pack()

        Checkbutton(frame, text="Explore cap", padx=20, variable=self.exp_cap, onvalue=1, offvalue=0).pack(anchor=W)
        Checkbutton(frame, text="Explore vit", padx=20, variable=self.exp_vit, onvalue=1, offvalue=0).pack(anchor=W)
        Checkbutton(frame, text="Explore vol", padx=20, variable=self.exp_vol, onvalue=1, offvalue=0).pack(anchor=W)
        Checkbutton(frame, text="Explore gaz", padx=20, variable=self.exp_gaz, onvalue=1, offvalue=0).pack(anchor=W)

        Button(frame, text="EXPLORE", fg="green", command=self._handle_explore).pack(padx=10, pady=5, anchor=N)

    def _create_command_frame(self, frame):
        """Crée le frame des commandes (libellés fournis par Kart_control.list_available_controls)."""
        Label(frame, text="""Commandes:""", justify=LEFT, padx=20).pack()
        self.command_radiobuttons = []
        for value, text in Kart_control.list_available_controls():
            rb = Radiobutton(frame, text=text, padx=20, variable=self.commandes, value=value)
            rb.pack(anchor=W)
            self.command_radiobuttons.append(rb)
        self.commandes.set(0)
    
    def _create_propagation_frame(self, frame):
        """Crée le frame de contrôle de propagation et forcage de vitesse"""
        # pas de tickinterval : les graduations sous un Scale horizontal laissent souvent une bande visuelle gênante
        self.pas_de_temps = Scale(frame, from_=0, to=100,
                                 length=100, label="Pas de temps (ms)", orient=HORIZONTAL)
        self.pas_de_temps.set(0)
        self.pas_de_temps.pack()
    
        Label(frame, text="Forcage vitesse (m/s) si <>0", justify=LEFT, padx=20).pack(anchor=W)
        self.forcage_v = StringVar(value="0")
        ent_fv = Entry(frame, textvariable=self.forcage_v, width=6, justify=CENTER)
        ent_fv.pack()
        for _seq in ("<Return>", "<KP_Enter>"):
            ent_fv.bind(_seq, self._focus_canvas_after_field)
    
        Label(frame, text="Forcage cap vitesse (deg)", justify=LEFT, padx=20).pack(anchor=W)
        # self.forcage_cap : IntVar déjà créé dans _create_control_panel (même plage 0..100 que l'ancien Scale)
        sb_cap = Spinbox(frame, from_=0, to=100, increment=1, textvariable=self.forcage_cap, width=6)
        sb_cap.pack()
        for _seq in ("<Return>", "<KP_Enter>"):
            sb_cap.bind(_seq, self._focus_canvas_after_field)

    def _create_frame0(self, frame):
        pass

    
    def _create_dyn_and_camera_frame(self, frame):
        """Crée le frame d'échelle d'affichage dynamique"""
        self.echelle_dyn = Scale(frame, from_=0, to=5, length=100, 
                                label="Aff. Dynamique", orient=HORIZONTAL)
        self.echelle_dyn.set(1.0)
        self.echelle_dyn.pack()
        
        """Crée le frame de contrôle de la caméra drone"""
        self.cam_alt = Scale(frame, from_=2, to=300, length=100, 
                            label="Altitude drone", orient=HORIZONTAL)
        self.cam_alt.set(self.cam_alt0)
        self.cam_alt.pack()
        
        self.cam_speed = Scale(frame, from_=0, to=self.cam_speedmax, length=100, 
                              label="Rapidité drone", orient=HORIZONTAL)
        self.cam_speed.set(self.cam_speed0)
        self.cam_speed.pack()
    
    def _create_control_buttons_frame(self, frame):
        """Crée le frame des boutons de contrôle"""
        Button(frame, text="RESET", fg="green", width=12,
                                    command=self._handle_reset).pack(padx=10, pady=5, anchor=N)
        Button(frame, text="PAUSE", fg="blue", width=12, 
                                    command=self._handle_pause).pack(padx=10, pady=5, anchor=CENTER)
        Button(frame, text="QUIT", fg="red", width=12, 
                                    command=self._quit_application).pack(padx=10, pady=5, anchor=S)

    def _create_recorder_buttons_frame(self, frame):
        """Crée le frame des boutons du recorder"""
        # width en caractères (police du bouton) : assez large pour « RECORDING » sans élargir le frame
        # Ne pas chaîner .pack() sur l'affectation : pack() retourne None.
        self.btn_record = Button(frame, text="RECORD", fg="green", width=12,
                                command=self._handle_record)
        self.btn_record.pack(padx=10, pady=5, anchor=N)
        Button(frame, text="STOP", fg="blue", width=12,
                                 command=self._handle_stop).pack(padx=10, pady=5, anchor=CENTER)
        self.btn_replay = Button(frame, text="REPLAY", fg="red", width=12,
                           command=self._handle_replay, state="disabled")
        self.btn_replay.pack(padx=10, pady=5, anchor=CENTER)
        Button(frame, text="READ", fg="black", width=12,
                                command=self.read_commands).pack(padx=10, pady=5, anchor=CENTER)

    def _create_circuits_frame(self, frame):
        """Crée le frame trajectoire cible, qui peut être un circuit d'ailleurs"""
        Label(frame, text="""Traj. cible:""", justify=LEFT, padx=20).pack()
        Button(frame, text="LOAD", fg="blue", width=12, 
                           command=self._handle_load_T_or_C).pack(padx=10, pady=5, anchor=CENTER)
        self.circuit.set(0)

        Button(frame, text="CLEAR", fg="blue", width=12, 
                           command=self._handle_clear_T_or_C).pack(padx=10, pady=5, anchor=CENTER)
    def _create_balancing_frame(self, frame):
        """Crée le frame de contrôle de position et hauteur CdG, 
         """
 
        self.pos_cdg = Scale(frame, from_=20, to=80, resolution=1, length=150, label="pos CdG %% (0 AR 100 AV)", orient=HORIZONTAL)
        self.pos_cdg.set(40)
        self.pos_cdg.pack()
        
        self.H_cdg = Scale(frame, from_=0, to=50, length=150, label="H CdG en %", orient=HORIZONTAL)
        self.H_cdg.set(0)
        self.H_cdg.pack()

    def _create_regulator_frame(self, frame):
        """Crée le frame des réglages asservisements de controle:
               Une case à cocher pour le régulateur de vitesse
               et trois paramètres (P1, P2, P3) pour l'asservissement de controle"""
        
        Checkbutton(frame, text="Regulateur de vitesse", padx=20, variable=self.regul,
                   onvalue=1, offvalue=0).pack(anchor=W)
        
        self.ass_p1 = Scale(frame, from_=0, to=100, resolution=1, length=100, label="Paramètre p1", orient=HORIZONTAL)
        self.ass_p1.set(10)
        self.ass_p1.pack()

        self.ass_p2 = Scale(frame, from_=0, to=100, resolution=1, length=100, label="Paramètre p2", orient=HORIZONTAL)
        self.ass_p2.set(10)
        self.ass_p2.pack()

        self.ass_p3 = Scale(frame, from_=0, to=100, resolution=1, length=100, label="Paramètre p3", orient=HORIZONTAL)
        self.ass_p3.set(10)
        self.ass_p3.pack()

    def _create_transmission_frame(self, frame):
        """Crée le frame de transmission"""
        self.ouverture = Scale(frame, from_=-5, to=5, resolution=1, length=100, 
                              label="Ouverture", orient=HORIZONTAL)
        self.ouverture.set(0)
        self.ouverture.pack()
        
        Label(frame, text="""Transmission:""", justify=LEFT, padx=20).pack()
        Radiobutton(frame, text="Propulsion", padx=20, variable=self.transm, value=0).pack(anchor=W)
        Radiobutton(frame, text="Axe arrière", padx=20, variable=self.transm, value=1).pack(anchor=W)
        Radiobutton(frame, text="Full 4 wheels", padx=20, variable=self.transm, value=2).pack(anchor=W)
    
    def _create_telemetry_zone(self):
        """Crée la zone de télémesures"""
        self.telemesure1 = Label(self.fenetre, fg="blue")
        self.telemesure1.pack()
        self.telemesure2 = Label(self.fenetre, fg="green")
        self.telemesure2.pack()
        self.telemesure3 = Label(self.fenetre, fg="red")
        self.telemesure3.pack()
    
    def _create_canvas(self):
        """Crée le canvas d'animation"""
        self.cnv = Canvas(self.fenetre, width=1800, height=1000, background="#003300")
        self.cnv.pack()

    def _focus_canvas_after_field(self, event=None):
        """Après Entrée dans un champ (Entry / Spinbox), rendre le focus au canvas pour les raccourcis."""
        if self.cnv is not None:
            self.cnv.focus_set()
    
    def _setup_key_bindings(self):
        """Configure les raccourcis clavier"""
        self.cnv.bind("<KeyPress>", self.press_key)
        self.cnv.bind("<KeyRelease>", self.stop_key)
        self.cnv.focus_set()
        self.cnv.focus_get()
        self.cnv.focus_force()
 
    def press_key(self, event): 
        """Gère les pressions de touches"""
        # Cette méthode doit être surchargée par la classe qui utilise UI
        pass
    
    def stop_key(self, event):
        """Gère le relâchement des touches"""
        # Cette méthode doit être surchargée par la classe qui utilise UI
        pass
    
    def _handle_explore(self):
        """Lance la tabulation des états possibles du Kart avec les cases cochées
        """
        self.explore_status = True

    def _handle_reset(self):
        """Gère l'action de reset - appelle la méthode surchargée"""
        self.reset()
    
    def _handle_pause(self):
        """Met en pause la simulation"""
        self.simul_pause = not self.simul_pause

    def _handle_record(self):
        """Change le status de self.record_status et du bouton RECORD
           et la classe fille SimulationUI gérera l'enregistrement
        """
        
        self.record_status = True
        self.btn_record.config(text="RECORDING", state="disabled")

    def _handle_stop(self):
        """Change le status de self.record_status et du bouton RECORD
        """
        self.record_status = False
        self.btn_record.config(text="RECORD")  # reste disabled jusqu'au prochain reset

    def _handle_load_T_or_C(self):
        """Gère l'action de chargement de la trajectoire cible
        Sera chargé dans la classe SimulationUI"""
        pass

    def _handle_clear_T_or_C(self):
        """Gère l'action de suppression de la trajectoire cible
        Sera chargé dans la classe SimulationUI"""
        pass

    def _handle_replay(self):
        """Gère l'action de pause - appelle la méthode surchargée"""
        self.record_replay()
        self.simul_pause = False

    @abstractmethod
    def reset(self):
        """Remet à zéro la simulation"""
        # Cette méthode doit être surchargée par la classe qui utilise UI
        pass

    @abstractmethod
    def read_commands(self):
        """Lit un fichier de commandes et remplit self.controls_recorded (et éventuels paramètres associés)."""
        pass
    
    def show_telemetry_1(self, pas_simul, temps, t_cyclemax_ms, t_framemax_ms, F_com):
        """Met à jour l'affichage de télémesure ligne 1.

        Tous les calculs numériques doivent être faits en amont :
        cette fonction se contente d'afficher les valeurs passées en arguments.
        """
        # Télémesure 1 (affichage direct des arguments formatés)
        text1="SIMULATION -   PAUSE  - " if self.simul_pause else "SIMULATION - RUNNING  -"
        text2=" RECORDER - OFF -" if not self.record_status else " RECORDER -  ON - "
        texteaff = (text1+
            f"N= {pas_simul:10}  T = {temps:6.2f}  "
            f"Tcyclemax = {t_cyclemax_ms:3d} ms Tframemax = {t_framemax_ms:3d} ms "+
            text2+
            f" F_com = {F_com:5d}")

        self.telemesure1.config(text=str(texteaff))

    def show_telemetry_2(self, pos_x, pos_y, vit_x, vit_y, lacet_deg, v_lacet_deg, V, V_kmh, vold, idx, ecart_lat, v_lat, curv, curv_N):
        """Met à jour l'affichage de télémesure ligne 1.

        Tous les calculs numériques doivent être faits en amont :
        cette fonction se contente d'afficher les valeurs passées en arguments.
        """
        # Télémesure 1 (affichage direct des arguments formatés)
        texteaff = ("KART "
            f"X = {pos_x:6.2f}   Y = {pos_y:6.2f}   Lacet = {lacet_deg:6.2f} V_lacet = {v_lacet_deg:6.2f} "
            f"Vx = {vit_x:6.2f}  Vy = {vit_y:6.2f}  V =  {V:6.2f} m/s =  {V_kmh:6.2f} km/h"
            f"Vold = {vold:6.2f} Idx = {idx:5d} Ecart_lat = {ecart_lat:6.2f} V_lat = {v_lat:6.2f}"
            f"Curv = {curv:6.2f} Curv_N = {curv_N:6.2f}"
        )
        self.telemesure2.config(text=str(texteaff))

    def show_telemetry_3(self, f_cdg_x, f_cdg_y, f_cdg_z, force_cdg, moment_cdg, radius, varbre, vstab):
        """Met à jour l'affichage de télémesure ligne 3
        """
        # Télémesure 3 (affichage direct des arguments formatés)
        texteaff = ("KART INTERNE "
            f"Fcdg x ={f_cdg_x:^+10.2f}  Fcdg y ={f_cdg_y:^+10.2f}  Fcdg z ={f_cdg_z:^+10.2f} "
            f"F_cdg = {force_cdg:^+10.2f} Mcdg ={moment_cdg:^+10.2f}   Radius ={radius:^+10.2f} "
            f"Varbre = {varbre:^+10.2f}  Vstab = {vstab:^+10.2f}"
        )
        self.telemesure3.config(text=str(texteaff))
    
    def update_camera_position(self, position):
        """Met à jour la position de la caméra drone en fonction de la position du kart passée en argument"""
        self.speedcam = self.cam_speed.get()
        self.xcam = (self.speedcam * position[0] + (self.cam_speedmax - self.speedcam) * self.xcam) / self.cam_speedmax
        self.ycam = (self.speedcam * position[1] + (self.cam_speedmax - self.speedcam) * self.ycam) / self.cam_speedmax
        
    def mainloop(self):
        """Lance la boucle principale de l'interface"""
        self.fenetre.mainloop()
    
    def after(self, ms, callback, *args):
        """Programme un appel de fonction après un délai (même sémantique que ``Tk.after``)."""
        self.fenetre.after(ms, callback, *args)
