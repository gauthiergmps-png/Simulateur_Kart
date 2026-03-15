import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
RECORDS_DIR = PROJECT_ROOT / "Records"
from classes.simulation import SimulationCore
from classes.kart import Kart
import numpy as np 
import matplotlib.pyplot as plt 
import pickle
import json
""" """

MAX_Y = 1


class SimuKart():

    def __init__(self, kart):
        self.simu = SimulationCore(kart)
        self.kart = kart
        self.dt = 0.025  # pas de temps en secondes
        self.max_episode_time = 10.0  # durée max d'un épisode (s) → truncate après 10/dt pas (ex. 400 si dt=0.025)

        # Initialisation de l'état du kart avec une vitesse X
        self.kart.init_state(vitesse=np.array([5., 0., 0.]))

        # 5 actions = 5 angles volant possibles (en degrés)
        self.volant_angles = [-10, -5, 0, 5, 10]
        n_actions = len(self.volant_angles)
        self.action_space = type('ActionSpace', (), { 'n': n_actions,
            'sample': lambda self: np.random.randint(0, self.n) })()

    def reset(self, last=False):
        """reset(last=False) -> (observation, info). Si last=True, info contient 'initial_state' (position, vitesse, angles, vitangul)."""
        self.simu.reset()
        # Redonner une vitesse initiale (sinon kart reste à l'arrêt)
        self.kart.init_state(vitesse=np.array([10., 0., 0.]))
        x, y = self.kart.position[0], self.kart.position[1]
        lacet = self.kart.angles[0]
        omega = self.kart.vitangul[0]
        observation = np.array([y, lacet, omega])
        info = {}
        if last:
            info["initial_state"] = {
                "position": self.kart.position.tolist(),
                "vitesse": self.kart.vitesse.tolist(),
                "angles": self.kart.angles.tolist(),
                "vitangul": self.kart.vitangul.tolist(),
            }
        return observation, info

    def step(self, action):
        """step(action) -> (observation, reward, terminated, truncated, info)"""
        # TODO: appliquer action, faire un pas simu, dériver observation/reward/terminated/truncated

        volant_deg = self.volant_angles[action]  # action = indice 0..4 → angle en degrés
        _,_,_,_,_=self.simu.step(self.dt, kart_controls={'volant': volant_deg, 'gaz': 0, 'frein': 0})
        x, y, lacet, omega = self.kart.position[0], self.kart.position[1], self.kart.angles[0], self.kart.vitangul[0]

        # Observation = (y, lacet, omega), donc on se fout de x
        observation = ([y, lacet, omega])
        # Reward = maximum au centre piste, vaudra de MAX_Y à 0 quand on s'écarte
        reward = MAX_Y- abs(y)
        # Terminated = si on sort de la piste
        terminated = abs(y) > MAX_Y
        # Truncated = si on dépasse le temps max de l'épisode
        truncated = self.simu.temps > self.max_episode_time
        info = {}
        return observation, reward, terminated, truncated, info

    def close(self):
        """close()"""
        pass



"""Fonction principale du premier agent pilote de Kart"""
print("Initialisation du premier agent pilote de Kart...")

# Création des instances 
kart = Kart()

print("Initialisation de l'environnement...")

env = SimuKart(kart)

MAXSTATES = 1000
STATE_DIM = 3
MAX_STEPS = 400
GAMMA = 0.9
ALPHA = 0.01

def max_dict(d):
    """ retourne la clé qui donne la plus grande valeur dans le dictionnaire d et cette valeur
    """
    max_v = float('-inf')
    for key, val in d.items():
        if val > max_v:
            max_v = val
            max_key = key
    return max_key, max_v

def create_bins():
    # On a quatre variables d'observation, avec des amplitudes propres,  on les discrétise en 10 bins chacune
    # obs[0] -> cart position en Y de -10 à 10
    # obs[1] -> cart angle de lacet en radians de -pi à pi
    # obs[2] -> cart velocity angulaire en radians/s de -1 à 1
    
    bins = np.zeros((3,10))
    bins[0] = np.linspace(-2, 2, 10)
    bins[1] = np.linspace(-np.pi/8, np.pi/8, 10)
    bins[2] = np.linspace(-0.1, 0.1, 10)

    return bins

def assign_bins(observation, bins):
    """ Chaque observation → indice 0-9 (10 bins). np.digitize renvoie 1..10, on ramène à 0-9. """
    state = np.zeros(STATE_DIM, dtype=int)
    for i in range(STATE_DIM):
        # digitize donne 1..10 pour 10 bords ; on clip à 0-9 pour toujours 1 chiffre par dimension
        state[i] = np.clip(np.digitize(observation[i], bins[i]) - 1, 0, 9)
    return state

def get_state_as_string(state):
    string_state = ''.join(str(int(e)) for e in state)
    return string_state

def get_all_states_as_string():
    states = []
    for i in range(MAXSTATES):
        states.append(str(i).zfill(STATE_DIM))
    return states

def initialize_Q():
    Q = {}

    all_states = get_all_states_as_string()
    for state in all_states:
        Q[state] = {}
        # pour chaque état, Q[state] est un dictionnaire, les actions possibles en clés et leur valeur 
        for action in range(env.action_space.n):
            Q[state][action] = 0
    return Q

