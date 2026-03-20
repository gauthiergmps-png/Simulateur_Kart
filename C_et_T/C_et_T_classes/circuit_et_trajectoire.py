from .profil import Profil
import numpy as np
import json
import os
import csv
from pathlib import Path
from tkinter import filedialog, messagebox

""" Ce fichier contient les deux classes principales: Circuit et Trajectoire, qui héritent de la classe Profil.

    Et une fonction d'optimisation de la vitesse

"""


DIR_FILES = "C_et_T_files"


def _dir_files_path() -> Path:
    """Retourne le dossier de travail pour les fichiers (toujours DIR_FILES)."""
    base_dir = Path(__file__).resolve().parent.parent  # .../C_et_T
    p = base_dir / DIR_FILES
    p.mkdir(parents=True, exist_ok=True)
    return p


def _is_within_dir_files(filepath: str) -> bool:
    """Vrai si filepath est dans DIR_FILES (après résolution)."""
    try:
        file_path = Path(filepath).resolve()
        dir_path = _dir_files_path().resolve()
        file_path.relative_to(dir_path)
        return True
    except Exception:
        return False


def _force_into_dir_files(filepath: str) -> str:
    """Force un chemin vers DIR_FILES en gardant uniquement le basename."""
    filename = os.path.basename(filepath)
    return str(_dir_files_path() / filename)


