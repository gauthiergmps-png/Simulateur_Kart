"""
Gestionnaire de fichiers pour les circuits et trajectoires
Permet de sauvegarder/charger des circuits et d'exporter des trajectoires
au format CSV lisible par Excel
"""

import json
import csv
import os
from pathlib import Path
from tkinter import filedialog, messagebox
from .circuit_et_trajectoire import Circuit, Trajectoire

DIR_FILES="C_et_T_files"

class FileManager:
    """Classe pour gérer les opérations de fichiers (sauvegarde, chargement, export)"""
    
    def __init__(self):
        """Initialise le gestionnaire de fichiers"""
        pass

    def _dir_files_path(self) -> Path:
        """Retourne le dossier de travail pour les fichiers (toujours DIR_FILES)."""
        base_dir = Path(__file__).resolve().parent.parent  # .../C_et_T
        p = base_dir / DIR_FILES
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _is_within_dir_files(self, filepath: str) -> bool:
        """Vrai si filepath est dans DIR_FILES (après résolution)."""
        try:
            file_path = Path(filepath).resolve()
            dir_path = self._dir_files_path().resolve()
            file_path.relative_to(dir_path)
            return True
        except Exception:
            return False

    def _force_into_dir_files(self, filepath: str) -> str:
        """Force un chemin vers DIR_FILES en gardant uniquement le basename."""
        filename = os.path.basename(filepath)
        return str(self._dir_files_path() / filename)
    
    def save_circuit(self, circuit):
        """
        Sauvegarde le circuit dans un fichier .csv ou .json
        
        Args:
            circuit: Instance de Circuit à sauvegarder
            
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        if len(circuit.raw_points) == 0:
            messagebox.showerror("Erreur", "Aucun circuit à sauvegarder")
            return False
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=str(self._dir_files_path()),
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return False

        # On écrit toujours dans DIR_FILES
        filename = self._force_into_dir_files(filename)
            
        try:
            if filename.lower().endswith('.json'):
                self._save_circuit_json(circuit, filename)
            elif filename.lower().endswith('.csv'):
                self._save_circuit_csv(circuit, filename)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return False
            return True
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
            return False

    def _save_circuit_csv(self, circuit, filename):
        """
        Sauvegarde le circuit au format CSV avec métadonnées
        
        Args:
            circuit: Instance de Circuit
            filename: Chemin du fichier de destination
        """
        messagebox.showerror("Erreur", "Module à coder ")
        return False    
        
    def _save_circuit_json(self, circuit, filename):
        """
        Sauvegarde le circuit au format JSON en utilisant uniquement circuit.to_dict().

        Args:
            circuit: Instance de Circuit
            filename: Chemin du fichier de destination
        """
        data = circuit.to_dict()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_circuit(self):
        """
        Charge un circuit depuis un fichier CSV ou JSON
        
        Returns:
            Circuit: Nouvelle instance de Circuit chargée, ou None si échec
        """
        filename = filedialog.askopenfilename(
            initialdir=str(self._dir_files_path()),
            filetypes=[("All files", "*.*")]
        )
        
        if not filename:
            return None

        # On lit toujours dans DIR_FILES (sinon on refuse)
        if not self._is_within_dir_files(filename):
            messagebox.showerror("Erreur", f"Lecture interdite hors de '{DIR_FILES}'.")
            return None
            
        try:
            new_circuit = Circuit()
            
            if filename.endswith('.csv'):
                self._load_circuit_csv(new_circuit, filename)
            elif filename.endswith('.json'):
                self._load_circuit_json(new_circuit, filename)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return None
            
            return new_circuit
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
            return None
    
    def _load_circuit_json(self, circuit, filename):
        """
        Charge un circuit depuis un fichier JSON en utilisant circuit.from_dict().
        
        Args:
            circuit: Instance de Circuit à remplir
            filename: Chemin du fichier source
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        circuit.from_dict(data)
        
    def _load_circuit_csv(self, circuit, filename):
        """
        Charge un circuit depuis un fichier CSV
        
        Args:
            circuit: Instance de Circuit à remplir
            filename: Chemin du fichier source        
            """
        messagebox.showerror("Erreur", "Module à coder ")
        return False    

    def load_trajectory(self):
        """
        Charge une trajectoire depuis un fichier JSON (nouveau format) ou CSV (non supporté ici).
        
        Returns:
            Trajectoire: Nouvelle instance de Trajectoire chargée, ou None si échec
        """
        filename = filedialog.askopenfilename(
            initialdir=str(self._dir_files_path()),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filename:
            return None

        if not self._is_within_dir_files(filename):
            messagebox.showerror("Erreur", f"Lecture interdite hors de '{DIR_FILES}'.")
            return None

        try:
            if filename.endswith('.json'):
                new_traj = Trajectoire()
                self._load_trajectory_json(new_traj, filename)
                messagebox.showinfo("Succès", f"Trajectoire chargée depuis {filename}")
                return new_traj
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .json).")
                return None
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
            return None

    def _load_trajectory_json(self, trajectory, filename):
        """
        Charge une trajectoire depuis un fichier JSON en appelant trajectory.from_dict().
        
        Args:
            trajectory: Instance de Trajectoire à remplir
            filename: Chemin du fichier source
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        trajectory.from_dict(data)
    
    def save_trajectory(self, trajectory):
        """
        Exporte la trajectoire dans un fichier .json ou .csv avec toutes les données
        
        Args:
            trajectory: Instance de Trajectory à exporter
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        if len(trajectory.fine_points) == 0:
            messagebox.showerror("Erreur", "Aucune trajectoire à exporter")
            return False
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=str(self._dir_files_path()),
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")])
        
        if not filename:
            return False

        # On écrit toujours dans DIR_FILES
        filename = self._force_into_dir_files(filename)
            
        try:
            if filename.lower().endswith('.json'):
                self._save_trajectory_json(trajectory, filename)
            elif filename.lower().endswith('.csv'):
                self._save_trajectory_csv(trajectory, filename)
            else:
                messagebox.showerror("Erreur", "Extension de fichier non supportée (utiliser .csv ou .json).")
                return False

            return True
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}")
            return False
    
    def _save_trajectory_csv(self, trajectory, filename):
        """
        Exporte la trajectoire au format CSV avec toutes les données
        
        Args:
            trajectory: Instance de Trajectory
            filename: Chemin du fichier de destination
        """
        messagebox.showerror("Erreur", "Module à coder ")
        # return False    
        # with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        #     writer = csv.writer(csvfile)
            
        #     # En-tête avec métadonnées
        #     writer.writerow(['# Trajectory Data'])
        #     writer.writerow(['# Closed:', trajectory.is_closed])
        #     writer.writerow(['# Number of points:', len(trajectory.fine_points)])
        #     writer.writerow(['# Has velocities:', len(trajectory.velocities) > 0])
        #     writer.writerow(['# Has accelerations:', len(trajectory.type_accel) > 0])
        #     writer.writerow([])  # Ligne vide
            
        #     # En-têtes des colonnes
        #     headers = ['Point_Index', 'X', 'Y']
            
        #     # Ajouter les colonnes disponibles
        #     if hasattr(trajectory, 'normals') and len(trajectory.normals) > 0:
        #         headers.extend(['Normal_X', 'Normal_Y'])
            
        #     if hasattr(trajectory, 'curvatures') and len(trajectory.curvatures) > 0:
        #         headers.append('Curvature')
            
        #     if len(trajectory.velocities) > 0:
        #         headers.append('Velocity')
            
        #     if len(trajectory.type_accel) > 0:
        #         headers.append('Accel_Type')
            
        #     writer.writerow(headers)
            
        #     # Données des points
        #     for i, point in enumerate(trajectory.fine_points):
        #         row = [i+1, point[0], point[1]]
                
        #         # Ajouter les données supplémentaires si disponibles
        #         if hasattr(trajectory, 'normals') and len(trajectory.normals) > 0 and i < len(trajectory.normals):
        #             normal = trajectory.normals[i]
        #             row.extend([normal[0], normal[1]])
        #         elif 'Normal_X' in headers:
        #             row.extend(['', ''])
                
        #         if hasattr(trajectory, 'curvatures') and len(trajectory.curvatures) > 0 and i < len(trajectory.curvatures):
        #             row.append(trajectory.curvatures[i])
        #         elif 'Curvature' in headers:
        #             row.append('')
                
        #         if len(trajectory.velocities) > 0 and i < len(trajectory.velocities):
        #             row.append(trajectory.velocities[i])
        #         elif 'Velocity' in headers:
        #             row.append('')
                
        #         if len(trajectory.type_accel) > 0 and i < len(trajectory.type_accel):
        #             # Convertir le type d'accélération en texte lisible
        #             accel_types = {
        #                 0: 'Constant',
        #                 1: 'Acceleration',
        #                 2: 'Power_Limited',
        #                 3: 'Coast',
        #                 4: 'Braking'
        #             }
        #             accel_type = accel_types.get(trajectory.type_accel[i], 'Unknown')
        #             row.append(accel_type)
        #         elif 'Accel_Type' in headers:
        #             row.append('')
                
        #         writer.writerow(row)

    def _save_trajectory_json(self, trajectory, filename):
        """
        Sauvegarde la trajectoire au format JSON en utilisant uniquement trajectory.to_dict().
        
        Args:
            trajectory: Instance de Trajectoire
            filename: Chemin du fichier de destination
        """
        data = trajectory.to_dict()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
