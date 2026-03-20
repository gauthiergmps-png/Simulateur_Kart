"""
Module pour la gestion de l'image de fond géolocalisée
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.image as mpimg
import numpy as np
import os


class ImageBackgroundManager:
    """Gestionnaire d'image de fond géolocalisée pour le simulateur de circuit"""
    
    def __init__(self, parent_window, ax, info_label):
        """
        Initialise le gestionnaire d'image de fond
        
        Args:
            parent_window: Fenêtre parente (tkinter root)
            ax: Axe matplotlib pour l'affichage
            info_label: Label pour afficher les informations
        """
        self.parent_window = parent_window
        self.ax = ax
        self.info_label = info_label
        
        # Variables pour l'image de fond
        self.background_image = None
        self.image_extent = None
        self.image_loaded = False
    
    def load_background_image(self):
        """Charge une image JPEG comme modèle de circuit"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Sélectionner l'image modèle du circuit",
            filetypes=[("Images PNG", "*.png"), ("Images JPEG", "*.jpg *.jpeg"),
             ("Tous les fichiers", "*.*")] )
        
        if filename:
            try:
                # Charger l'image
                self.background_image = mpimg.imread(filename)
                
                # Demander les coordonnées géographiques à l'utilisateur
                coords = self.get_image_coordinates()
                if coords is None:
                    return  # Utilisateur a annulé
                
                lat_nw, lon_nw, lat_se, lon_se = coords
                
                # Convertir les coordonnées géographiques en coordonnées métriques
                # Utilisation d'une projection simple (approximation pour petites distances)
                # Pour une précision plus élevée, on pourrait utiliser pyproj
                
                # Calculer le centre géographique
                lat_center = (lat_nw + lat_se) / 2
                lon_center = (lon_nw + lon_se) / 2
                
                # Conversion approximative en mètres (1 degré ≈ 111320 m à l'équateur)
                # Ajustement pour la latitude (cosinus de la latitude)
                lat_factor = np.cos(np.radians(lat_center))
                
                # Calculer les dimensions en mètres
                width_m = (lon_se - lon_nw) * 111320 * lat_factor
                height_m = (lat_nw - lat_se) * 111320  # Latitude décroît vers le sud
                
                # Calculer les coordonnées du coin nord-ouest en mètres
                x_nw = (lon_nw - lon_center) * 111320 * lat_factor
                y_nw = (lat_nw - lat_center) * 111320
                
                # Définir l'étendue de l'image en mètres
                self.image_extent = [x_nw, x_nw + width_m, y_nw - height_m, y_nw]
                
                self.image_loaded = True
                self.info_label.config(text=f"Image modèle chargée: {os.path.basename(filename)}\n"
                                           f"Dimensions: {width_m:.0f}m × {height_m:.0f}m")
                
                # Ajuster la vue pour afficher l'image complète
                # self.ax.set_xlim(self.image_extent[0], self.image_extent[1])
                # self.ax.set_ylim(self.image_extent[2], self.image_extent[3])
                # self.ax._xlim = (self.image_extent[0], self.image_extent[1])
                # self.ax._ylim = (self.image_extent[2], self.image_extent[3])
                
                return True
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement de l'image: {e}")
                self.background_image = None
                self.image_loaded = False
                return False
        
        return False
    
    def get_image_coordinates(self):
        """Demande à l'utilisateur les coordonnées géographiques de l'image"""
        # Première boîte de dialogue : Coin Nord-Ouest
        nw_coords = self.get_single_point_coordinates("Coin Nord-Ouest", 
                                                     "Placez votre souris sur le coin nord-ouest de l'image\n"
                                                     "et copiez les coordonnées affichées en bas de l'écran")
        if nw_coords is None:
            return None
        
        # Deuxième boîte de dialogue : Coin Sud-Est
        se_coords = self.get_single_point_coordinates("Coin Sud-Est", 
                                                     "Placez votre souris sur le coin sud-est de l'image\n"
                                                     "et copiez les coordonnées affichées en bas de l'écran")
        if se_coords is None:
            return None
        
        lat_nw, lon_nw = nw_coords
        lat_se, lon_se = se_coords
        
        # Validation finale
        if lat_nw <= lat_se:
            messagebox.showerror("Erreur", "La latitude nord-ouest doit être supérieure à la latitude sud-est")
            return None
        if lon_nw >= lon_se:
            messagebox.showerror("Erreur", "La longitude nord-ouest doit être inférieure à la longitude sud-est")
            return None
        
        return (lat_nw, lon_nw, lat_se, lon_se)
    
    def get_single_point_coordinates(self, title, instructions):
        """Demande les coordonnées d'un seul point"""
        # Créer une fenêtre de dialogue pour les coordonnées
        coord_window = tk.Toplevel(self.parent_window)
        coord_window.title(f"Coordonnées - {title}")
        coord_window.geometry("500x400")
        coord_window.transient(self.parent_window)
        coord_window.grab_set()
        
        result = [None]  # Pour retourner le résultat
        
        def validate_and_close():
            try:
                # Récupérer directement le contenu du widget Entry
                coords_text = coords_entry.get().strip()
                
                # Parser les coordonnées - formats acceptés :
                # "lat,lon" ou "lat lon" ou "lat, lon"
                coords_text = coords_text.replace(',', ' ')
                parts = coords_text.split()
                
                if len(parts) != 2:
                    messagebox.showerror("Erreur", "Format invalide. Utilisez: latitude, longitude")
                    return
                
                lat = float(parts[0])
                lon = float(parts[1])
                
                # Validation basique
                if not (-90 <= lat <= 90):
                    messagebox.showerror("Erreur", "La latitude doit être entre -90 et 90")
                    return
                if not (-180 <= lon <= 180):
                    messagebox.showerror("Erreur", "La longitude doit être entre -180 et 180")
                    return
                
                result[0] = (lat, lon)
                coord_window.destroy()
                
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer des coordonnées valides (format: 43.202153, 0.499418)")
        
        def cancel():
            coord_window.destroy()
        
        # Interface utilisateur
        ttk.Label(coord_window, text=f"Coordonnées du {title}:", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Instructions
        ttk.Label(coord_window, text=instructions, justify=tk.LEFT).pack(pady=5)
        
        # Zone de texte pour les coordonnées
        coords_frame = ttk.Frame(coord_window)
        coords_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        ttk.Label(coords_frame, text="Coordonnées (latitude, longitude):", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Zone de saisie simple (une seule ligne)
        coords_entry = ttk.Entry(coords_frame, width=50, font=('Courier', 10))
        coords_entry.pack(fill=tk.X, pady=5)
        
        # Lier la touche Entrée à la validation
        coords_entry.bind('<Return>', lambda event: validate_and_close())
        
        # Exemples de formats
        examples_frame = ttk.LabelFrame(coords_frame, text="Exemples de formats acceptés:", padding=10)
        examples_frame.pack(fill=tk.X, pady=10)
        
        examples = [
            "43.202153, 0.499418",
            "43.202153,0.499418", 
            "43.202153 0.499418"
        ]
        
        for i, example in enumerate(examples):
            ttk.Label(examples_frame, text=f"{i+1}. {example}", 
                     font=('Courier', 9), foreground='gray').pack(anchor=tk.W, pady=1)
        
        # Boutons
        button_frame = ttk.Frame(coord_window)
        button_frame.pack(pady=20, fill=tk.X, padx=20)
        
        ttk.Button(button_frame, text="Valider", command=validate_and_close).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annuler", command=cancel).pack(side=tk.LEFT, padx=10)
        
        # Bouton pour coller depuis le presse-papiers
        def paste_coords():
            try:
                clipboard_content = coord_window.clipboard_get()
                coords_entry.delete(0, tk.END)
                coords_entry.insert(0, clipboard_content)
            except tk.TclError:
                messagebox.showerror("Erreur", "Aucun contenu dans le presse-papiers")
        
        ttk.Button(button_frame, text="Coller", command=paste_coords).pack(side=tk.LEFT, padx=10)
        
        # Centrer la fenêtre
        coord_window.update_idletasks()
        x = (coord_window.winfo_screenwidth() // 2) - (coord_window.winfo_width() // 2)
        y = (coord_window.winfo_screenheight() // 2) - (coord_window.winfo_height() // 2)
        coord_window.geometry(f"+{x}+{y}")
        
        # Focus sur la zone de saisie
        coords_entry.focus_set()
        
        # Attendre la fermeture de la fenêtre
        coord_window.wait_window()
        
        return result[0]
    
    def display_background_image(self, circuit_input_mode):
        """Affiche l'image de fond si elle est chargée et en mode saisie circuit"""
        if circuit_input_mode and self.image_loaded and self.background_image is not None:
            self.ax.imshow(self.background_image, extent=self.image_extent, alpha=0.3, aspect='auto', zorder=0)
    
    def is_image_loaded(self):
        """Retourne True si une image est chargée"""
        return self.image_loaded
    
    def reset_image(self):
        """Remet à zéro l'image de fond"""
        self.background_image = None
        self.image_extent = None
        self.image_loaded = False
