"""Explorateur Tkinter pour un Q-table (dimension d'état 3, 10x10x10).

Ce programme permet d'afficher le contenu d'un fichier Q enregistré dans le dossier Records/.
L'affichage est organisé en trois zones :
- une zone commande,
- une zone info,
- une zone affichage.

Dans la zone commande :
- un bouton "LOAD Q" permet de lire un fichier dans le dossier Records/ ;
- un groupe de 3 boutons radio permet de choisir la dimension de coupe (0, 1 ou 2) ;
- une commande (+ / -) permet de choisir la hauteur de coupe (0..9), affichée dans la zone info ;
- un groupe radio "type d'affichage" est prévu, une seule option est fonctionnelle dans cette première version :
  "état de visite".

Dans la zone affichage, on visualise un tableau carré de 10x10 :
- chaque case correspond à un état (d0,d1,d2) selon la dimension de coupe choisie :
  - si dim=0 : état (cut, x, y)
  - si dim=1 : état (x, cut, y)
  - si dim=2 : état (x, y, cut)
- la case est colorée en noir si l'état n'a jamais été visité,
  ou en vert clair si l'état a été visité ;
- au centre de chaque case, on affiche la valeur moyenne de Q sur toutes les actions possibles pour cet état.
"""

import os
import pickle
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np


RECORDS_DIR = os.path.join(os.path.dirname(__file__), "Records")


