
import numpy as np
# Les fonctions de rotations: s'applique à des vecteurs ou des suites de vecteurs:
print ("Définition fonctions")

def tourne_vecteur(V, angle):
    #tourne le vecteur (ou les vecteurs de la "liste") V d'un angle donné  
    V2=np.copy(V)
    try:
        np.shape(V)[1]
        V2[:,0]= np.cos(angle)*V[:,0]-np.sin(angle)*V[:,1]       
        V2[:,1] = np.sin(angle)*V[:,0]+np.cos(angle)*V[:,1]      
    except (IndexError, TypeError):
        V2[0]= np.cos(angle)*V[0]-np.sin(angle)*V[1]       
        V2[1] = np.sin(angle)*V[0]+np.cos(angle)*V[1]   
    return (V2)   
def vehicule2piste(V,lacet): return tourne_vecteur(V, lacet)
def piste2vehicule(V,lacet): return tourne_vecteur(V,-lacet)
def roue2vehicule(V, braquage): return tourne_vecteur(V, braquage)
def vehicule2roue(V, braquage): return tourne_vecteur(V,-braquage)

def norme_vecteur(V): return ((V[0]**2+V[1]**2+V[2]**2)**0.5)   