class Circuit(Profil):
    """
    Classe Circuit héritant de Profil, y ajoute la gestion de la largeur et des bordures
    """
    
    def __init__(self, name="Circuit", is_closed=True, width=10.0, n_fine_points=100):
        super().__init__(name, is_closed, n_fine_points)
        self.width = width
        self.left_border = []
        self.right_border = []
        
    def set_width(self, width):
        """Définit la largeur du circuit"""
        self.width = width
        self.calculate_borders()
        
    def calculate_borders(self):
        """Calcule les bordures gauche et droite du circuit"""
        if len(self.fine_points) == 0 or len(self.normals) == 0:
            return
            
        # Calcul des bordures avec numpy
        left_border = np.array(self.fine_points) + np.array(self.normals) * self.width / 2
        right_border = np.array(self.fine_points) - np.array(self.normals) * self.width / 2
        
        self.left_border = left_border.tolist()
        self.right_border = right_border.tolist()
        
        # Ajuster les extrémités pour les circuits ouverts
        if not self.is_closed:
            self.left_border.append(self.fine_points[-1])
            self.right_border.append(self.fine_points[-1])
            self.left_border.insert(0, self.fine_points[0])
            self.right_border.insert(0, self.fine_points[0])
 
    def reset_fine_profile(self):
        """Surcharge pour réinitialiser aussi les bordures du circuit"""
        super().reset_fine_profile()
        self.left_border = []
        self.right_border = []

    def calculate_parameters(self):
        """Surcharge pour calculer les paramètres d'un circuit"""
        # on a dejà les paramètres du profil parent, à savoir tangents[], normals[], curvatures[], distances[], length
        super().calculate_parameters()

        """Calcule des paramètres specifiques: les bordures:"""
        self.calculate_borders()

    def is_point_inside(self, x, y, add=False):
        """Vérifie si un point (x, y) est à l'intérieur du circuit"""
        debug = False
        if add and debug: print(f"Appel inside for x = {x}, y = {y}")
        if len(self.fine_points) == 0 or len(self.normals) == 0:
            return False
            
        point = np.array([x, y])
        
        # Méthode 1: Vérification par projection sur la normale
        closest_idx = self.closest_fine_point(x, y, threshold=1000)
        if add and debug: print(f"Debug: plus proche point = {closest_idx}")
        if closest_idx is None:
            return False
        
        # Vecteur du point circuit au point testé
        vector_to_point = point - self.fine_points[closest_idx]
        distance = np.linalg.norm(vector_to_point)
        # Projection sur le vecteur normal
        normal = self.normals[closest_idx]
        projection = np.dot(vector_to_point, normal)

        if add and debug: print(f"Debug: projection = {projection}, distance = {distance}", 
                                  f"width = {self.width}")
        
        if closest_idx == 0:
            # on est au début du circuit, il faut être du bon cotésur la ligne de départ -  A FAIRE
            pass
        if closest_idx == len(self.fine_points) - 1:
            # on est à la fin du circuit, il faut être sur la ligne d'arrivée -  A FAIRE
            pass
        # Le point est dans le circuit si sa projection est inférieure à la moitié de la largeur
        if abs(projection) <= self.width / 2: # and distance <= self.width / 2:
            return True
        
    def to_dict(self):
        """Convertit le circuit en dictionnaire pour sauvegarde"""
        profil = super().to_dict()
        circuit_data = {
            'width': self.width,
            'left_border': self.left_border,
            'right_border': self.right_border}
        data = {'profil': profil, 'circuit_data': circuit_data}
        return data
        
    def from_dict(self, data):
        """Charge le circuit depuis un dictionnaire"""
        # Nouveau format (issu de to_dict): {'profil': {...}, 'circuit_data': {...}}
        profil_data = data.get('profil', None)
        circuit_data = data.get('circuit_data', None)

        if profil_data is not None:
            super().from_dict(profil_data)

        if circuit_data is not None:
            self.width = circuit_data.get('width', self.width)
            self.left_border = circuit_data.get('left_border', [])
            self.right_border = circuit_data.get('right_border', [])

    def _save_circuit_csv(self, filename):
        """Sauvegarde CSV (actuellement non implémentée)."""
        messagebox.showerror("Erreur", "Module à coder ")
        return False

    def _save_circuit_json(self, filename):
        """Sauvegarde JSON en utilisant uniquement circuit.to_dict()."""
        data = self.to_dict()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_circuit_dialog(self):
        """Ouvre une boite de dialogue et sauvegarde le circuit (.csv ou .json)."""
        if len(self.raw_points) == 0:
            messagebox.showerror("Erreur", "Aucun circuit à sauvegarder")
            return False

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=str(_dir_files_path()),
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filename:
            return False

        filename = _force_into_dir_files(filename)

        try:
            if filename.lower().endswith('.json'):
                self._save_circuit_json(filename)
            elif filename.lower().endswith('.csv'):
                self._save_circuit_csv(filename)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return False
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
            return False

    @classmethod
    def load_circuit_dialog(cls):
        """Ouvre une boite de dialogue et charge un circuit (.csv ou .json)."""
        filename = filedialog.askopenfilename(
            initialdir=str(_dir_files_path()),
            filetypes=[("All files", "*.*")]
        )

        if not filename:
            return None

        if not _is_within_dir_files(filename):
            messagebox.showerror("Erreur", f"Lecture interdite hors de '{DIR_FILES}'.")
            return None

        try:
            new_circuit = cls()
            if filename.endswith('.csv'):
                cls._load_circuit_csv(new_circuit, filename)
            elif filename.endswith('.json'):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                new_circuit.from_dict(data)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return None
            return new_circuit
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
            return None

    @staticmethod
    def _load_circuit_csv(circuit, filename):
        """Charge un circuit depuis un fichier CSV."""
        circuit.raw_points = []

        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)

            # Lire les métadonnées
            for row in reader:
                if not row or not row[0].startswith('#'):
                    break
                if row[0].startswith('# Width:'):
                    circuit.width = float(row[1])
                elif row[0].startswith('# Closed:'):
                    circuit.is_closed = row[1].lower() == 'true'

            # Chercher la ligne d'en-tête des colonnes
            for row in reader:
                if row and len(row) >= 4 and row[0] == 'Point_Index':
                    break

            # Lire les points bruts
            for row in reader:
                if not row or len(row) < 4:
                    break
                if row[3] == 'Raw':
                    try:
                        x = float(row[1])
                        y = float(row[2])
                        circuit.raw_points.append([x, y])
                    except ValueError:
                        continue



