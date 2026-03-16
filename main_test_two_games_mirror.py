"""Test miroir de Q-learning sur deux environnements SimuKart.

Ce script est dédié au debug de la symétrie gauche/droite au niveau de Q.

Principe :
- On crée deux envs : env_L et env_R (même dynamique, mêmes paramètres).
- On initialise Q_L et Q_R avec des mêmes valeurs miroir.
- A chaque step : on choisit une action act_L via epsilon-greedy,
  et on applique act_R = action_miroir(act_L) dans env_R.
- On met à jour Q_L et Q_R, puis on compare Q_L(state, act_L) et
  Q_R(state, act_R) (même état discret, actions miroirs).
"""

import sys
from pathlib import Path

import numpy as np

# Pour importer les modules du projet
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from classes.simulation import SimulationCore  # type: ignore
from classes.kart import Kart                  # type: ignore


# Hyperparamètres Q-learning (doivent correspondre à 0-kart_qulearning.py)
MAX_Y = 1.0
MAX_STEPS = 400
GAMMA = 0.9
ALPHA = 0.01


def max_dict(d: dict[int, float]) -> tuple[int, float]:
    max_v = float("-inf")
    max_k = 0
    for k, v in d.items():
        if v > max_v:
            max_v = v
            max_k = k
    return max_k, max_v


def create_bins():
    """Discrétisation identique à celle de 0-kart_qulearning.py (version symétrique)."""
    bins = np.zeros((3, 8))
    bins[0] = np.linspace(-MAX_Y, MAX_Y, 8)
    bins[1] = np.linspace(-np.pi / 8, np.pi / 8, 8)
    bins[2] = np.linspace(-0.1, 0.1, 8)
    return bins


def assign_bins(observation, bins):
    """Chaque observation → indice 0-8 (9 valeurs) via np.digitize sur 8 bornes."""
    state = np.zeros(3, dtype=int)
    for i in range(3):
        state[i] = np.digitize(observation[i], bins[i])
    return state


def get_state_as_string(state) -> str:
    return "".join(str(int(e)) for e in state)


def initialize_Q(n_actions: int) -> dict[str, dict[int, float]]:
    """Initialise un Q-table vide (rempli à la volée)."""
    return {}


MIRROR_ACTION = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0}


def get_mirror_action_index(a: int) -> int:
    return MIRROR_ACTION.get(a, a)


class SimuKart:
    """Environnement simplifié basé sur SimulationCore, avec la même logique de reward/terminated."""

    def __init__(self, kart: Kart):
        self.simu = SimulationCore(kart)
        self.kart = kart
        self.dt = 0.025
        self.max_episode_time = 10.0
        # État initial
        self.kart.init_state(vitesse=np.array([10.0, 0.0, 0.0]))

        # Actions = angles volant (comme 0-kart_qulearning.py)
        self.volant_angles = [-10, -5, 0, 5, 10]
        n_actions = len(self.volant_angles)
        self.action_space = type(
            "ActionSpace",
            (object,),
            {"n": n_actions, "sample": lambda self: np.random.randint(0, n_actions)},
        )()

    def reset(self, mirror=False):
        self.simu.reset()
        # Redonner une vitesse initiale (sinon kart reste à l'arrêt)
        Y_init = 0.1 if not mirror else -0.1
        self.kart.init_state(position=np.array([0., Y_init, 0.]), vitesse=np.array([10., 0., 0.]))
        x, y = self.kart.position[0], self.kart.position[1]
        lacet = self.kart.angles[0]
        omega = self.kart.vitangul[0]
        observation = np.array([y, lacet, omega])
        info = {}
        return observation, info

    def step(self, action: int):
        volant_deg = self.volant_angles[action]
        self.simu.step(self.dt, kart_controls={"volant": volant_deg, "gaz": 0, "frein": 0})
        x, y = self.kart.position[0], self.kart.position[1]
        lacet = self.kart.angles[0]
        omega = self.kart.vitangul[0]

        observation = np.array([y, lacet, omega])
        reward = MAX_Y - abs(y)
        terminated = abs(y) > MAX_Y
        truncated = self.simu.temps > self.max_episode_time
        info = {}
        return observation, reward, terminated, truncated, info