def play_one_game(bins, Q, eps=0.5, verbose=False, record=False):
    """Lance un épisode. Si record=True, enregistre Q et commandes dans Records/ à la fin."""
    last = record  # enregistrer implique dernier épisode (état initial + commandes)
    observation, info = env.reset(last=last)
    initial_state = info.get("initial_state") if last else None
    done = False
    max_steps = MAX_STEPS  # nombre de pas de temps max dans un épisode
    cnt = 0  # number of moves in an episode
    state = get_state_as_string(assign_bins(observation, bins))
    total_reward = 0
    commandes = [] if record else None

    while not done:
        cnt += 1
        if state not in Q:
            Q[state] = {a: 0.0 for a in range(env.action_space.n)}
        # ON choisi l'action, prop espilon au hasard, prob 1-eps greedy, i.e la "meilleure" action connue dans cet état
        if np.random.uniform() < eps:
            # choix d'une action au hasard
            act = env.action_space.sample()
        else:
            # choix de la meilleure action connue dans cet état
            act = max_dict(Q[state])[0]
        if record and commandes is not None:
            commandes.append(act)
        observation, reward, terminated, truncated, info = env.step(act)
        done = terminated or truncated
        if verbose:
            print("cnt: ", cnt, "state: ", state, "act: ", act, "reward: ", reward, "terminated: ", terminated, "truncated: ", truncated)
        total_reward += reward

        # Pénalité forte pour la transition qui fait sortir de la piste (sinon l'agent préfère sortir vite)
        if terminated and cnt < max_steps:
            reward = -300

        state_new = get_state_as_string(assign_bins(observation, bins))

        if state_new not in Q:
            Q[state_new] = {a: 0.0 for a in range(env.action_space.n)}
        a1, max_q_s1a1 = max_dict(Q[state_new])
        # Cible TD : pas de bootstrap depuis l'état terminal (épisode fini)
        target = reward if done else (reward + GAMMA * max_q_s1a1)
        Q[state][act] += ALPHA * (target - Q[state][act])
        state, act = state_new, a1

    if record and commandes is not None and initial_state is not None:
        save_last_commandes(Q, commandes, initial_state)

    return total_reward, cnt


def save_last_commandes(Q, commandes, initial_state):
    """Enregistre Q et la séquence de commandes dans Records/ (appelée par play_one_game quand record=True).
    Format commandes: JSON {"parametres": {position, vitesse, angles, vitangul, ...}, "steps": [...]}."""
    if commandes is None:
        return
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    path_q = RECORDS_DIR / "Q_recorded"
    with open(path_q, "wb") as f:
        pickle.dump(Q, f)
    print(f"Table Q sauvegardée dans '{path_q}'.")
    path_cmd = RECORDS_DIR / "commandes.txt"
    steps = [
        {"volant": env.volant_angles[indice], "gaz": 0, "frein": 0}
        for indice in commandes
    ]
    data = {"parametres": initial_state if initial_state is not None else {}, "steps": steps}
    with open(path_cmd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Commandes sauvegardées dans '{path_cmd}'.")


def play_many_games(bins, N=500, record=False):
    """Lance une série de N épisodes de simulation.
    Si record=True, enregistre Q et les commandes du dernier épisode dans Records/."""

    # Choix : initialiser Q ou charger une version enregistrée (fichiers dans Records/)
    use_saved = input("Charger un Q enregistré ? (o/n) : ").strip().lower()
    if use_saved == 'o':
        fichier_q = input("Nom du fichier Q à charger (dans Records/) ? ").strip()
        path_q = RECORDS_DIR / fichier_q
        try:
            with open(path_q, "rb") as f:
                Q = pickle.load(f)
            print(f"Table Q chargée depuis '{path_q}'.")
        except FileNotFoundError:
            print(f"Fichier '{path_q}' introuvable, initialisation de Q.")
            Q = initialize_Q()
    else:
        Q = initialize_Q()

    length = []
    reward = []
    verbose = False if N > 10 else True
    for n in range(N):
        eps = 1.0 / np.sqrt(n + 1)
        episode_reward, episode_length = play_one_game(bins, Q, eps, verbose, record=(record and (n == N - 1)))
        print("Step: ", n, "Durée: ", episode_length, "Reward total: ", episode_reward)
        # if n % 10 == 0:
        #     print(n, '%.4f' % eps, episode_reward)
        length.append(episode_length)
        reward.append(episode_reward)

    return length, reward, Q


def plot_running_avg(totalrewards):
    N = len(totalrewards)
    running_avg = np.empty(N)
    for t in range(N):
        running_avg[t] = np.mean(totalrewards[max(0, t-100):(t+1)])
    plt.plot(running_avg)
    plt.title("Running Average")
    plt.show()

if __name__ == '__main__':
    bins = create_bins()
    N = int(input("Nombre d'épisodes N ? "))
    record = input("Sauvegarder Q et commandes dans Records/ après la session ? (o/n) : ").strip().lower() == 'o'

    episode_lengths, episode_rewards, Q = play_many_games(bins, N, record=record)

    plot_running_avg(episode_rewards)

    env.close()