class Trajectoire(Profil):
    """
    Classe Trajectoire héritant de Profil, ajoute la gestion des vitesses et du temps au tour
    """
    
    def __init__(self, name="Trajectoire", is_closed=True, max_acceleration=9.81, max_velocity=150/3.6, n_fine_points=100):
        super().__init__(name, is_closed, n_fine_points)
        self.max_acceleration = max_acceleration  # m/s²  soit 1g donc adhérence pneus = 1
        self.max_velocity = max_velocity          # m/s 41.6 m/s, soit 150Km/h
        self.velocities = []                     # Vitesses en chaque point
        self.type_accel = []                     # Type d'accélération en chaque point
        self.optimization_type = 1              # Type d'optimisation
        self.lap_time = 0.0                      # Temps au tour
        
    def reset_fine_profile(self):
        """Surcharge pour réinitialiser aussi les attributs spécifiques à la trajectoire"""
        super().reset_fine_profile()
        self.velocities = []
        self.lap_time = 0.0
            
    def calculate_lap_time(self):
        """Calcule le temps au tour selon les vitesses"""
        if len(self.velocities) == 0 or len(self.fine_points) == 0:
            return
            
        total_time = 0.0
        
        for i in range(len(self.fine_points) - 1): # pour tous les points jusqu'à l'avant dernier
            # Distance entre ce point et le suivant
            dist = self.distances[i] if i < len(self.distances) else 0
            
            # Vitesses aux deux points
            v1 = self.velocities[i]
            v2 = self.velocities[i + 1]
            
            # Temps pour ce segment (moyenne harmonique des vitesses)
            if v1 > 0 and v2 > 0:
                avg_velocity = 2 * v1 * v2 / (v1 + v2)
                segment_time = dist / avg_velocity
            else:
                segment_time = 0
                
            total_time += segment_time

        # Fermer la boucle si trajectoire fermée
        if self.is_closed and len(self.fine_points) > 1:
            dist = self.distances[-1] if self.distances else 0
            v1 = self.velocities[-1]
            v2 = self.velocities[0]
            
            if v1 > 0 and v2 > 0:
                avg_velocity = 2 * v1 * v2 / (v1 + v2)
                segment_time = dist / avg_velocity
                total_time += segment_time
        
        self.lap_time = total_time
        
    def calculate_parameters(self):
        """Surcharge pour calculer les paramètres d'une trajectoire"""
        # on a dejà les paramètres du profil parent, à savoir tangents[], normals[], curvatures[], distances[], length
        super().calculate_parameters()

        """Calcule des paramètres specifiques de la trajectoire: vitesses, temps au tour"""

        # Calculer les vitesses
        self.calculate_velocities()
        
        # Calculer le temps au tour
        self.calculate_lap_time()
        
    def to_dict(self):
        """Convertit la trajectoire en dictionnaire pour sauvegarde"""
        
        profil = super().to_dict()
        def _jsonify(v):
            """Rend un élément numpy sérialisable JSON (list/float/int Python)."""
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, (np.floating, np.integer)):
                return v.item()
            return v

        velocities = self.velocities
        velocities = _jsonify(velocities)
        if isinstance(velocities, list):
            velocities = [_jsonify(v) for v in velocities]

        traj_data = {
            'max_acceleration': _jsonify(self.max_acceleration),
            'max_velocity': _jsonify(self.max_velocity),
            'velocities': velocities,
            'lap_time': _jsonify(self.lap_time)}

        data = {'profil': profil, 'traj_data': traj_data}
        return data
        
    def from_dict(self, data):
        """Charge la trajectoire depuis un dictionnaire"""
        # Nouveau format défini par to_dict : {'profil': {...}, 'traj_data': {...}}
        profil_data = data['profil']
        traj_data = data['traj_data']

        # Recharge la partie Profil
        super().from_dict(profil_data)

        # Recharge les champs spécifiques Trajectoire
        self.max_acceleration = traj_data.get('max_acceleration', self.max_acceleration)
        self.max_velocity = traj_data.get('max_velocity', self.max_velocity)
        self.velocities = traj_data.get('velocities', [])
        self.lap_time = traj_data.get('lap_time', 0.0)

    def _save_trajectory_csv(self, filename):
        """Sauvegarde CSV (actuellement non implémentée)."""
        messagebox.showerror("Erreur", "Module à coder ")
        return False

    def _save_trajectory_json(self, filename):
        """Sauvegarde JSON en utilisant uniquement trajectory.to_dict()."""
        data = self.to_dict()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_trajectory_dialog(self):
        """Ouvre une boite de dialogue et sauvegarde la trajectoire (.csv ou .json)."""
        if len(self.fine_points) == 0:
            messagebox.showerror("Erreur", "Aucune trajectoire à exporter")
            return False

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=str(_dir_files_path()),
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not filename:
            return False

        filename = _force_into_dir_files(filename)

        try:
            if filename.lower().endswith('.json'):
                self._save_trajectory_json(filename)
            elif filename.lower().endswith('.csv'):
                self._save_trajectory_csv(filename)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return False
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}")
            return False

    @classmethod
    def load_trajectory_dialog(cls):
        """Ouvre une boite de dialogue et charge une trajectoire (.json uniquement)."""
        filename = filedialog.askopenfilename(
            initialdir=str(_dir_files_path()),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filename:
            return None

        if not _is_within_dir_files(filename):
            messagebox.showerror("Erreur", f"Lecture interdite hors de '{DIR_FILES}'.")
            return None

        try:
            new_traj = cls()
            if filename.lower().endswith('.json'):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                new_traj.from_dict(data)
                return new_traj
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .json).")
                return None
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
            return None

    def calculate_velocities(self):
        """Calcule les vitesses maximales selon les courbures de la trajectoire"""
        if len(self.fine_points) == 0:
            return
            
        self.velocities = []
        
        # METHODE 1 - COURBURES ONLY, ACCEL TANGENTIELLE INFINIE
        if self.optimization_type == 1:
            print("Optimisation 1")
            self.velocities, self.type_accel = optimize_vitesse(self.curvatures, self.distances, vtop=True,
            gmax=self.max_acceleration, vmax=self.max_velocity, is_closed=self.is_closed)
        
        # METHODE 2 - COURBURES ET DISTANCES, ACCELERATION 1G MAX
        elif self.optimization_type == 2:
            print("Optimisation 2")
            self.velocities, self.type_accel = optimize_vitesse(self.curvatures, self.distances,
            gmax=self.max_acceleration, vmax=self.max_velocity, is_closed=self.is_closed)
        
        # METHODE 3 - COURBURES ET DISTANCES, PUISSANCE LIMITEE 120ch - SUPERSPRINT
        elif self.optimization_type == 3:
            print("Optimisation 3")
            self.velocities, self.type_accel = optimize_vitesse(self.curvatures, self.distances, 
            puissance_massique=120.*735/400, is_closed=self.is_closed)

        # METHODE 4 - COURBURES ET DISTANCES, PUISSANCE LIMITEE 80ch - MAXI SPRINT
        elif self.optimization_type == 4:
            print("Optimisation 4")
            self.velocities, self.type_accel = optimize_vitesse(self.curvatures, self.distances, 
            puissance_massique=80.*735/400, gmax=self.max_acceleration, vmax=self.max_velocity, is_closed=self.is_closed)

        # METHODE 5 - COURBURES ET DISTANCES, PUISSANCE LIMITEE 40ch - JUNIOR SPRINT
        elif self.optimization_type == 5:
            print("Optimisation 5")
            self.velocities, self.type_accel = optimize_vitesse(self.curvatures, self.distances, 
            puissance_massique=40.*735/400, gmax=self.max_acceleration, vmax=self.max_velocity, is_closed=self.is_closed)