def play_two_games_mirror(bins, Q_L, Q_R, eps=0.5, max_steps=400, verbose=True, tol=1e-6):
    """Lance deux épisodes miroir en parallèle et compare Q_L et Q_R à chaque step."""

    kart_L = Kart()
    kart_R = Kart()
    env_L = SimuKart(kart_L)
    env_R = SimuKart(kart_R)

    obs_L, _ = env_L.reset(mirror=False)
    obs_R, _ = env_R.reset(mirror=True)

    if verbose:
        print("Initial states:")
        print("  obs_L:", obs_L)
        print("  obs_R:", obs_R)

    done_L = False
    done_R = False
    cnt = 0

    state_L = get_state_as_string(assign_bins(obs_L, bins))
    state_R = get_state_as_string(assign_bins(obs_R, bins))

    diffs_Q = []

    while not (done_L or done_R) and cnt < max_steps:
        cnt += 1

        if state_L not in Q_L:
            Q_L[state_L] = {a: 0.0 for a in range(env_L.action_space.n)}
        if state_R not in Q_R:
            Q_R[state_R] = {a: 0.0 for a in range(env_R.action_space.n)}

        # Epsilon-greedy partagé
        if np.random.uniform() < eps:
            act_L = env_L.action_space.sample()
        else:
            act_L = max_dict(Q_L[state_L])[0]
        act_R = get_mirror_action_index(act_L)

        obs_L, r_L, term_L, trunc_L, _ = env_L.step(act_L)
        obs_R, r_R, term_R, trunc_R, _ = env_R.step(act_R)

        if verbose:
            # On s'attend à ce que obs_R soit le miroir de obs_L (y, lacet, omega) -> (-y, -lacet, -omega)
            obsL_f = np.asarray(obs_L, dtype=float)
            obsR_f = np.asarray(obs_R, dtype=float)
            is_mirror = np.allclose(obsR_f, -obsL_f, atol=tol)
            same_reward = abs(r_L - r_R) <= tol

            # N'afficher que si le comportement diverge de ce qui est attendu
            if (not is_mirror) or (not same_reward):
                print(f"divergence step {cnt:3d} | "+"\n"+
                    f"obs_L={obsL_f}, act_L={act_L}, r_L={r_L:.3f}, term_L={term_L}, trunc_L={trunc_L}")
                print(f"obs_R={obsR_f}, act_R={act_R}, r_R={r_R:.3f}, term_R={term_R}, trunc_R={trunc_R}")

        done_L = term_L or trunc_L
        done_R = term_R or trunc_R

        if term_L and cnt < max_steps:
            r_L = -300
        if term_R and cnt < max_steps:
            r_R = -300

        state_new_L = get_state_as_string(assign_bins(obs_L, bins))
        state_new_R = get_state_as_string(assign_bins(obs_R, bins))

        if state_new_L not in Q_L:
            Q_L[state_new_L] = {a: 0.0 for a in range(env_L.action_space.n)}
        if state_new_R not in Q_R:
            Q_R[state_new_R] = {a: 0.0 for a in range(env_R.action_space.n)}

        a1_L, max_q_L = max_dict(Q_L[state_new_L])
        a1_R, max_q_R = max_dict(Q_R[state_new_R])

        target_L = r_L if done_L else (r_L + GAMMA * max_q_L)
        target_R = r_R if done_R else (r_R + GAMMA * max_q_R)

        Q_L[state_L][act_L] += ALPHA * (target_L - Q_L[state_L][act_L])
        Q_R[state_R][act_R] += ALPHA * (target_R - Q_R[state_R][act_R])

        # Comparaison simple sur le même état discret (états initiaux identiques)
        if state_L == state_R and act_R == get_mirror_action_index(act_L):
            qL = Q_L[state_L][act_L]
            qR = Q_R[state_R][act_R]
            diff = abs(qL - qR)
            if (abs(diff) > tol):
                diffs_Q.append(diff)
            if verbose:
                print(
                    f"    Q_L[{state_L}][{act_L}]={qL:.3f} | "
                    f"Q_R[{state_R}][{act_R}]={qR:.3f} | diff={diff:.3e}"
                )
            if diff > tol:
                print(f"\nViolation de symétrie de Q au step {cnt}, diff={diff:.6e} > tol={tol:.6e}")
                break

        state_L, act_L = state_new_L, a1_L
        state_R, act_R = state_new_R, a1_R

    if diffs_Q:
        print(f"\nRésumé symétrie Q sur cet épisode miroir  après {cnt} steps :")
        print(f"  Ecart moyen |Q_L - Q_R| : {np.mean(diffs_Q):.6f}")
        print(f"  Ecart max   |Q_L - Q_R| : {np.max(diffs_Q):.6f}")
    else:
        print(f"No divergence of Q found after {cnt} steps")


def main():
    bins = create_bins()
    # Q_L et Q_R initialisés vides mais même structure d'actions
    Q_L = initialize_Q(n_actions=5)
    Q_R = initialize_Q(n_actions=5)

    eps = 0.5
    print("Lancement d'un test de symétrie Q avec deux jeux miroir (gauche/droite)...")
    play_two_games_mirror(bins, Q_L, Q_R, eps=eps, max_steps=MAX_STEPS, verbose=True, tol=1e-6)


if __name__ == "__main__":
    main()
