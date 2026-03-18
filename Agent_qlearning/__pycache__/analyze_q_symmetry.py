import os
import pickle
import json

BASE_DIR = os.path.dirname(__file__)

# Fichiers Q à comparer (version gauche et droite)
Q_LEFT_PATH = os.path.join(BASE_DIR, "Records", "Q_recorded_L")
Q_RIGHT_PATH = os.path.join(BASE_DIR, "Records", "Q_recorded_R")

# Fichiers de commandes à comparer (version gauche et droite)
CMD_LEFT_PATH = os.path.join(BASE_DIR, "Records", "commandes_L.txt")
CMD_RIGHT_PATH = os.path.join(BASE_DIR, "Records", "commandes_R.txt")


def mirror_state_str(s: str) -> str:
    """Retourne l'état miroir en inversant les 3 chiffres de 0..8 -> 8..0."""
    return "".join(str(8 - int(ch)) for ch in s)


# Actions de l'agent kart (ordre dans 0-kart_qulearning.py)
volant_angles = [-10, -5, 0, 5, 10]
# Miroir d'action : indices 0..4 ↔ actions de signe opposé
mirror_action = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0}


def analyze_Q_symmetry() -> None:
    """Analyse la symétrie entre Q_left et Q_right."""
    with open(Q_LEFT_PATH, "rb") as f:
        Q_left = pickle.load(f)

    with open(Q_RIGHT_PATH, "rb") as f:
        Q_right = pickle.load(f)

    total_pairs = 0
    asym_values = []  # liste des |Q_L(s,a) - Q_R(s',a')|

    for state_str, actions_L in Q_left.items():
        if not isinstance(actions_L, dict):
            continue
        # On ne regarde que les états effectivement modifiés (au moins une Q != 0 côté gauche)
        if not any(v != 0.0 for v in actions_L.values()):
            continue

        mirror_state = mirror_state_str(state_str)
        actions_R = Q_right.get(mirror_state)
        if not isinstance(actions_R, dict):
            continue

        for a, qL in actions_L.items():
            ma = mirror_action.get(a)
            if ma is None or ma not in actions_R:
                continue
            qR = actions_R[ma]
            diff = abs(qL - qR)
            asym_values.append(diff)
            total_pairs += 1

    print("=== Comparaison Q_left vs Q_right (miroir) ===")
    print(f"  Fichier gauche : {os.path.basename(Q_LEFT_PATH)}")
    print(f"  Fichier droite : {os.path.basename(Q_RIGHT_PATH)}")
    print(f"  Nombre de paires (état, action) comparées avec leur miroir : {total_pairs}")
    if asym_values:
        avg_asym = sum(asym_values) / len(asym_values)
        max_asym = max(asym_values)
        print(f"  Asymétrie moyenne |Q_L(s,a) - Q_R(s',a')| : {avg_asym:.4f}")
        print(f"  Asymétrie maximale : {max_asym:.4f}")
    else:
        print("  Aucune paire symétrique trouvée ou Q_left est entièrement nul / non recouvrant Q_right.")


def analyze_commandes_symmetry() -> None:
    """Analyse la symétrie entre commandes_L.txt et commandes_R.txt."""
    try:
        with open(CMD_LEFT_PATH, "r", encoding="utf-8") as f:
            data_L = json.load(f)
        with open(CMD_RIGHT_PATH, "r", encoding="utf-8") as f:
            data_R = json.load(f)
    except FileNotFoundError as e:
        print("=== Comparaison commandes_L / commandes_R ===")
        print(f"  Fichier manquant : {e}")
        return

    steps_L = data_L.get("steps", [])
    steps_R = data_R.get("steps", [])

    print("\n=== Comparaison commandes_L.txt vs commandes_R.txt (miroir) ===")
    print(f"  Fichier gauche : {os.path.basename(CMD_LEFT_PATH)} (steps={len(steps_L)})")
    print(f"  Fichier droite : {os.path.basename(CMD_RIGHT_PATH)} (steps={len(steps_R)})")

    if len(steps_L) != len(steps_R):
        print("  Longueurs différentes : les deux séquences de commandes ne sont pas symétriques (tailles).")
        return

    n = len(steps_L)
    max_err_volant = 0.0
    max_err_gaz = 0.0
    max_err_frein = 0.0

    for k, (cL, cR) in enumerate(zip(steps_L, steps_R)):
        vL = float(cL.get("volant", 0.0))
        gL = float(cL.get("gaz", 0.0))
        fL = float(cL.get("frein", 0.0))

        vR = float(cR.get("volant", 0.0))
        gR = float(cR.get("gaz", 0.0))
        fR = float(cR.get("frein", 0.0))

        # Symétrie attendue : volant_R ≈ -volant_L, gaz et frein identiques
        err_volant = abs(vR + vL)
        err_gaz = abs(gR - gL)
        err_frein = abs(fR - fL)

        max_err_volant = max(max_err_volant, err_volant)
        max_err_gaz = max(max_err_gaz, err_gaz)
        max_err_frein = max(max_err_frein, err_frein)

    print(f"  Nombre de pas comparés : {n}")
    print(f"  Erreur max sur volant (volant_R + volant_L) : {max_err_volant:.4f}")
    print(f"  Erreur max sur gaz    (gaz_R - gaz_L)      : {max_err_gaz:.4f}")
    print(f"  Erreur max sur frein  (frein_R - frein_L)  : {max_err_frein:.4f}")


if __name__ == "__main__":
    analyze_Q_symmetry()
    analyze_commandes_symmetry()
