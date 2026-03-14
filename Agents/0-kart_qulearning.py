import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classes.simulation import SimulationCore
from classes.kart import Kart
import numpy as np 
import matplotlib.pyplot as plt 
""" """

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

    def reset(self):
        """reset() -> (observation, info)"""
        self.simu.reset()
        # Redonner une vitesse initiale (sinon kart reste à l'arrêt et reward = 0 tout l'épisode)
        self.kart.init_state(vitesse=np.array([5., 0., 0.]))
        x, y = self.kart.position[0], self.kart.position[1]
        lacet = self.kart.angles[0]
        omega = self.kart.vitangul[0]
        observation = np.array([y, lacet, omega])
        info = {}
        return observation, info

    def step(self, action):
        """step(action) -> (observation, reward, terminated, truncated, info)"""
        # TODO: appliquer action, faire un pas simu, dériver observation/reward/terminated/truncated

        volant_deg = self.volant_angles[action]  # action = indice 0..4 → angle en degrés
        _,_,_,_,_=self.simu.step(self.dt, kart_controls={'volant': volant_deg, 'gaz': 0, 'frein': 0})
        x, y, lacet, omega = self.kart.position[0], self.kart.position[1], self.kart.angles[0], self.kart.vitangul[0]

		# Observation = (y, lacet, omega), donc on se fout de x
        observation = ([y, lacet, omega])
        reward = 10- abs(y)
        terminated = abs(y) > 10
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
	bins[0] = np.linspace(-10, 10, 10)
	bins[1] = np.linspace(-np.pi, np.pi, 10)
	bins[2] = np.linspace(-1, 1, 10)

	return bins

def assign_bins(observation, bins):
	""" on assigne à chaque DIM-observation sa place dans l'espace des observables DIMx10 bins """
	state = np.zeros(STATE_DIM)
	for i in range(STATE_DIM):
		state[i] = np.digitize(observation[i], bins[i])
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

def play_one_game(bins, Q, eps=0.5):
	observation, info = env.reset()
	done = False
	max_steps = 400 # nombre de pas de temps max dans un épisode
	cnt = 0 # number of moves in an episode
	state = get_state_as_string(assign_bins(observation, bins))
	total_reward = 0

	while not done:
		cnt += 1
		if state not in Q:
			Q[state] = {a: 0.0 for a in range(env.action_space.n)}
		# ON choisi l'action, prop espilon au hasard, prob 1-eps greedy, i.e la "meilleure" action connue dans cet état
		if np.random.uniform() < eps:
			# choix d'une action au hasard
			act = env.action_space.sample() #
		else:			
			# choix de la meilleure action connue dans cet état
			act = max_dict(Q[state])[0]
		
		observation, reward, terminated, truncated, info = env.step(act)
		done = terminated or truncated

		# le reward est de 1 parait-il à chaque pas de temps
		total_reward += reward

		if terminated and cnt < max_steps:
			# echec avant la limite max de l'episode: on penalise fortement
			reward = -300

		state_new = get_state_as_string(assign_bins(observation, bins))

		# np.digitize peut renvoyer 10 (hors bords) -> state sur 5 chiffres, absent de Q initial
		if state_new not in Q:
			Q[state_new] = {a: 0.0 for a in range(env.action_space.n)}
		a1, max_q_s1a1 = max_dict(Q[state_new])
		Q[state][act] += ALPHA*(reward + GAMMA*max_q_s1a1 - Q[state][act])
		state, act = state_new, a1					

	return total_reward, cnt

def play_many_games(bins, N=500):
	Q = initialize_Q()

	length = []
	reward = []
	for n in range(N):
		eps = 1.0 / np.sqrt(n+1)

		episode_reward, episode_length = play_one_game(bins, Q, eps)
		print("Step: ", n, "Durée: ", episode_length, "Reward: ", episode_reward)
		# if n % 10 == 0:     
		# 	print(n, '%.4f' % eps, episode_reward)
		length.append(episode_length)
		reward.append(episode_reward)

	return length, reward

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
	episode_lengths, episode_rewards = play_many_games(bins)

	plot_running_avg(episode_rewards)
	env.close()