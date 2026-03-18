import numpy as np
from scipy.interpolate import splprep, splev
import math
import json

class Profil:
    """ Classe parente pour gérer les profils (circuits et trajectoires) pour lesquels:
        - Un profil est défini par des "raw points" à saisir par l'utilisateur, qu'on peut modifier après saisie,
        - qui peut être fermé ou ouvert,
        - à partir desquels on calcule un profil fin par spline,
        - et sur lequel on calcule des paramètres comme distance ou courbures
    """
    
    def __init__(self, name="Profil", is_closed=True, n_fine_points=100):
        """ 
        Initialise un profil
        
        Args:
            name (str): Nom du profil
            is_closed (bool): Si le profil est fermé (circuit) ou ouvert (trajectoire)
            n_fine_points (int): Nombre de points pour le profil fin
        """
        self.name = name
        self.is_closed = is_closed
        self.n_fine_points = n_fine_points

        self.input_mode = False   # Mode saisie actif ou non

        """initialise les points de saisie, donc le profil fin et ses paramètres"""
        self.raw_points=[]
        self.reset_fine_profile()

    def reset_raw_points(self, forcage=False):
        """Efface tous les points de saisie (si pas verrouillé), donc le profil fin et ses paramètres"""
        if self.input_mode or forcage:
            self.raw_points=[]
            self.reset_fine_profile()
        else:
            raise RuntimeError("Impossible de modifier un profil verrouillé")
        
    def insert_point(self, x, y, idx):
        """Ajoute un point au profil grossier après l'index idx(seulement si pas verrouillé)"""
        if self.input_mode:
            if idx is None: idx=0
            self.raw_points.insert(idx+1, [x, y])
        else:
            raise RuntimeError("Impossible d'ajouter des points à un profil verrouillé")

    def remove_point(self, idx):
        """Supprime le point d'index idx du profil (logique métier uniquement)"""
        if self.input_mode and self.raw_points and 0 <= idx < len(self.raw_points):
            del self.raw_points[idx]
            self.reset_fine_profile()
            return True
        elif not self.input_mode:
            raise RuntimeError("Impossible de modifier un profil verrouillé")
        elif not 0 <= idx < len(self.raw_points):
            raise RuntimeError("Erreur d'idx dans remove_point")
        return False
        
    def start_input(self):
        """Déverrouille le profil (permet la modification) et réinitialise le profil fin"""
        self.input_mode = True
        self.reset_fine_profile()

    def stop_input(self):
        """Termine la saisie du profil, verrouille le profil et calcule le profil fin (logique métier uniquement)"""
        self.input_mode = False
        if self.is_ready_for_calculation():
            self.calculate_fine_profile()
        
    def is_ready_for_calculation(self):
        """Vérifie si le profil a assez de points pour être calculé"""
        if self.is_closed:
            return len(self.raw_points) >= 4  # Circuit fermé : besoin de 4 points
        else:
            return len(self.raw_points) >= 2  # Trajectoire ouverte : besoin de 2 points

    def reset_fine_profile(self):
        """Réinitialise le profil fin et ses paramètres"""
        self.fine_points = []
        self.tangents = []
        self.normals = []
        self.curvatures = []
        self.length = 0.0
        self.distances = []
    
    def closest_raw_point(self, x, y, threshold=10):
        """Trouve l'index du raw point le plus proche des coordonnées (x, y)"""
        closest_index = None
        if len(self.raw_points) == 0:
            return closest_index
            
        min_distance = float('inf')
        for i, point in enumerate(self.raw_points):
            # on utilise la distance issue de la norme 1, c'est plus rapide que la norme 2
            distance = abs(x - point[0]) + abs(y - point[1])
            if distance < min_distance and distance < threshold:
                min_distance = distance
                closest_index = i
        return closest_index

    def closest_fine_point(self, x, y, threshold=10):
        """Trouve l'index du point fin le plus proche des coordonnées (x, y)"""
        #         et en plus simple, s'inspirer de:
        #         distances = [np.linalg.norm(point - circuit_point) 
        #         for circuit_point in self.fine_points]
        #         closest_idx = np.argmin(distances)

        closest_index = None
        if len(self.fine_points) == 0:
            return closest_index

        min_distance = float('inf')
        for i, point in enumerate(self.fine_points):
            # on utilise la distance issue de la norme 1, c'est plus rapide que la norme 2
            distance = abs(x - point[0]) + abs(y - point[1])
            if distance < min_distance and distance < threshold:
                min_distance = distance
                closest_index = i
        return closest_index
            
    def calculate_fine_profile(self):
        """Calcule le profil fin par spline à partir des points bruts"""
        if not self.is_ready_for_calculation():
            raise ValueError(f"Pas assez de points pour calculer le profil fin. "
                           f"Minimum requis: {4 if self.is_closed else 2}")
            
        points = np.array(self.raw_points)
        
        try:
            if self.is_closed and len(points) >= 4:
                # Profil fermé - ajouter le premier point à la fin pour assurer la continuité
                points_closed = np.vstack([points, points[0]])
                # Pour les splines périodiques, utiliser k=3 (cubique) mais s'assurer qu'il y a assez de points
                k = min(3, len(points_closed) - 1)
                tck, u = splprep([points_closed[:, 0], points_closed[:, 1]], s=0, per=True, k=k)
                u_new = np.linspace(0, 1, self.n_fine_points, endpoint=False)
                self.fine_points = np.array(splev(u_new, tck)).T
            else:
                # Profil ouvert - gérer le cas avec peu de points
                if len(points) < 4:
                    # Pour moins de 4 points, utiliser une interpolation linéaire
                    if len(points) == 2:
                        # Deux points : ligne droite
                        t = np.linspace(0, 1, self.n_fine_points)
                        x = points[0][0] + t * (points[1][0] - points[0][0])
                        y = points[0][1] + t * (points[1][1] - points[0][1])
                        self.fine_points = np.column_stack([x, y])
                    elif len(points) == 3:
                        # Trois points : interpolation quadratique
                        t = np.linspace(0, 1, self.n_fine_points)
                        # Formule d'interpolation quadratique
                        x = (1-t)**2 * points[0][0] + 2*t*(1-t) * points[1][0] + t**2 * points[2][0]
                        y = (1-t)**2 * points[0][1] + 2*t*(1-t) * points[1][1] + t**2 * points[2][1]
                        self.fine_points = np.column_stack([x, y])
                    else:
                        raise ValueError("Nombre de points insuffisant pour l'interpolation")
                else:
                    # 4 points ou plus : utiliser les splines
                    tck, u = splprep([points[:, 0], points[:, 1]], s=0, k=min(3, len(points)-1))
                    u_new = np.linspace(0, 1, self.n_fine_points, endpoint=True)
                    self.fine_points = np.array(splev(u_new, tck)).T
                
            # Ajuster les points de départ et d'arrivée pour les profils ouverts
            if not self.is_closed and len(self.fine_points) > 0:
                # Premier point
                first_original = points[0]
                first_calculated = self.fine_points[0]
                if np.linalg.norm(first_original - first_calculated) > 0.1:
                    self.fine_points[0] = first_original
                
                # Dernier point
                last_original = points[-1]
                last_calculated = self.fine_points[-1]
                if np.linalg.norm(last_original - last_calculated) > 0.1:
                    self.fine_points[-1] = last_original
                    
        except Exception as e:
            raise RuntimeError(f"Erreur lors du calcul des splines: {e}")
        
        # Calculer les paramètres du profil fin ??
        # Note: calculate_parameters() est appelée par les sous-classes si nécessaire

    def calculate_parameters(self):
        """Calcule tous les paramètres du profil fin"""
        # tangents[]: vecteurs tangents
        # normals[]: vecteurs normaux
        # curvatures[]: courbures (signés si possible, A FAIRE)
        # distances[]: distances entre le point courant et son suivant
        # length: longueur totale

        if len(self.fine_points) < 3:
            return
            
        points = self.fine_points
        n_points = len(points)
        
        # Vider les listes existantes
        self.tangents.clear()
        self.normals.clear()
        self.curvatures.clear()
        self.distances.clear()
        self.length = 0.0
        
        for i in range(n_points):
            # Vecteur tangent
            if i == 0:
                if self.is_closed:
                    tangent = points[1] - points[-1]
                else:
                    tangent = points[1] - points[0]
            elif i == n_points - 1:
                if self.is_closed:
                    tangent = points[0] - points[-2]
                else:
                    tangent = points[-1] - points[-2]
            else:
                tangent = points[i+1] - points[i-1]
                
            # Normalisation
            tangent_norm = np.linalg.norm(tangent)
            if tangent_norm > 0:
                tangent = tangent / tangent_norm
                
            self.tangents.append(tangent)
            
            # Vecteur normal (rotation de 90°)
            normal = np.array([-tangent[1], tangent[0]])
            
            # Ajuster la direction du vecteur normal pour les profils ouverts
            if not self.is_closed and (i == 0 or i == n_points - 1):
                if i == 0 and n_points > 1:
                    next_normal = np.array([-(points[2] - points[1])[1], (points[2] - points[1])[0]])
                    next_normal = next_normal / np.linalg.norm(next_normal)
                    if np.dot(normal, next_normal) < 0:
                        normal = -normal
                elif i == n_points - 1 and n_points > 1:
                    prev_normal = np.array([-(points[-1] - points[-2])[1], (points[-1] - points[-2])[0]])
                    prev_normal = prev_normal / np.linalg.norm(prev_normal)
                    if np.dot(normal, prev_normal) < 0:
                        normal = -normal
                        
            self.normals.append(normal)

            def calculate_curv_and_dist(p1, p2, p3):
                v1 = p2 - p1
                v2 = p3 - p2
                dist = np.linalg.norm(p3 - p2)
                # Produit vectoriel et produit scalaire
                cross_product = v1[0] * v2[1] - v1[1] * v2[0]
                dot_product = np.dot(v1, v2)
                if abs(dot_product) > 1e-10:
                    return math.atan2(abs(cross_product), dot_product) / dist, dist 
                else:
                    return math.pi/2 / dist, dist 
                           
            # Calcul de la courbure et de la distance entre le point courant et son suivant
            if i > 0 and i < n_points - 1: # pour les points intermédiaires
                curvature, dist = calculate_curv_and_dist(points[i-1], points[i], points[i+1])
            elif i==0:
                if self.is_closed: # pour le premier point si profil fermé
                    curvature, dist = calculate_curv_and_dist(points[-1], points[0], points[1])
                else:
                    curvature=0    # curvature nulle pour le premier point d'un circuit ouvert
                    dist = np.linalg.norm(points[0] - points[1])
            elif i==n_points-1: # pour le dernier point , on garde la courbure de l'avant dernier
                if self.is_closed:
                    curvature, dist = calculate_curv_and_dist(points[-2], points[-1], points[0])
                else:
                    dist=0.
            else: #on garde la courbure de l'avant dernier pour un circuit ouvert
                dist=0
            self.distances.append(dist)
            self.length += dist
            self.curvatures.append(curvature)
        
    def to_dict(self):
        """Convertit le profil en dictionnaire pour sauvegarde"""
        data = {
            'name': self.name, 
            'is_closed': self.is_closed,
            'n_fine_points': self.n_fine_points,
            'raw_points': self.raw_points,
            'fine_points': self.fine_points.tolist() if len(self.fine_points) > 0 else [],
            'parameters': {}
        }
        parameters = {
            'tangents': self.tangents,
            'normals': self.normals,
            'curvatures': self.curvatures,
            'distances': self.distances,
            'length': self.length
        }
        data['parameters'] = parameters
        return data
        
    def from_dict(self, data):
        """Charge le profil depuis un dictionnaire (format issu de to_dict / to_json)."""
        self.name = data.get('name', self.name)
        self.is_closed = data.get('is_closed', self.is_closed)
        self.n_fine_points = data.get('n_fine_points', self.n_fine_points)
        self.raw_points = data.get('raw_points', [])

        # Charger éventuellement le profil fin et ses paramètres (si fournis)
        fine_points = data.get('fine_points', [])
        if fine_points:
            self.fine_points = np.array(fine_points, dtype=float)
        else:
            self.fine_points = np.array([])

        parameters = data.get('parameters', {}) or {}
        self.tangents = parameters.get('tangents', [])
        self.normals = parameters.get('normals', [])
        self.curvatures = parameters.get('curvatures', [])
        self.distances = parameters.get('distances', [])
        self.length = parameters.get('length', 0.0)

        # Fallback : recalculer le profil fin si nécessaire (ancien format / dict incomplet)
        if (not fine_points) and len(self.raw_points) > 0:
            self.calculate_fine_profile()
