import gymnasium as gym
import numpy as np 
import matplotlib.pyplot as plt 
""" ORIGINAL - NE PAS MODIFIER
    Eexemple de Qlearning pour le jeu CartPole: un chariot tient un pendule en l'air et se déplace sur un rail horizontal.
	la commande est une force appliquée au chariot, vers la gauche ou vers la droite.
	le but est de tenir le pendule en l'air pendant 500 steps.
	le jeu est terminé si le pendule tombe, si le chariot sort du rail, ou si 500 steps sont atteints.
	le reward est de 1 parait-il à chaque pas de temps.
	le state est la position et la vitesse du chariot, et l'angle et la vitesse du pendule.
	le action space est la force appliquée au chariot, vers la gauche ou vers la droite.
	le reward space est le reward obtenu à chaque pas de temps.
	le state space est l'espace des états possibles.
    qui commence à m'interesser car c'est de la dynamique
	il apprend typiquement à tenir le pendule en l'air pendant 500 steps en 5000 jeux"""

# Cheat sheet Gym/Gymnasium (CartPole):
# 1) env = gym.make("CartPole-v1")
# 2) New Gymnasium API:
#    observation, info = env.reset()
#    observation_, reward, terminated, truncated, info = env.step(action)
#    done = terminated or truncated
# 3) Action space for CartPole is a discrete force applied to the cart: 0 (left), 1 (right)
# 4) This script is now updated to Gymnasium API.

env = gym.make('CartPole-v1')

MAXSTATES = 10**4
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
	# obs[0] -> cart position --- -4.8 - 4.8
	# obs[1] -> cart velocity --- -inf - inf
	# obs[2] -> pole angle    --- -41.8 - 41.8
	# obs[3] -> pole velocity --- -inf - inf
	
	bins = np.zeros((4,10))
	bins[0] = np.linspace(-4.8, 4.8, 10)
	bins[1] = np.linspace(-5, 5, 10)
	bins[2] = np.linspace(-.418, .418, 10)
	bins[3] = np.linspace(-5, 5, 10)

	return bins

def assign_bins(observation, bins):
	""" on assigne à chaque 4-observation sa place dans l'espace des observables 4x10 bins """
	state = np.zeros(4)
	for i in range(4):
		state[i] = np.digitize(observation[i], bins[i])
	return state

def get_state_as_string(state):
	string_state = ''.join(str(int(e)) for e in state)
	return string_state

def get_all_states_as_string():
	states = []
	for i in range(MAXSTATES):
		states.append(str(i).zfill(4))
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
	max_steps = env.spec.max_episode_steps if env.spec is not None else 500
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

def play_many_games(bins, N=10000):
	Q = initialize_Q()

	length = []
	reward = []
	for n in range(N):
		#eps=0.5/(1+n*10e-3)
		eps = 1.0 / np.sqrt(n+1)

		episode_reward, episode_length = play_one_game(bins, Q, eps)
		
		if n % 100 == 0:
			print(n, '%.4f' % eps, episode_reward)
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