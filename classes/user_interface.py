import tkinter as tk
from abc import abstractmethod
import numpy as np
import time
from tkinter import (Tk, ttk, Canvas, Frame, Button, LEFT, RIGHT, TOP, BOTTOM, 
                     CENTER, HORIZONTAL, VERTICAL, ARC, LAST, Label, Scale,
                     Checkbutton, Radiobutton, IntVar, W, N, S, DoubleVar)
from .utils import tourne_vecteur, vehicule2piste, piste2vehicule, norme_vecteur


class User_Interface:
    """Classe gérant l'interface utilisateur du simulateur de kart"""
    
    def __init__(self, kart):
        """         Initialise l'interface utilisateur.  Args:   kart: Instance de la classe Kart """

        self.kart = kart
        
        # Variables d'état de l'interface
        self.fenetre = None
        self.cnv = None
        self.telemesure1 = None
        self.telemesure2 = None
        
        # Variables de contrôle
        self.volant_curseur = None
        self.pas_de_temps = None
        self.echelle_dyn = None
        self.H_cdg = None
        self.ouverture = None
        
        # Variables d'état (initialisées après création de la fenêtre)
        self.commandes = None
        self.methode = None
        self.regul = None
        self.ass_d = None
        self.transm = None
        
        # Variables de simulation
        self.F_com = []
        self.Vold = 0.
        self.t_cyclemax = 0.
                
        # Variable dtold pour la fonction pause (sera surchargée par Simulation)
        self.dtold = 25
        
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
        self.fenetre.title("Simulateur Sprint Car by Laurent Gauthier - V0.13")
    
    def _create_control_panel(self):
        """Crée le panneau de contrôle avec tous les widgets"""
        # Initialisation des variables Tkinter après création de la fenêtre
        self.commandes = IntVar()
        self.methode = IntVar()
        self.regul = IntVar()
        self.ass_d = IntVar()
        self.transm = IntVar()
        
        # Variables de simulation
        self.pas_simul = IntVar()
        self.temps = DoubleVar()
        self.pas_com = IntVar()
        
        # Initialisation des valeurs
        self.pas_simul.set(0)
        self.temps.set(0.0)
        self.pas_com.set(0)
        
        # Bandeau principal
        bandeau = Frame(self.fenetre, width=1800, height=100, highlightbackground="red", highlightthickness=2)
        bandeau.pack()
        
        # Création des frames
        frames = {}
        frame_names = ['frameB', 'frameA', 'frame0', 'frame1', 'frame2', 
                      'frame3', 'frame4', 'frame5', 'frame6', 'frame7', 'frame8']
        
        for i, name in enumerate(frame_names):
            frames[name] = Frame(bandeau, width=200, height=100, 
                               highlightbackground="black", highlightthickness=1)
            frames[name].pack(side=LEFT)
        
        # Frame B - Commandes
        self._create_command_frame(frames['frameB'])
        
        # Frame A - Contrôle propagation
        self._create_propagation_frame(frames['frameA'])
        
        # Frame 0 - Échelle affichage dynamique
        self._create_dynamic_scale_frame(frames['frame0'])
        
        # Frame 1 - Contrôle drone caméra
        self._create_camera_frame(frames['frame1'])
        
        # Frame 2 - Boutons RESET, PAUSE, QUIT
        self._create_control_buttons_frame(frames['frame2'])
        
        # Frame 3 - Volant et hauteur CdG
        self._create_steering_frame(frames['frame3'])

        # Frame 4 - Espace réservé pour contrôles futurs
        # (pas de boutons dupliqués)

        # Frame 5 - Régulateur et asservissement
        self._create_regulator_frame(frames['frame5'])
        
        # Frame 6 - Asservissement dynamique
        self._create_dynamic_control_frame(frames['frame6'])
        
        # Frame 7 - Ouverture et transmission
        self._create_transmission_frame(frames['frame7'])
        
        # Frame 8 - Espace réservé
        frames['frame8'].pack()
        
        # Zone télémesures
        self._create_telemetry_zone()
    
    def _create_command_frame(self, frame):
        """Crée le frame des commandes"""
        Label(frame, text="""Commandes:""", justify=LEFT, padx=20).pack()
        Radiobutton(frame, text="Clavier", padx=20, variable=self.commandes, value=0).pack(anchor=W)
        Radiobutton(frame, text="W Fichier", padx=20, variable=self.commandes, value=1).pack(anchor=W)
        Radiobutton(frame, text="R Fichier", padx=20, variable=self.commandes, value=2).pack(anchor=W)
        Radiobutton(frame, text="Reset", padx=20, variable=self.commandes, value=3).pack(anchor=W)
        self.commandes.set(0)
    
    def _create_propagation_frame(self, frame):
        """Crée le frame de contrôle de propagation"""
        self.pas_de_temps = Scale(frame, from_=0, to=300, tickinterval=0.01, 
                                 length=100, label="Pas de temps (ms)", orient=HORIZONTAL)
        self.pas_de_temps.set(0)
        self.pas_de_temps.pack()
        
        Label(frame, text="""Propagateur:""", justify=LEFT, padx=20).pack()
        Radiobutton(frame, text="Euler", padx=20, variable=self.methode, value=0).pack(anchor=W)
        Radiobutton(frame, text="Runge-Kutta 4", padx=20, variable=self.methode, value=1).pack(anchor=W)
        self.methode.set(0)
    
    def _create_dynamic_scale_frame(self, frame):
        """Crée le frame d'échelle d'affichage dynamique"""
        self.echelle_dyn = Scale(frame, from_=0, to=5, length=100, 
                                label="Aff. Dynamique", orient=HORIZONTAL)
        self.echelle_dyn.set(1.0)
        self.echelle_dyn.pack()
    
    def _create_camera_frame(self, frame):
        """Crée le frame de contrôle de la caméra drone"""
        self.cam_alt = Scale(frame, from_=10, to=1000, length=100, 
                            label="Altitude drone", orient=HORIZONTAL)
        self.cam_alt.set(self.cam_alt0)
        self.cam_alt.pack()
        
        self.cam_speed = Scale(frame, from_=0, to=self.cam_speedmax, length=100, 
                              label="Rapidité drone", orient=HORIZONTAL)
        self.cam_speed.set(self.cam_speed0)
        self.cam_speed.pack()
    
    def _create_control_buttons_frame(self, frame):
        """Crée le frame des boutons de contrôle"""
        Button(frame, text="RESET", fg="green", command=self._handle_reset).pack(padx=10, pady=5, anchor=N)
        Button(frame, text="PAUSE", fg="blue", command=self._handle_pause).pack(padx=10, pady=5, anchor=CENTER)
        Button(frame, text="QUIT", fg="red", command=self.fenetre.destroy).pack(padx=10, pady=5, anchor=S)
    
    def _create_steering_frame(self, frame):
        """Crée le frame de contrôle du volant et hauteur CdG"""
        self.volant_curseur = Scale(frame, from_=-45, to=45, length=200, 
                                   label="Volant", orient=HORIZONTAL)
        self.volant_curseur.set(0)
        self.volant_curseur.pack()
        
        self.H_cdg = Scale(frame, from_=0, to=100, length=200, 
                          label="H CdG en %", orient=HORIZONTAL)
        self.H_cdg.set(0)
        self.H_cdg.pack()
    
    def _create_regulator_frame(self, frame):
        """Crée le frame du régulateur de vitesse"""
        def set_v():
            if self.regul.get():
                self.Vold = norme_vecteur(self.kart.vitesse)
        
        Checkbutton(frame, text="Regulateur de vitesse", padx=20, variable=self.regul,
                   onvalue=1, command=set_v, offvalue=0).pack(anchor=W)
        
        self.ass_d = IntVar()
        Checkbutton(frame, text="Asserv. d", padx=20, variable=self.ass_d,
                   onvalue=1, offvalue=0).pack(anchor=W)
        
        self.ass_d0 = Scale(frame, from_=-2, to=2, resolution=0.1, length=100, 
                           label="V_lacet cible", orient=HORIZONTAL)
        self.ass_d0.set(0)
        self.ass_d0.pack()
        
        self.ass_dgain_stat = Scale(frame, from_=0, to=5, resolution=0.1, length=100, 
                                   label="Gain Statique", orient=HORIZONTAL)
        self.ass_dgain_stat.set(2.5)
        self.ass_dgain_stat.pack()
    
    def _create_dynamic_control_frame(self, frame):
        """Crée le frame de contrôle dynamique"""
        self.ass_dgain_dyn = Scale(frame, from_=0, to=5, resolution=0.1, length=100, 
                                  label="Gain Dynamique", orient=HORIZONTAL)
        self.ass_dgain_dyn.set(2.5)
        self.ass_dgain_dyn.pack()
    
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
    
    def _create_canvas(self):
        """Crée le canvas d'animation"""
        self.cnv = Canvas(self.fenetre, width=1800, height=1000, background="#003300")
        self.cnv.pack()
    
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
    
    def _handle_reset(self):
        """Gère l'action de reset - appelle la méthode surchargée"""
        self.reset()
    
    def _handle_pause(self):
        """Gère l'action de pause - appelle la méthode surchargée"""
        self.pause()
    
    @abstractmethod
    def reset(self):
        """Remet à zéro la simulation"""
        # Cette méthode doit être surchargée par la classe qui utilise UI
        pass
    
    def pause(self):
        """Met en pause la simulation"""
        current_value = self.pas_de_temps.get()
        
        if current_value > 0:  # Si la simulation tourne
            self.dtold = current_value  # Sauvegarde la valeur actuelle
            self.pas_de_temps.set(0)    # Met en pause
        else:  # Si la simulation est en pause
            self.pas_de_temps.set(self.dtold)  # Reprend avec la valeur sauvegardée
    
    def update_telemetry(self, pas_simul, temps, t_cyclemax, force_cdg, moment_cdg, 
                        position, vitesse, lacet, V, gaz, F_com, varbre, vold):
        """Met à jour l'affichage de télémesure"""
        # Télémesure 1
        texteaff = (f"N= {pas_simul:10}  T = {temps:6.2f}  Tcyclemax = {int(t_cyclemax*1000):3d} ms "
                   f"F_com = {len(F_com):5d}  X = {position[0]:6.2f}   Y = {position[1]:6.2f}   Z = {position[2]:6.2f} "
                   f"Vx = {vitesse[0]:6.2f}  Vy = {vitesse[1]:6.2f}   Lacet = {lacet*180./np.pi:6.2f} "
                   f"V =  {V:6.2f} m/s =  {V*3.6:6.2f} km/h     Gaz = {gaz:3.0f} ch Vold = {vold:6.2f}")
        self.telemesure1.config(text=str(texteaff))
        
        # Télémesure 2
        radius = (1000000000. if (norme_vecteur(force_cdg) < 0.00001) 
                  else self.kart.masse * V * V / norme_vecteur(force_cdg))
        f_cdg = piste2vehicule(force_cdg, lacet)
        texteaff = (f"FORCES APPLIQUES AU CDG:  "
                   f"Fcdg x ={f_cdg[0]:^+10.2f}  Fcdg y ={f_cdg[1]:^+10.2f}  Fcdg z ={f_cdg[2]:^+10.2f} "
                   f"F_cdg = {norme_vecteur(force_cdg):^+10.2f} Mcdg ={moment_cdg[2]:^+10.2f}   Radius ={radius:^+10.2f} "
                   f"Varbre = {varbre:^+10.2f}  Vstab = {np.dot(force_cdg,vehicule2piste(vitesse, lacet)):^+10.2f}")
        self.telemesure2.config(text=str(texteaff))
    
    def update_camera_position(self):
        """Met à jour la position de la caméra drone en fonction de la position du kart passée en argument"""
        self.speedcam = self.cam_speed.get()
        position = self.kart.position
        self.xcam = (self.speedcam * position[0] + (self.cam_speedmax - self.speedcam) * self.xcam) / self.cam_speedmax
        self.ycam = (self.speedcam * position[1] + (self.cam_speedmax - self.speedcam) * self.ycam) / self.cam_speedmax
        
    def mainloop(self):
        """Lance la boucle principale de l'interface"""
        self.fenetre.mainloop()
    
    def after(self, ms, callback):
        """Programme un appel de fonction après un délai"""
        self.fenetre.after(ms, callback)