def optimize_vitesse(curvatures, distances, puissance_massique=1000.,debug=False, 
                                         vtop=False, gmax=9.81, vmax=41.6, is_closed=True):
    # Optimisation de la vitesse sur un tracé donné. Pas simple.
    # pas mal de travail fait pour que ca marche avec un circuit fermé, ouvert,....

   # On va d'abord limiter la vitesse via une curvature minimale, et calculer les vitesse max par troncon:
    npt=len(curvatures)
    curv_minimum = [gmax / vmax**2  for i in range(npt)]  # soit 5.6 10-3, soit R=177m
    curvatures = np.abs(curvatures) # et utilise ici que des valeurs absolues
    
    # Calculons déjà les vitesses max par troncon.  F = mV²/R = mV²C, donc Vmax = racine (Gmax/C)
    # mais à cette vitesse, la totalité d'ahérence sert à faire tourner, aucune capacité d'accélération tangentielle !
    V_max =(gmax / np.maximum(curv_minimum, curvatures))**0.5
    
    debug=True
                     
    # Il faut maintenant calculer des vitesses, maximisées par V_max, qui soient cohérente 
    # de profils d'accélérations
    # et l'accélération maximale est la puissance massique (W/Kg) divisée par la vitesse tangentielle
    # et il faut partir d'un point qui est un maximum local de courbure, dans lequel on passera 
    # à une vitesse connue (à priori V_max), et à partir duquel on accellérera en sortie, et on freinera avant. 
    # Ensuite il faut vérifier que ca s'est recollé proprement quand ça se rencontre.
    #
    vitesse=np.zeros(len(V_max))
    # 0: vitesse Max , 1: accél 1g, 2: accel. P limited , 3: levée pied, 4: freinage
    type_accel=[0 for i in range(npt)]  
    # Construction de la liste L_Cmax des maximum locaux de courbure
    # en cas de plateau, le premier point du plateau est retenu seulement, 
    L_Cmax=[]
    if not is_closed: L_Cmax.append(0) # pour un circuit ouvert, on ajoute le premier point comme maximum local de courbure
    for i in range(npt): 
        if curvatures[i-2]< curvatures [i-1] >= curvatures [i]: L_Cmax.append(i-1) 
    if debug: print ("max locaux de courbure: ", L_Cmax)

    if vtop:   # si l'option vtop est activée, on retourne simplement les vmax en tout point
        type_accel=[0 for i in range(npt)]
        for i in range(npt): 
            if V_max[i] > V_max[i-1]: type_accel[i]=2 
            if V_max[i] < V_max[i-1]: type_accel[i-1]=4 
        for i in L_Cmax: type_accel[i]=0
        return V_max, type_accel

    # Traitement des phases d'accélération à partir des maximums locaux de courbure
    j=0
    skipped=[]
    for i in L_Cmax:              # pour chaque point ou la courbure est maximale,
        if j>i:
            # on saute le traitement de ce point, on y est déjà passé en accelération issue d'un maximum précédent
            skipped.append(i)
            if debug: print("Saut sur maximum i = ", i)
        else:
            if debug: print("traitement après maximum i = ", i)
            acceleration=True
            # traitons déjà le point i et le point i+1:
            vitesse[i]= V_max[i]      # on passe le point i de courbure max à vitesse max possible, sans accélération
            if i==0 and not is_closed: # sauf dans le cas particulier du premier point d'un circuit ouvert
                vitesse[i]= 0 # on y est à l'arret au départ
                j=0         # et on accélère dès le point de départ, donc mettons j à 0
            elif i!=0 or is_closed: # cas général, après le point i passé à vitesse max sans accélération tangentielle
                vitesse[(i+1)%npt] = vitesse[i] # le point i+1 sera donc atteint à la même vitesse 
                j=(i+1)%npt    # on accelère dès le point suivant, on travaille modulo npoints    
            # elif i==npt-1 and not is_closed: # cas particulier du dernier point d'un circuit ouvert
            #     acceleration=False   # MAIS JE VOIS PAS COMMENT ON PEUT PASSER LA !
            # else:
            #     j=(i+1)%npt  # MAIS JE VOIS PAS COMMENT ON PEUT PASSER LA !
            while acceleration and (is_closed or j!=npt-1):   
            # on boucle sur tout les point suivants tant qu'on peut accélérer et qu'on est pas au 
            # dernier point d'un circuit ouvert
            # on connait la vitesse en j, on veut calculer le type d'acceleration en j et la vitesse en j+1
                if debug: print(f"Debug: j = {j}, acceleration ={acceleration}, courbure={curvatures[j]:.3f}"+
                                f"vitesse={vitesse[j]:.3f}")
                # if not is_closed and j==npt-1: # donc on a fini pour un circuit ouvert
                #     acceleration = False
                if V_max[(j+1)%npt] < vitesse[j]: # si la vitesse max du troncon suivant est inférieure à la vitesse actuelle, on a fini l'accélération
                    acceleration = False
                elif abs(vitesse[j] - V_max[j]) < 1e-6 and abs(V_max[(j+1)%npt] - V_max[j]) < 1e-6:
                    acceleration = True          # ici on est en fait sur un plateau de courbure à Vmax,
                    vitesse[(j+1)%npt] = V_max[(j+1)%npt]    # donc on passe le point suivant à Vmax
                    type_accel[j] = 0
                else:
                    GamaN= curvatures[j] * vitesse [j]**2 -0.000001   # il a besoin d'une accélération normale pour tourner
                    GamaT= (gmax**2 - GamaN**2)**0.5   
                    if debug:print(f"    GamaN={GamaN:.3f}, Gama_T={GamaT:.3f}, Gmax={gmax:.3f}")
                    if GamaT < (puissance_massique / max(vitesse[j], 1e-6)):  # ici la capacité d'accélération tangentielle GamaT
                        type_accel[j]=1                                             # n'est pas limitée par la puissance disponible
                        v_possible = (vitesse[j]**2 + 2.* GamaT * distances[j])**0.5  # et elle peut générer ce dV tangentiel
                    else:                                        # ici on est limité par la puissance disponible, 
                        type_accel[j]=2                          # qui peut générer ce dV tangentiel
                        v_possible = (vitesse[j]**3 + 3.*puissance_massique * distances[j])**(1/3) # Calcul nouvelle vitesse possible en puissance max
                    if (v_possible>V_max[(j+1)%npt]):  
                        type_accel[j]=3                      # il faut donc lever le pied,
                        vitesse [(j+1)%npt] = V_max[(j+1)%npt]       # car la vitesse max du troncon suivant est atteinte
                    else:
                        vitesse [(j+1)%npt] = v_possible             # sinon on accelère de ce qu'on peut
                if abs(vitesse[(j+1)%npt] - vitesse[j]) < 1e-6: type_accel[j]=0
                if debug:print(f"au point {j} type_accel = {type_accel[j]}, et au point {(j+1)%npt}, "+
                        f"on retient la vitesse = {vitesse[(j+1)%npt]:.3f}")
                j=(j+1)%npt
    if debug: print ("fin traitement accelleration, i , j = ", i, j)

    # il est possible qu'on ait continué d'acélérer pendant des maximum locaux de courbure,
    # qu'il faut donc éliminer de la liste L_Cmax. Ce sont les points entre i+1 et j
    if debug: print ("eventuel max locaux de courbure passée en accélération:", skipped)
    if len(skipped) > 0: 
        L_Cmax= [x for x in L_Cmax if x not in skipped]
        if debug: print ("max locaux de courbure restant:", L_Cmax)

    # Traitement des phase de freinage, qu'on traine en remontant le tracé à partir du max de courbure, donc encore dans un sens 
    # de courbure décroissante. C'est moins simple.
    if not is_closed: L_Cmax=L_Cmax[1:] # pour un circuit ouvert, on supprime le premier point de la liste
    for i in L_Cmax:
        freinage=True
        j=i-1      # pas besoin de modulo ici, Python n'a pas de problème avec les indices négatifs
        if debug: print("traitement avant maximum i = ", i)
        while freinage:
            # il faut trouver la vitesse du point précédent vitesse[j]. C'est un peu plus subtil, car
            # ça sera la vitesse V qui annulera la fonction ecart suivante:
            
            def ecart(V, Vp1, courbure, distance, G_max) :       
                GamaN= courbure * V**2 -0.000001      # A une vitesse V, il y a besoin d'une accélération normale pour tourner
                if (abs(GamaN)>G_max): print("Warning: exces de GamaN")
                GamaT= (G_max**2 - GamaN**2)**0.5     # il reste une capacité de freinage tangentielle GamaT
                dV = - GamaT * distances[j] / V       # qui peut générer ce dV
                return Vp1 - (V+dV)                   # et il faudra que ce dV ajouté à V donne bien a vitesse du point suivant
            
            # Recherche du zéro de la fonction ecart par méthode itérative stupide version LG qui marche très bien
            erreur = 1. ; vmin = 0.  ; vmax = V_max[j] ; boucle=0 ; V = 0.5 *(vmin+vmax)
            while (abs(erreur) >0.001*abs(V)) and (boucle<100) :
                boucle+=1
                V = 0.5 *(vmin+vmax)
                if ecart(V, vitesse[j+1], curvatures[j], distances[j], gmax)<0. :
                    vmax=V
                else:
                    vmin=V
                erreur = vmax-vmin     
        
            vitesse [j] = V      
            type_accel[j]=4
            if debug:print("Freinage au point ", j, "Vitesse = ", vitesse[j])          
            if (curvatures[j-1] > curvatures[j]): freinage =False   # en remontant au point d'avant, si la courbure remonte, on est au début du freinage
            j=j-1
    if debug: print("fin traitement freinage")   
    
    # Si ce programme a bien marché, les vitesses sont bien renseignées sur tout les troncons, ce qu'on vérifie:
    if is_closed: 
        mask = np.abs(vitesse[1:]) < 1e-6  # booléen : True si "presque nul"
    else:
        mask = np.abs(vitesse) < 1e-6  # booléen : True si "presque nul"
    if np.any(mask): print("ATTENTION: DES TRONCONS VITESSE NULLE: ", np.where(mask)[0])
    
    return vitesse, type_accel