class QExplorerApp:
    """Application Tkinter pour explorer un Q-table de dimension d'état 3 (10x10x10)."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Explorateur de Q-table (dimension 3)")
        # On agrandit un peu la fenêtre pour mieux voir les légendes
        self.root.geometry("900x700")

        # Données Q chargées
        self.Q: dict[str, dict[int, float]] | None = None
        self.state_dim = 3
        self.n_bins = 10
        self.n_actions: int | None = None

        # Paramètres de visualisation
        self.slice_dim = tk.IntVar(value=0)   # dimension de coupe (0,1,2)
        self.slice_value = tk.IntVar(value=0) # valeur de coupe (0..9)

        # Construction de l'UI
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Construction interface
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        # Frames principales
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Zone commande (gauche)
        self._build_command_panel(left_frame)

        # Zone info (en bas à gauche)
        info_frame = tk.Frame(left_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        self.info_label = tk.Label(info_frame, text="Aucun fichier Q chargé.")
        self.info_label.pack()

        # Zone affichage (droite)
        self.canvas_size = 600
        self.grid_canvas = tk.Canvas(right_frame, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.grid_canvas.pack(fill=tk.BOTH, expand=True)

    def _build_command_panel(self, parent: tk.Frame) -> None:
        # Bouton LOAD Q
        load_frame = tk.Frame(parent)
        load_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Button(load_frame, text="LOAD Q", command=self.load_q_from_file).pack(fill=tk.X)

        # Noms symboliques des dimensions (0: Y, 1: lacet, 2: oméga)
        self.dim_names = ["Y", "lacet", "oméga"]

        # Choix dimension de coupe
        dim_frame = tk.LabelFrame(parent, text="Dimension de coupe")
        dim_frame.pack(fill=tk.X, pady=(0, 10))
        for d in range(self.state_dim):
            tk.Radiobutton(
                dim_frame,
                text=f"dim {d} ({self.dim_names[d]})",
                variable=self.slice_dim,
                value=d,
                command=self.update_display,
            ).pack(anchor="w")

        # Hauteur de coupe (0..9)
        slice_frame = tk.LabelFrame(parent, text="Hauteur de coupe (0-9)")
        slice_frame.pack(fill=tk.X, pady=(0, 10))

        value_label = tk.Label(slice_frame, textvariable=self.slice_value, width=3)
        value_label.pack(side=tk.LEFT, padx=5)

        tk.Button(slice_frame, text="-", width=3, command=self.decrement_slice).pack(side=tk.LEFT, padx=2)
        tk.Button(slice_frame, text="+", width=3, command=self.increment_slice).pack(side=tk.LEFT, padx=2)

        # Choix type affichage (pour l'instant un seul)
        mode_frame = tk.LabelFrame(parent, text="Type d'affichage")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(mode_frame, text="état de visite (moyenne Q-actions)").pack(anchor="w")

    # ------------------------------------------------------------------ #
    # Gestion Q
    # ------------------------------------------------------------------ #
    def load_q_from_file(self) -> None:
        """Ouvre un fichier Q (pickle) dans Records/ et le charge."""
        initial_dir = RECORDS_DIR if os.path.isdir(RECORDS_DIR) else os.path.dirname(__file__)
        filepath = filedialog.askopenfilename(
            title="Choisir un fichier Q_recorded",
            initialdir=initial_dir,
            filetypes=[("Fichiers pickle", "*.pkl *.pickle *"), ("Tous fichiers", "*.*")],
        )
        if not filepath:
            return

        try:
            with open(filepath, "rb") as f:
                Q = pickle.load(f)
        except Exception as e:
            messagebox.showerror("Erreur de chargement", f"Impossible de charger le fichier Q:\n{e}")
            return

        if not isinstance(Q, dict):
            messagebox.showerror("Format invalide", "Le fichier Q ne contient pas un dictionnaire.")
            return

        # On suppose Q[state_str][action] = valeur
        self.Q = Q
        # Déterminer n_actions à partir d'un état quelconque
        sample_state = next(iter(Q.values()), None)
        if isinstance(sample_state, dict) and sample_state:
            self.n_actions = len(sample_state)
        else:
            self.n_actions = 0

        # Info sur la taille de Q
        self.update_info_label(filepath)
        self.update_display()

    def update_info_label(self, filepath: str) -> None:
        if self.Q is None:
            self.info_label.config(text="Aucun fichier Q chargé.")
            return
        n_states = len(self.Q)
        txt = (
            f"Fichier Q : {os.path.basename(filepath)}\n"
            f"Nombre d'états dans Q : {n_states}\n"
            f"Dimension des états : {self.state_dim} (attendu: 3)\n"
            f"Nombre d'actions : {self.n_actions}"
        )
        self.info_label.config(text=txt)

    # ------------------------------------------------------------------ #
    # Interaction commande coupe
    # ------------------------------------------------------------------ #
    def increment_slice(self) -> None:
        v = self.slice_value.get()
        if v < self.n_bins - 1:
            self.slice_value.set(v + 1)
            self.update_display()

    def decrement_slice(self) -> None:
        v = self.slice_value.get()
        if v > 0:
            self.slice_value.set(v - 1)
            self.update_display()

    # ------------------------------------------------------------------ #
    # Rendu de la grille
    # ------------------------------------------------------------------ #
    def update_display(self) -> None:
        """Redessine la grille 10x10 en fonction de la coupe choisie."""
        self.grid_canvas.delete("all")
        if self.Q is None:
            return

        dim = self.slice_dim.get()
        cut = self.slice_value.get()

        # On laisse une marge pour dessiner les légendes (axes 0..9 et texte des dimensions)
        margin = 40
        grid_size = self.canvas_size - margin - 10  # petite marge en bas/droite
        cell_size = grid_size / self.n_bins
        x_offset = margin
        y_offset = margin

        # Déterminer quelles dimensions sont affichées sur X et Y
        if dim == 0:
            dim_x, dim_y = 1, 2
        elif dim == 1:
            dim_x, dim_y = 0, 2
        else:  # dim == 2
            dim_x, dim_y = 0, 1

        for i in range(self.n_bins):      # axe X de la grille
            for j in range(self.n_bins):  # axe Y de la grille
                # Construire l'état (d0,d1,d2) en fonction de dim et cut
                if dim == 0:
                    state_indices = (cut, i, j)
                elif dim == 1:
                    state_indices = (i, cut, j)
                else:  # dim == 2
                    state_indices = (i, j, cut)

                state_str = "".join(str(k) for k in state_indices)
                q_entry = self.Q.get(state_str) if self.Q is not None else None

                # Déterminer si l'état a été "visité" :
                # Q est initialisé à 0 pour toutes les actions → un état est considéré comme visité
                # si au moins une valeur Q(state, action) est différente de 0.
                visited = False
                avg_q = 0.0
                if isinstance(q_entry, dict) and self.n_actions:
                    values = list(q_entry.values())
                    if any(v != 0.0 for v in values):
                        visited = True
                    if values:
                        avg_q = float(np.mean(values))

                # Couleur : noir si jamais visité, vert clair sinon
                fill_color = "#000000" if not visited else "#90EE90"

                x0 = x_offset + i * cell_size
                y0 = y_offset + j * cell_size
                x1 = x0 + cell_size
                y1 = y0 + cell_size

                # Dessin de la case
                self.grid_canvas.create_rectangle(x0, y0, x1, y1, fill=fill_color, outline="white")

                # Texte : valeur moyenne de Q
                self.grid_canvas.create_text(
                    (x0 + x1) / 2,
                    (y0 + y1) / 2,
                    text=f"{avg_q:.2f}",
                    fill="black" if visited else "white",
                    font=("Arial", 8),
                )

        # Légendes des axes (valeurs 0..9)
        # Axe X (en bas)
        for i in range(self.n_bins):
            x = x_offset + i * cell_size + cell_size / 2
            y = y_offset + grid_size + 12
            self.grid_canvas.create_text(x, y, text=str(i), font=("Arial", 8))

        # Axe Y (à gauche)
        for j in range(self.n_bins):
            x = x_offset - 12
            y = y_offset + j * cell_size + cell_size / 2
            self.grid_canvas.create_text(x, y, text=str(j), font=("Arial", 8))

        # Légende des dimensions affichées (avec noms physiques)
        legend_text = (
            f"Coupe sur dim {dim} ({self.dim_names[dim]}) = {cut}  |  "
            f"Axe X: dim {dim_x} ({self.dim_names[dim_x]})  |  "
            f"Axe Y: dim {dim_y} ({self.dim_names[dim_y]})"
        )
        self.grid_canvas.create_text(
            self.canvas_size / 2,
            15,
            text=legend_text,
            font=("Arial", 10, "bold"),
        )


def main() -> None:
    root = tk.Tk()
    app = QExplorerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()