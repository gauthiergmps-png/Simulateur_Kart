# # SIMULATEUR KART

# RECAP DES VARIABLES IMPORTANTES:
   #  etat, tableau 4x3 float
        # etat[0,:]X = position du cdg =  première ligne donc, en repère piste
        # etat[1,:]Xpoint= vecteur vitesse en repère véhicule, donc attention, il faut le détourner d'un cran !
        # etat[2,:]vt=angles de Bryant (phi(z), vt(y), psi(x)),
        # etat[3,:]vtpoint, les vitesses angulaires en rd/s, attention, omega = np.flip(etat[3,:] !)

    # variables roues: je les prefere en clair à des tableaux: dans l'ordre avg, avd, arg, ard:
        # roue_avg.position() = vecteur position I/F roue/sol en repère véhicule
        # kart.pavg = valeur du poid statique du kart sur cette roue
        # favg = vecteur force appliquée par le sol à la roue, en repère véhicule
        # vavg = vecteur vitesse du centre de chaque roue en repère roue,
        # gavg = etat de glisse: 0=arret, 1=regime linéaire, 2=pneu saturé
    # commande
        # volant = angle volant en degré
        # gaz = en ch moteur
        # frein 0 à 4: de 1 à 4, Vitesse tangentielle imposée à 98%,96% 90%, 10% de la roue libre.
        # transm: 0= propulsion et roues independantes, 1= Axe rigide arrière, 2= 4WD axes AV et AR rigides


# PARTIE SIMULATION NUMERIQUE

import numpy as np
from math import floor
import time
from classes.wheel import Wheel
from classes.kart import Kart
from classes.utils import *


# Définition paramètres véhicule, longeurs en mêtres

adherence= 1.    # adherence du pneu, 1=cone de frottement à 45°

kart=Kart()
roue_avg=Wheel("AVG", kart) 
roue_avd=Wheel("AVD", kart) 
roue_arg=Wheel("ARG", kart)  
roue_ard=Wheel("ARD", kart) 

# Les dimensions de roue (rayon et largeur) sont définis proportionnels à la charge statique



def angles_roues(volant):
    # calcul des angles de braquage roues avant G et D en repère véhicule en radians à partir d'un angle volant en deg
    # et d'un angle de reglage "ouverture"
    braquage=np.radians(volant)
    ouv=np.radians(ouverture.get())
    if (abs(braquage)>1e-10):
        R=kart.empattement/np.tan(braquage)
        vtG=np.arctan(kart.empattement/(R-roue_avg.position()[1]))-ouv
        vtD=np.arctan(kart.empattement/(R-roue_avd.position()[1]))+ouv
        return(vtG, vtD)
    else: return(-ouv,ouv)

def V_arbre(vg, vd, rgg, rgd, gaz, frein):  # Renvoie la vitesse de l'arbre AR fixe
    # on peut bougrement simplifier si gaz=0, non ??? en fait probablement non, voir equations.
    global debug                     # nombreux "print if debug" supprimés, voir en 0.9 if needed
    if (debug): print (f"IN  V_arbre: Vg = {vg[0]:.3f},{vg[1]:.3f},{vg[2]:.3f}, Vd = {vd[0]:.3f},{vd[1]:.3f},{vd[2]:.3f} gaz={gaz:.3f} frein ={frein:0d}")

    def gg5(vg, vd, rgg, rgd, gaz, vt):
        # fonction dont on cherche le zéro pour determiner la vitesse d'arbre vt
        # calcul des vitesses de glissement des point de contacts des deux roues, des alpha:
        nvg = norme_vecteur(vg) ; nvd = norme_vecteur(vd)                  # vitesses d'entrainement du centre roue % sol, gauche et droite
        vgg=vg+np.array([vt,0.,0.])   ; vgd = vd+np.array([vt,0.,0.])      # vitesses de glissement des point de contact
        nvgg = norme_vecteur(vgg) ; nvgd = norme_vecteur(vgd) ;
        alphag= min(1., nvgg/0.05/(max(1.,nvg)))   # donc en zone linéaire  0 <= alpha < 1, sinon =1 en saturé,en traitant vsol=0
        alphad= min(1., nvgd/0.05/(max(1.,nvd)))   # donc en zone linéaire  0 <= alpha < 1, sinon =1 en saturé,en traitant vsol=0
        # calcul de la fonction gg:
        gg_g = 0. if (nvgg==0.) else  vgg[0] / norme_vecteur(vgg)     # calcul de cos(teta)
        gg_d = 0. if (nvgd==0.) else  vgd[0] / norme_vecteur(vgd)
        gg_m = -10000000. if (abs(vt)<0.000001) else 1. / vt
        gg_value= alphag * rgg * gg_g + alphad * rgd * gg_d - gaz * gg_m # -Sigma(F) = Alpha.Rg*Cos(teta) + Id - gaz / Vt
        return (gg_value)

    # Recherche du zéro de gg par méthode itérative stupide, Newton marchant moins bien sur cette fonction peu C²
    erreur = 1.
    vt =min(-0.0001, -0.5*(vg[0]+vd[0]))   # on part d'une vitesse estimée moyenne pas trop con, toujours négative
    vtmin = vt ; vtmax=0.
    boucle=0
    while (gg5(vg, vd, rgg, rgd, gaz, vtmin)>0.)and(boucle<100) :
        boucle+=1
        vtmin = 2. * vtmin  # recherche d'un vtmin tel que gg(vtmin) <0.
    if (boucle>99): print("      WARNING - BOUCLE 100 pour Vtmin =", Vtmin)

    boucle=0
    while (abs(erreur) >0.000001*abs(vt)) and (boucle<100) :
        boucle+=1
        vt = 0.5 *(vtmin+vtmax)
        if gg5(vg, vd, rgg, rgd, gaz, vt) >0. :
            vtmax=vt
        else:
            vtmin=vt
        erreur = vtmax-vtmin
    if (vt>0.):
        print("      WARNING - ANNULATION VT >0.")
        vt=0

    # application du frein:
    match frein:    # pourquoi ce crétin de jupyter ne met pas match en vert ??
        case 0 : vtf=vt
        case 1 : vtf=0.98*vt    # Freinage: 1 = 98%, léger lineaire
        case 2 : vtf=0.96*vt    # Freinage: 1 = 96%, fort linéraire
        case 3 : vtf=0.9*vt
        case 4:  vtf=0.1*vt
    if (debug): print (f"OUT V_arbre: avant frein Vt ={vt:.3f} après frein: {vtf:.3f}")
    return (vtf)

def inversf(ycible, d):
    # Utilisée pour la roue libre: Donne le zéro de la fonction f(teta) = ycible - sinus(teta) ( cos(d) + sin(d) tan(teta))
    # et renvoie donc teta en radians en fonction de ycible et d en radians qui doit être positif ici.
    # f'(teta) = - cos(teta) (cos(d)+ sin(d) tan(teta))  - sin(teta) sin(d) 1 / cos²(teta)
    #          = - cos(teta) cos(d) - sin(d) sin (teta) ( 1 +   1 / cos²(teta) )
    erreur = 1.
    teta = 45. / 180. * np.pi

    f = lambda teta : ycible - np.sin(teta) * ( np.cos(d) + np.sin(d) * np.tan(teta))
    fprime = lambda teta: - np.cos(teta) * np.cos(d) - np.sin(d) * np.sin (teta) * ( 1 +   1 / np.cos(teta)**2 )

    if (f(0.1/180.*np.pi)<0.): return 0.
    if (f(89.9/180.*np.pi)>0.): return np.pi/2

    # iteration méthode de newton: Xn+1 = Xn - f(Xn) / f'(Xn)
    boucle=0
    while (abs(erreur) >0.01) and (boucle<100) :
        boucle+=1
        erreur = f(teta)/fprime(teta)
        teta = max(0.1/180.*np.pi, min(89.9/180.*np.pi, teta - erreur))    # teta doit rester entre 0.1° et 89.9°
    if boucle ==100 : print("erreur boucle: ycible =", ycible,"d en deg = ", d*180./np.pi)

    return teta

def adher_roue(Vsol, gaz, frein, Varbre, Fz):
    # cas général: Si Varbre=0. c'est une roue libre, sinon c'est une roue sur arbre arrière ou 4WD
    if not(Varbre): # cas d'une roue libre, avec gaz ou frein
        if not(frein):
            return adher_roue_libre(Vsol, gaz, Fz)
        else:         # roue libre freinée, on calcule la vitesse imposée par le frein
            match frein:
                case 1 : vf=-0.98*Vsol[0]   # Freinage: 1 = 98%, on reste linéaire
                case 2 : vf=-0.96*Vsol[0]   # Freinage: 1 = 96%, on reste juste linéaire
                case 3 : vf=-0.90*Vsol[0]   # Freinage: 1 = 90%, on sature la roue
                case 4 : vf=0.             # Freinage: 1 = 98%, on bloque la roue
            return adher_roue_V_force(Vsol, vf, Fz)
    else:
        return adher_roue_V_force(Vsol, Varbre, Fz)

def adher_roue_libre(Vsol, gaz, Fz):
    # renvoie la force d'adhérence au sol d'une roue libre sur son axe, éventuellement avec un couple moteur,
    # force retournée en repère roue, qui sera donc appliquée par la roue au véhicule,
    # En fonction de la vitesse du sol en repère roue, des gaz (ici en W), et de la Fz sur cette roue
    # Renvoie aussi l'état de glisse: Roue à l'arret=0, zone linéaire = 1, saturée par couple = 2, saturée par dérive = 3
    force=[0.,0.,Fz]    #le pneu renvera Fx=0 si pas de  gaz et Fz en z (négative, vers le haut donc)

    d_lin = 5/180*np.pi            # zone de comportement linéaire, dérive max en radians
    Rg = adherence * abs(Fz)       # rayon du cone de glissement sec, module de la force max donc
    nVsol= (Vsol[0]**2+Vsol[1]**2)**0.5
    Vmin=0.4
    d = 0. if (nVsol<0.01) else np.arctan(Vsol[1]/Vsol[0])
    sens = np.sign(Vsol[0])

    if (Fz>=0.):            # Roue "en l'air" donc
        force=[0.,0.,0.]
        glisse=0
    elif nVsol<Vmin:
        if gaz<1.:                      # zone de très basse vitesse (<1m/s) avant arret
            force=[-100*Vsol[0], -1000*Vsol[1], Fz]                 # on met une sorte de freinage linéaire pour arret
            glisse=0
        else:
            force=[Rg, -1000*Vsol[1], Fz]
            glisse = 2
    elif abs(d) < d_lin:                # zone de comportement lineaire
        # Calcul de Fn:
        force[1]=-sens*d/d_lin*Rg
        # calcul de Ft: Calculons Pmax possible avant de saturer le pneu:
        t1 = (d_lin**2-d**2)**0.5 / d_lin   # = sinus teta
        t2 = t1 * Rg                            # = sinus teta * Rg; c'est le Ft max linéaire
        Pmax = t2 * nVsol * np.cos(d)            # = sinus teta * Rg * Vsol * Cos(d)
        if (gaz<Pmax):   # la puissance appliquée ne sature pas le pneu:
            force[0]= gaz/ ( nVsol * np.cos(d) )     # donc on ajoute Ft et on touche pas à Fn
            glisse=1
        else:            # la puissance sature le pneu
            ycible = gaz / (Rg * nVsol )
            teta = inversf(ycible,abs(d))
            force[0] = np.sin(teta) * Rg
            force[1] = -np.cos(teta) * np.sign(Vsol[1])*Rg
            glisse=2
    else:              # C'est la dérive qui sature le pneu
        ycible = gaz / (Rg * nVsol )              # valeur de sinus teta ( cos(d) + sin(d) tan(teta)) qu'il faut inverser, dans R+
        if (ycible<0.01):
            teta=0.
        else:
            teta = inversf(ycible,abs(d))
        force[0] = np.sin(teta) * Rg
        force[1] = - np.cos(teta) * np.sign(Vsol[1])*Rg
        glisse=3
    return force, glisse

def adher_roue_V_force(Vsol, Varbre, Fz):
    # renvoie la force d'adhérence d'une roue à vitesse forcée (ex: AR sur un pont rigide, ou roue freiné) celle qui sera appliquée au véhicule,
    # en repère roue en fonction de la vitesse du centre roue % sol en repère roue,de la vitesse Tangentielle du point de contact roue % sol
    # imposée à la roue (par un arbre rigide, ou par un système de freinage), et de la force verticale appliqués à cette roue uniquement
    # Renvoie aussi l'info de glisse: Roue à l'arret=0, zone linéaire = 1, saturée par couple = 2, saturée par dérive = 3
    global debug
    force=[0.,0.,Fz]    #le pneu renvera Fx, Fy et Fz en z (négative, vers le haut donc)

    Rg = adherence * abs(Fz)       # rayon du cone de glissement sec, module de la force max donc
    Vg =  Vsol + np.array([Varbre,0.,0.])   # La vitesse tangentielle du point de contact pneu % sol (donc sa vitesse de glisse en X) est la somme de la vitesse arbre et de la vitesse d'entrainement
                                               # d'où un glissement tangentiel, du signe de la force qui en résulte sur le véhicule, <0 roue extérieure
    nVg= norme_vecteur(Vg)            # vitesse de glisse totale du point de contcat
    nVsol=norme_vecteur(Vsol)
    sVy = np.sign(Vg[1])
    if not(sVy) : sVy = 1.   # signe de Vy, forcé à +1 si Vy nul.
    if (debug): print (f"IN adher roue: Vsol={Vsol[0]:.3f}, {Vsol[1]:.3f}, {Vsol[2]:.3f} Vg ={Vg[0]:.3f},{Vg[1]:.3f},{Vg[2]:.3f} Varbre={Varbre:.3f} nVsol={nVsol:.3f} nVg={nVg:.3f} sVy={sVy:.3f}")

    if (Fz>=0.):            # Roue "en l'air" donc
        force=[0.,0.,0.]
        glisse=0
    elif (nVsol<=0.1)and(abs(Varbre)<=0.1):  # zone de très basse vitesse (<1m/s) sans gaz avant arret
        force=[-1000*Vsol[0], -1000*Vsol[1], Fz]                 # on met une sorte de freinage linéaire pour arret
        glisse=0
    elif (nVsol<=0.3)and(abs(Varbre)>0.1):   # Roue à l'arret mais il y a Varbre
        force=[Rg, -1000*Vsol[1], Fz]   # pour décoller de l'arret complet après remise de gaz.
        glisse = 2
    else:
        teta=-np.pi/2 if not(Vg[1]) else np.arctan(Vg[0]/Vg[1])
        alpha = min(1., nVg/(0.05*nVsol))  # alpha < 1 en zone de comportement lineaire, glisssement < 5% de Vsol, cohérent de 3° dérive roue libre
        force[0]= -  Rg * np.sin(teta) * alpha* sVy
        force[1]= - Rg * np.cos(teta) * alpha * sVy
        glisse=1 if (alpha<1.) else 3    # le pneu saturé si alpha >=1.
    if (debug): print (f"OUT adher roue: glisse={glisse:0d} fx={force[0]:.3f}, fy={force[1]:.3f} gaz={gaz:.3f} teta ={teta*180/np.pi:.3f}, alpha= {alpha:.3f}")
    return force, glisse


def V_et_Fz_roues(tetaG, tetaD, V_cdg, Omeg_cdg, lacet):
    global debug, h_cdg, force_cdg, coul_chassis, coul_chassis
    # calcul de la vitesse du centre de chaque roue en repère roue,
    # V_roue[0,:] = Vitesse avg, V_roue[1,:]=avd, V_roue[2,:] = arg, V_roue[3,:] = ard
    V_roue = np.array([ [0.,0.,0.], [0.,0.,0.],[0.,0.,0.], [0.,0.,0.] ])
    # En repère véhicule la vitesse roue est Vcdg + Rot ^ R, donc à tourner pour roues avant
    omega=np.flip(Omeg_cdg)
    V_roue[0,:] = vehicule2roue(V_cdg+ np.cross(omega,roue_avg.position()),tetaG)
    V_roue[1,:] = vehicule2roue(V_cdg+ np.cross(omega,roue_avd.position()),tetaD)
    V_roue[2,:] = V_cdg+ np.cross(omega,roue_arg.position())
    V_roue[3,:] = V_cdg+ np.cross(omega,roue_ard.position())

    #Prise en compte transfert de masse si h_cdg non nul: On calcule le couple de transfert en repère véhicule:
    couple_transfert=np.cross(np.array([0.,0.,-h_cdg]),piste2vehicule(force_cdg, lacet)) # car les forces sont en dessous du cdg
    Fdy = couple_transfert[1]/2./kart.empattement ; #  Force dynamique pour compenser le couple Cy entrainé par les Fx
    Fdxav = couple_transfert[0]/2./kart.voie_av  ; #  Force dynamique à l'avant pour compenser le couple Cx entrainé par les Fy
    Fdxar = couple_transfert[0]/2./kart.voie_ar  ; #  Force dynamique à l'arrière pour compenser le couple Cx entrainé par les Fy
    Fzt = np.array([-kart.pavg-Fdy-Fdxav, -kart.pavd-Fdy+Fdxav, -kart.parg+Fdy-Fdxar, -kart.pard+Fdy+Fdxar])

    # Traitement d'un éventuel décollage d'une roue
    # print (f" Avant corrections : Fzt = {Fzt[0]:.3f}   {Fzt[1]:.3f}  {Fzt[2]:.3f}  {Fzt[3]:.3f}total =",Fzt[0]+Fzt[1]+Fzt[2]+Fzt[3])
    # On vérifie qu'aucune roue est tirée vers le bas (Fz>0.), si oui on ajoute du poid aux trois autres
    if (np.count_nonzero(Fzt>0.)==1): # test si une roue décolle
        Nup= np.argmax(Fzt) # index de la roue en l'air
        Fzt[(Nup+1)%4]+=Fzt[Nup]/3. # on transfère un tiers de poid manquant sur chaque autre roue
        Fzt[(Nup+2)%4]+=Fzt[Nup]/3. # en fait faudrait faire au prorata des poids statiques je pense
        Fzt[(Nup+3)%4]+=Fzt[Nup]/3.
        Fzt[Nup]=0.

    coul_chassis=4
    if (np.count_nonzero(Fzt>0.)!=0) :# si malgré ça, une deuxième  roue décolle, tonneau
        coul_chassis=3    # Si le kart fait un tonneau, il devient rouge
        print ("CRASH - TONNEAU")

    # print (f" Après corrections : Fzt = {Fzt[0]:.3f}   {Fzt[1]:.3f}  {Fzt[2]:.3f}  {Fzt[3]:.3f}total =",Fzt[0]+Fzt[1]+Fzt[2]+Fzt[3])
    #favg = [0.,0.,Fzt[0]] ; favd = [0.,0.,Fzt[1]] ; farg = [0.,0.,Fzt[2]] ; fard = [0.,0.,Fzt[3]]
    return (V_roue, Fzt)

def forces_roues(tetaG, tetaD, gaz, frein, V_roue, Fzt):
    # Calcul des quatre forces d'interaction roue-piste en repère véhicule, en fonction des angles volant
    global  debug, transm, Varbre

    # TRANSMISSION: Propulsion roue indépendante, Axe arrière ou full 4 Wheels
    if (transm.get()==0):       # Cas d'un arbre libre, donc roues arrières indépendantes, roues av libres
        # et en plus du gaz sur les roues arrières, qu'on envoie en watt, egalement sur les deux roues arrières
        favg, gavg = adher_roue(V_roue[0,:] , 0.,          frein, 0., Fzt[0]) ; favg=roue2vehicule(favg, tetaG)
        favd, gavd = adher_roue(V_roue[1,:] , 0.,          frein, 0., Fzt[1]) ; favd=roue2vehicule(favd, tetaD)
        farg, garg = adher_roue(V_roue[2,:] , gaz*735.5/2.,frein, 0., Fzt[2])
        fard, gard = adher_roue(V_roue[3,:] , gaz*735.5/2.,frein, 0., Fzt[3])
        #if (debug): print ("out adherence  : (varg, vard)", varg, vard,"(farg, fard):", farg, garg, fard, gard)
    elif (transm.get()==1):     # Cas d'un pont arrière rigide,
        rgg = adherence * abs(Fzt[2])       # rayon du cone de glissement sec, module de la force max induite par la roue AR concernée
        rgd = adherence * abs(Fzt[3])
        # Calcul de la vitesse de rotation de l'abre arrière, exprimée sous la forme de la vitesse tangentielle imposée par l'arbre
        # au point de contact des roues AR % au repère roue arrière,
        Varbre = V_arbre(V_roue[2,:], V_roue[3,:] , rgg, rgd, gaz*735.5, frein)  # Toute puissance sur axe arrière
        favg, gavg = adher_roue(V_roue[0,:] , 0., frein, 0.    , Fzt[0]) ; favg=roue2vehicule(favg, tetaG)
        favd, gavd = adher_roue(V_roue[1,:] , 0., frein, 0.    , Fzt[1]) ; favd=roue2vehicule(favd, tetaD)
        farg, garg = adher_roue(V_roue[2,:] , 0., 0. ,   Varbre, Fzt[2])
        fard, gard = adher_roue(V_roue[3,:] , 0., 0. ,   Varbre, Fzt[3])
        #if (debug): print ("out adher ARBRE : (varg, vard):", varg, vard,"Varbre :", Varbre)
        #if (debug): print ("                : (farg, fard):", farg, garg, fard, gard)
    else:  # Cas d'un 4 Wheels intégral, quatre roues asservies à une même vitesse de rotation
        rgg = adherence * abs(Fzt[2])       # On va dire que la vitesse arbre est imposée par les roues AR
        rgd = adherence * abs(Fzt[3])
        # Calcul de la vitesse de rotation de l'arbre arrière, au prorata de la puissance prise à l'AR,
        # vitesse imposée ensuite aux quatres roues (sinon faut faire un Varbre 4WD dédié)
        # ce qui fait un truc bizarre, le Fx des roues avant varie avec H cdg en zone linéaire ???
        Varbre = V_arbre(V_roue[2,:], V_roue[3,:], rgg, rgd, gaz*735.5*(1.-kart.pos_cdg), frein)
        favg, gavg = adher_roue(V_roue[0,:], 0., 0., Varbre, Fzt[0])    ; favg=roue2vehicule(favg, tetaG)
        favd, gavd = adher_roue(V_roue[1,:], 0., 0., Varbre, Fzt[1])    ; favd=roue2vehicule(favd, tetaD)
        farg, garg = adher_roue(V_roue[2,:], 0., 0., Varbre, Fzt[2])
        fard, gard = adher_roue(V_roue[3,:], 0., 0., Varbre, Fzt[3])
        #if (debug): print ("out adher ARBRE : (varg, vard):", varg, vard,"Varbre :", Varbre)
        #if (debug): print ("                : (farg, fard):", farg, garg, fard, gard)

    if (debug):print (f" FORCES ROUES: favg = {favg[0]:.3f} {favg[1]:.3f}  {favg[2]:.3f} favd = {favd[0]:.3f} {favd[1]:.3f} {favd[2]:.3f} farg = {farg[0]:.3f} {farg[1]:.3f}  {farg[2]:.3f} fard = {fard[0]:.3f} {fard[1]:.3f} {fard[2]:.3f}")
    return(favg, favd, farg, fard, gavg, gavd, garg, gard)

def deriv_etat(etat_evalue):
    # On calcule la dérivée d'un état évalué =[X, Xpoint, Teta, Tetapoint]
    # On rappelle que ses éléments sont des vecteurs à trois dimensions:
        # etat[0,:]=X = vecteur position du cdg en repère piste
        # etat[1,:]=Xpoint= vecteur vitesse en repère véhicule, donc attention, il faut le détourner d'un cran !
        # etat[2,:]= Teta=angles de Bryant (phi(z), teta(y), psi(x)),
        # etat[3,:]Tetapoint, les vitesses angulaires en rd/s, attention, omega = np.flip(etat[3,:] !)
    # les variable globale ne sont pas utilisée, sont des sorties pour l'affichage du dernier état propagé
    global force_cdg, moment_cdg, gaz, frein, volant, favg, favd, farg, fard, gavg, gavd, garg, gard
    V_cdg    = etat_evalue[1,:]
    Omeg_cdg = etat_evalue[3,:]
    lacet    = etat_evalue[2,0]
    detat    = np.zeros((4,3), dtype=float)   # Initialisation du vecteur résultat

    # Dérivée de la position du cdg en repère piste = c'est la vitesse en repère piste
    detat[0,:]=vehicule2piste(V_cdg, lacet)

    # dérivée des angles, c'est leur vitesse avant de faire plus compliqué en 3D,
    # mais attention, le kart tourne, donc on détourne son vecteur vitesse, car on l'exprime en repère véhicule !!
    detat[2,:]=Omeg_cdg
    detat[1,:]= np.cross(V_cdg, np.flip(detat[2,:]))

    #FORCES ET MOMENTS APPLIQUES PAR LES ROUES AU CDG VEHICULE, en repère véhicule
    tetaG, tetaD=angles_roues(volant)
    # Calcul des vitesses et Fz par roue
    V_roue, Fzt = V_et_Fz_roues(tetaG, tetaD, V_cdg, Omeg_cdg, lacet)
    #calcul vecteurs force par roue en fonction vitesse véhicule, vlacet, angle volant, en repère véhicule
    favg, favd, farg, fard, gavg, gavd, garg, gard=forces_roues(tetaG, tetaD, gaz, frein, V_roue, Fzt)
    # calcul des forces et moments totaux:
    force_cdg=favg+favd+farg+fard
    if(force_cdg[0]!=favg[0]+favd[0]+farg[0]+fard[0]): print ("IL Y A BIEN UN PROBLEME SUR SOMME FORCE_CDG !!!")
    moment_cdg=np.cross(roue_avg.position(),favg)+np.cross(roue_avd.position(),favd)+ np.cross(roue_arg.position(),farg)+np.cross(roue_ard.position(),fard)     #calcul moment résultant des forces au cdg par les bras de leviers et produit vectoriel:
    # Ajout force_aero= -Cx * V²,  en repère véhicule - A VENIR

    #forces extérieures ramenées en repère piste, puis ajout des forces de gravité dans ce repère:
    force_cdg=vehicule2piste(force_cdg, lacet) + np.array([0.,0.,kart.pavg+kart.pavd+kart.parg+kart.pard]) # ajout de la force de gravité
    if (abs(force_cdg[2])>1e-5): print("Problème, la voiture a une force Z !", force_cdg[2])  # on vérifie qu'il s'envole pas

    #dérivée des vitesses du cdg = acceleration, sans oublier le détournage précédent
    detat[1,:]= detat[1,:]+piste2vehicule(force_cdg/kart.masse, lacet)

    # idem rotations pour l'instant en 2D, seul moment lacet: dérivée lacet = vlacet, et dérivée vlacet = moment / inertie
    # il faudra remettre moment_cdg dans le bon ordre d'ailleurs !
    detat[3,0]=moment_cdg[2]/kart.inertie_lacet

    return(detat)

#PARTIE DESSINS, ANIMATION GRAPHIQUE ET PROGRAMME PRINCIPAL
from tkinter import Tk, Canvas, Frame, Button, LEFT, RIGHT, TOP, BOTTOM, CENTER, HORIZONTAL, VERTICAL, ARC, LAST, Label, Scale, \
                    Checkbutton, Radiobutton, IntVar, W, N, S

def init():
    global etat, favg, favd, farg, fard, gavg, gavd, garg, gard    # etat du kart au sens large
    global volant, gaz, frein, force_cdg, moment_cdg, Varbre, coul_chassis   # commandes et observable
    global cam_alt0, cam_speed0, xcam, ycam, hist_xcdg,hist_ycdg  # elements d'affichage
    global temps, dtold, pas_com, pas_simul, debug, t_cyclemax  # paramètres de simulation

    #initialisation vecteur état du vehicule et autres variables clés:
        # etat=[X, Xpoint, Teta, Tetapoint] ou les elements sont des vecteurs à trois dimensions:
            # X = position du cdg (axes SAE donc x vers l'avant, y à droite, z vers le bas),
            # Xpoint= vecteur vitesse en repère véhicule
            # Teta=angles de Bryant (phi(z), teta(y), psi(x)),
            # Tetapoint, les vitesses angulaires en rd/s
        # commandes = (volant, gaz, frein), volant en degré, gaz en ch moteur, freinage en % du couple de glisse sans transfert
        # Fxx = forces interface roue/sol et gxx état de glisse par roue
    etat = np.array([ [0.,0.,0.],     # position initiale
                      [0.,0.,0.],     # vitesse initiale en repère véhicule en m/s
          [np.radians(0.),0.,0.],     # rotations initiales en radians
                      [0.,0.,0.] ])   # vitesses angulaires initiales en rad/sec

    debug=False   # pour impressions de debug avec "t"

    volant=0. ; gaz=0. ; frein=0 ; Varbre=0.      # commandes initiales (volant (deg, positif à droite), gaz, frein

    favg = [0.,0.,-kart.pavg] ; favd = [0.,0.,-kart.pavd] ; farg = [0.,0.,-kart.parg] ; fard = [0.,0.,-kart.pard] # Forces roues initiales
    gavg = 0 ; gavd = 0 ; garg = 0 ; gard = 0

    dtold=25  ;  temps=0. ; pas_simul=0  ;pas_com=0 ;t_cyclemax =0.
    xcam = 0. ; ycam=0.  ; cam_alt0=100 ; cam_speed0=5 ; hist_xcdg=[] ; hist_ycdg=[]
    force_cdg=[0., 0., 0.] ; moment_cdg=[0., 0., 0.]

    coul_chassis=4
    print ("Initialisation de l'état")
    return

def reset():   # Si je met ca dans init, ca bugge car ces variables ne sont pas encore connues...
    init()
    pas_de_temps.set(0)       # donc après un reset, on est en pause
    volant_curseur.set(0)     # et volant droit
    return

def profil_voiture(x_cdg,y_cdg, lacet, volant):
    # Retourne un profil complet x,y à plotter du véhicule en fonction de l'état
    # Arguments entrée = 4 float
    # Sortie: 20 points = 5 fois 4 points, pour 5 polygones: un chassis et 4 roues avg avd arg ard
    XCDG= np.array([x_cdg,y_cdg,0.])
    tetaG, tetaD=angles_roues(volant)

    # On trace le polygone chassis
    X = kart.profil
    # 
    #on colle les quatres polygones roue 
    X = np.append(X,tourne_vecteur(roue_avg.profil(), tetaG)+roue_avg.position(), axis=0) # Roue AVG, tournée de tetaG,
    X = np.append(X,tourne_vecteur(roue_avd.profil(),tetaD)+roue_avd.position(), axis=0) # Roue AVD, 
    X = np.append(X, roue_arg.profil()+roue_arg.position(), axis=0)      # On colle une roueG en arg,
    X = np.append(X, roue_ard.profil()+roue_ard.position(), axis=0)      # On colle une roueD en ard, 

    # et on tourne la voiture de l'angle lacet, puis on la place à sa position
    X=XCDG+vehicule2piste(X,lacet)
    return( list(X[:,0]), list(X[:,1]) )          # on renvoie deux listes, les coord. x et les coord. y des points à tracer

def profil_circuit(x_cdg,y_cdg):
    # Retourne un profil complet x,y, donc en coordonnées absolues, à plotter sous le vehicule
    # prévoir d'ajouter type_circuit

    # type_circuit = 0: quadrillage: on se contente donc de dessiner 3x3 carrés de 10m de coté, autour du kart qui est dans le carré du milieu
    # le premier coin est donc à la partie entière de position(CDG)/10m,  on défini deux vecteurs H et V pour les segments horizontaux et verticaux
    Xo= np.array([10.*floor(x_cdg/10.),10.*floor(y_cdg/10.)])
    H=np.array([10.,0.])  ; V=np.array([0.,10.])
    # puis on fait une sequence habile, un polygone un peu compliqué qui fait presque un carré 3x3 autour du carré contenant le kart
    X=np.array([Xo])
    X = np.append(X,[Xo-V, Xo-V-H, Xo-H, Xo+2*H,Xo+2*H-V, Xo+H-V, Xo+H+2*V, Xo+2*H+2*V, Xo+2*H+V, Xo-H+V, Xo-H+2*V,Xo+2*V], axis=0)

    # # type_circuit = 1: anneau
    # x = np.linspace(0, 2*np.pi, 100)
    # R=50.
    # X=np.zeros((100,2))
    # X[:,0] = R*np.cos(x)
    # X[:,1] = R*(-1+np.sin(x))

    return( list(X[:,0]), list(X[:,1]) )          # on renvoie deux listes, les coord. x et les coord. y des points à tracer

def Dessin(xcam, ycam, scale, kc):            # fonction de dessin du canevas à chaque pas
    #   xcam, ycam position caméra drone
    #   scale = échelle du kart % canevas ,fonction de l'altitude du drone
    #   kc= echelle des informations dynamiques % taille kart

    global etat,hist_xcdg,hist_ycdg, gaz, frein, force_cdg, moment_cdg, coul_chassis
    # on efface tout, et on calcule l'origine d'affichage
    cnv.delete('all')

    # les coordonnées d'affichages sont les mêmes axes que Etat[0], à translation et échelle près
    origx = int(900-scale*xcam) ; origy = int(500-scale*ycam)
    xcdg=etat[0,0] ; ycdg=etat[0,1] ; lacet=etat[2,0]
    vitesse=vehicule2piste(etat[1,:],lacet)


    # CALCUL ET TRACE DU CIRCUIT OU FOND DE PISTE
    x,y=profil_circuit(xcdg,ycdg)    # calcul d'un profil "circuit" (ou fond de piste), coordonnées absolues en mêtres
    circuit = []                     # qu'on va recalculer en repère écran
    for i in range (0,len(x)): circuit+= [int(scale*x[i])+origx,int(scale*y[i])+origy]
    cnv.create_polygon(circuit, outline='black', fill='',width=1)

    # CALCUL ET TRACE DU KART
    x,y=profil_voiture(xcdg,ycdg, lacet, volant)    # calcul profil "véhicule", coordonnées absolues en mêtres

    # dessin des cinq polygones chassis + roues, en repère écran avec les couleurs qu'il faut
    # couleurs roues en fonction de l'état: Noire à l'arret, blue en lineaire, orange = saturé par couple, rouge = saturé par derive
    couleurs=['black','blue','orange', 'red', 'yellow']    ;    coul_roue=couleurs[:]

    chassis = []
    for i in range (0,4): chassis += [int(scale*x[i])+origx, int(scale*y[i])+origy]
    cnv.create_polygon(chassis, outline='black', fill=couleurs[coul_chassis], width=1)

    coul_roue[1]=couleurs[gavg]   ;  coul_roue[2]=couleurs[gavd] ; coul_roue[3]= couleurs[garg]  ; coul_roue[4]= couleurs[gard]
    for roue in range (1,5):
        polygone = []
        for point in range (0,4):
            i=4*roue+point
            polygone+= [int(scale*x[i])+origx, int(scale*y[i])+origy]
        cnv.create_polygon(polygone, outline='black', fill=coul_roue[roue], width=1)


    # ENREGISTREMENT ET TRACE D'UNE QUEUE DE TRAJECTOIRE
    hist_xcdg.append(xcdg) ; hist_ycdg.append(ycdg)            # on enregistre tout l'historique de trajectoire
    queue=[]
    for i in range (max(len(hist_xcdg)-50,0),len(hist_xcdg)):
        queue+=[int(scale*hist_xcdg[i])+origx, int(scale*hist_ycdg[i])+origy]
    if len(queue)>50:                     # quand la queue a la longeur voulue, on a garde à cette longeur et on la trace
        del queue[0:2]                     # ce qui supprime uniquement les index 0 et 1 !!
        cnv.create_line(*queue, fill='red', dash=(2,20),width=1)

    # CALCUL ET TRACE DES INFORMATIONS DYNAMIQUES
    # trace de la flèche "vitesse"
    cnv.create_line(scale*xcdg+origx,scale*ycdg+origy, scale*(xcdg+kc/10*vitesse[0])+origx,\
                    scale*(ycdg+kc/10*vitesse[1])+origy,width=3, fill="blue", arrow=LAST, arrowshape=(18,20,3))

    # trace de la flèche "force cdg"
    cnv.create_line(scale*xcdg+origx,scale*ycdg+origy, scale*(xcdg+kc/10000*force_cdg[0])+origx,\
                    scale*(ycdg+kc/10000*force_cdg[1])+origy,width=3, fill="red", arrow=LAST, arrowshape=(18,20,3))

    # trace du petit arc indiquant le "moment lacet" appliqué au kart:
    TT1=20/100*kc ; TT2 = -1   # TT1 = diametre de l'arc, TT2 = gain sur moment affiché, saturé à 90° pour lisibilité
    cnv.create_arc((scale*(xcdg-TT1)+origx,scale*(ycdg-TT1)+origy), (scale*(xcdg+TT1)+origx, scale*(ycdg+TT1)+origy), outline="red",
                   extent=min(max(-90, TT2*moment_cdg[2]), 90), start=-180.*lacet/np.pi, fill='',  width=3, style=ARC)

    # on calcule et trace les informations dynamiques de chaque roue:
          # centré sur point d'application de la force d'interaction Pneu/véhicule = vecteur force (Fx, Fy, Fz)
          # Un cercle de diamètre = kc*diamètre roue en statique, et proportionnel à Fz en dynamique
          # Une flèche de direction/longueur force (Fx, Fy) dans cette échelle, représente la force appliquée par le pneu au sol.

    def trace_dyn(position, poid, force, rayonstat, scale):
        # Affiche les informations dynamiques: cercle = Cone max, flèche = Force roue appliquée au véhicule
        # position = position centre roue, poid = poid statique sur roue, force = force sur piste axes pistes,
        # rayon du cercle voulu
        # les deux points pour create_oval sont les deux angles du carré dans lequel s'incrit le cercle...
        rayon= -rayonstat*force[2]/poid
        cnv.create_oval(scale*(position[0]-rayon)+origx,scale*(position[1]-rayon)+origy,
                        scale*(position[0]+rayon)+origx,scale*(position[1]+rayon)+origy, outline="green", width=3 )
        if (force[2]!=0.): cnv.create_line(scale*position[0]+origx,scale*position[1]+origy,
                        scale*(position[0]-rayon*force[0]/force[2])+origx,scale*(position[1]-rayon*force[1]/force[2])+origy,
                        width=3, fill="green", arrow=LAST)

    # Affichage info dynamiques des roues AVG / AVD / ARG / ARD
    r_av= roue_avg.rayon  # rayon des roues avant
    r_ar= roue_arg.rayon  # rayon des roues arrières 
    trace_dyn(etat[0,:]+vehicule2piste(roue_avg.position(), lacet), kart.pavg, vehicule2piste(favg, lacet), kc*r_av, scale)
    trace_dyn(etat[0,:]+vehicule2piste(roue_avd.position(), lacet), kart.pavd, vehicule2piste(favd, lacet), kc*r_av, scale)
    trace_dyn(etat[0,:]+vehicule2piste(roue_arg.position(), lacet), kart.parg, vehicule2piste(farg, lacet), kc*r_ar, scale)
    trace_dyn(etat[0,:]+vehicule2piste(roue_ard.position(), lacet), kart.pard, vehicule2piste(fard, lacet), kc*r_ar, scale)

    # affichage indicateurs gaz/frein
    cnv.create_rectangle(30, 30, 50, 110, fill='white', outline='black')
    cnv.create_rectangle(30, int(110-frein*20), 50, 110, fill='red', outline='')
    cnv.create_rectangle(60, 30, 80, 110, fill='white', outline='black')
    cnv.create_rectangle(60, int(110-gaz*80./100.), 80, 110, fill='springgreen', outline='')
    dt_text = cnv.create_text(68, 100, text=str(int(gaz)), font="Arial 10", fill="black")

    #  affichage compte tour et vitesse (pour l'intant le compte tour affiche la vitesse)
    V=3.6 * norme_vecteur(etat[1,:])
    cnv.create_arc((100,40), (190, 130), outline="cyan", extent=max(-240, -2*V), start=210,
               fill='',  width=20, style=ARC)
    dt_text = cnv.create_text(143, 80, text=str(int(V)), font="Arial 18", fill="white")

    return



def press_key(event):
# Fonctions d'actions, suite à commandes manuelles sur clavier
    global volant, gaz, frein, debug

    # pour connaitre le nom d'une touche, utiliser la commande suivante:
    # dt_text = cnv.create_text(200, 200, text=event.keysym, font=('bold',20), fill="red")

    # q/w = modification vitesse forcés
    if event.keysym == "d":   etat[1,:]*= 1.05
    if event.keysym == "c": etat[1,:]*= 0.95

    # Volan = Gauche/Droite variations +/- 5°, saturé à 45° - réglage fin = l,m
    if event.keysym == "Left":  volant=max(volant-5., -45.) ; volant_curseur.set(volant)
    if event.keysym == "Right": volant=min(volant+5., 45.)  ; volant_curseur.set(volant)
    if event.keysym == "l":  volant=max(volant-1., -45.) ; volant_curseur.set(volant)
    if event.keysym == "m": volant=min(volant+1., 45.)  ; volant_curseur.set(volant)

    # s/x = gaz up/down - reglage fin avec majuscule
    if event.keysym == "s": frein=0 ; gaz=min(gaz+10, 80)
    if event.keysym == "S": frein=0 ; gaz=min(gaz+1, 80)
    if event.keysym == "x": gaz=max(0, gaz-10)
    if event.keysym == "X": gaz=max(0, gaz-1)

    # d/c = frein up/down
    if event.keysym == "q": gaz=0  ; frein=min(frein+1, 4)
    if event.keysym == "w":          frein=max(0, frein-1)
    if event.keysym == "space": # Espace = pause simulation
        pause()

    # Up/Down: accelleration/ralentissement de la simulation
    if event.keysym == "Up":    pas_de_temps.set(pas_de_temps.get()+5)
    if event.keysym == "Down":  pas_de_temps.set(pas_de_temps.get()-5)

    # Appui sur t: mode debug
    if event.keysym == "t": debug=True

def stop_key(event):
    global debug
    debug=False
    return

def pause():
    global dtold
    if pas_de_temps.get():
        dtold=pas_de_temps.get()  ; pas_de_temps.set(0)
    else:
        pas_de_temps.set(dtold)

# PROGRAMME PRINCIPAL

#initialisation des variables
init()

# Paramètres et installation de la fenètre: zéro en haut à gauche
fenetre = Tk()
fenetre.title("Simulateur Sprint Car by Laurent Gauthier - V0.10")

# ajout bandeau de controles et commandes, et on défini des frames cote à cote
# vocabulaire: commandes = volant, gaz, frein  controles = le reste
bandeau = Frame(fenetre,  width=1800, height=100, highlightbackground="red", highlightthickness=2)
bandeau.pack()

frameB = Frame(bandeau, width=200, height=100, highlightbackground="black", highlightthickness=1)
frameB.pack(side=LEFT)
frameA = Frame(bandeau, width=200, height=100, highlightbackground="black", highlightthickness=1)
frameA.pack(side=LEFT)
frame0 = Frame(bandeau, width=200, height=100, highlightbackground="black", highlightthickness=1)
frame0.pack(side=LEFT)
frame1 = Frame(bandeau, width=200, height=100)
frame1.pack(side=LEFT)
frame2 = Frame(bandeau , width=200, height=100,highlightbackground="black", highlightthickness=1)
frame2.pack(side=LEFT)
frame3 = Frame(bandeau , width=200, height=100,highlightbackground="black", highlightthickness=1)
frame3.pack(side=LEFT)
frame4 = Frame(bandeau , width=200, height=100,highlightbackground="black")
frame4.pack(side=LEFT)
frame5 = Frame(bandeau , width=200, height=100,highlightbackground="black", highlightthickness=1)
frame5.pack(side=LEFT)
frame6 = Frame(bandeau, width=200, height=100)
frame6.pack(side=LEFT)
frame7 = Frame(bandeau, width=200, height=100)
frame7.pack(side=LEFT)
frame8 = Frame(bandeau, width=200, height=100,highlightbackground="black", highlightthickness=1)
frame8.pack(side=LEFT)

# Choix commandes: clavier (0) ou fichier commande (1=écriture, 2=lecture)
commandes=IntVar()
Label(frameB, text="""Commandes:""", justify = LEFT, padx = 20).pack()
Radiobutton(frameB, text="Clavier", padx = 20, variable=commandes, value=0).pack(anchor=W)
Radiobutton(frameB, text="W Fichier", padx = 20, variable=commandes, value=1).pack(anchor=W)
Radiobutton(frameB, text="R Fichier", padx = 20, variable=commandes, value=2).pack(anchor=W)
Radiobutton(frameB, text="Reset", padx = 20, variable=commandes, value=3).pack(anchor=W)
commandes.set(0)
F_com=[]

# Controle propagation:
pas_de_temps = Scale(frameA, from_=0, to=300, tickinterval=0.01, length=100, label="Pas de temps (ms)", orient=HORIZONTAL)
pas_de_temps.set(0)
pas_de_temps.pack()

methode=IntVar()
Label(frameA, text="""Propagateur:""", justify = LEFT, padx = 20).pack()
Radiobutton(frameA, text="Euler", padx = 20, variable=methode, value=0).pack(anchor=W)
Radiobutton(frameA, text="Runge-Kutta 4", padx = 20, variable=methode, value=1).pack(anchor=W)
methode.set(0)


# Controle échelle affichage dynamique:
echelle_dyn = Scale(frame0, from_=0, to=5, length=100, label="Aff. Dynamique", orient=HORIZONTAL)
echelle_dyn.set(1.0)
echelle_dyn.pack()

# Controle drone porte caméra:
cam_alt = Scale(frame1, from_=10, to=1000, length=100, label="Altitude drone", orient=HORIZONTAL)
cam_alt.set(cam_alt0)
cam_alt.pack()

cam_speedmax=20
cam_speed = Scale(frame1, from_=0, to=cam_speedmax, length=100, label="Rapidité drone", orient=HORIZONTAL)
cam_speed.set(cam_speed0)
cam_speed.pack()

# Boutons RESET, PAUSE, QUIT:
button = Button(frame3, text="RESET", fg="green", command=reset)
button.pack(padx=10, pady=5, anchor=N)
button = Button(frame3, text="PAUSE", fg="blue", command=pause)
button.pack(padx=10, pady=5, anchor=CENTER)
button = Button(frame3, text="QUIT", fg="red", command=fenetre.destroy)
button.pack(padx=10, pady=5, anchor=S)

# Commande Volant et controle hauteur CdG par curseur:
volant_curseur = Scale(frame4, from_=-45, to=45, length=200, label="Volant", orient=HORIZONTAL)
volant_curseur.set(volant)
volant_curseur.pack()
H_cdg = Scale(frame4, from_=0, to=100, length=200, label="H CdG en %", orient=HORIZONTAL)
H_cdg.set(0)
H_cdg.pack()

# Controles régulateur, asservisement lacet, transmission:
regul = IntVar()
Vold=0.
def set_v():
    global Vold
    if regul.get(): Vold = norme_vecteur(etat[1,:])
    return

Checkbutton(frame5, text = "Regulateur de vitesse", padx = 20, variable = regul,onvalue = 1, command=set_v, offvalue = 0).pack(anchor=W)

ass_d = IntVar()
Checkbutton(frame5, text = "Asserv. d", padx = 20, variable =ass_d,onvalue = 1, offvalue = 0).pack(anchor=W)
ass_d0=Scale(frame5, from_=-2, to=2, resolution=.1, length=100, label="V_lacet cible", orient=HORIZONTAL)
ass_d0.set(0)
ass_d0.pack()
ass_dgain_stat=Scale(frame5, from_=0, to=5, resolution=0.1, length=100, label="Gain Statique", orient=HORIZONTAL)
ass_dgain_stat.set(2.5)
ass_dgain_stat.pack()
ass_dgain_dyn=Scale(frame6, from_=0, to=5, resolution=0.1, length=100, label="Gain Dynamique", orient=HORIZONTAL)
ass_dgain_dyn.set(2.5)
ass_dgain_dyn.pack()

ouverture=Scale(frame7, from_=-5, to=5, resolution=1, length=100, label="Ouverture", orient=HORIZONTAL)
ouverture.set(0)
ouverture.pack()
transm=IntVar()
Label(frame7, text="""Transmission:""", justify = LEFT, padx = 20).pack()
Radiobutton(frame7, text="Propulsion", padx = 20, variable=transm, value=0).pack(anchor=W)
Radiobutton(frame7, text="Axe arrière", padx = 20, variable=transm, value=1).pack(anchor=W)
Radiobutton(frame7, text="Full 4 wheels", padx = 20, variable=transm, value=2).pack(anchor=W)

# Zone télémesures: deux lignes
telemesure1 = Label(fenetre, fg="blue")
telemesure1.pack()
telemesure2= Label(fenetre, fg="green")
telemesure2.pack()

# Zone d'animation, focus sur le canevas pour qu'il réponde aux pressions sur les touches -

cnv = Canvas(fenetre, width=1800, height=1000, background="#003300")
cnv.pack()
cnv.bind("<KeyPress>", press_key)
cnv.bind("<KeyRelease>", stop_key)  # je m'en sert pas en fait.
cnv.focus_set()
cnv.focus_get()
cnv.focus_force()


# pour écrire un fichier:
# file=open("trajectoire.txt","w")
# for i in range(frames):
#     # propagation état et enregistrement dans fichier
#     file.write(np.array2string(etat,max_line_width=240)[1:-1]+"\n")
#     etat=etat+deriv_etat()*dt


def Animation():           # Boucle principale de simulation, incrémente l'indice pas_simul, augmente le temps de dt= pas_de_temps
    global  pas_com, pas_simul, temps, xcam, ycam, Vold, t_cyclemax
    global etat,  force_cdg, moment_cdg,  Varbre, h_cdg
    global volant, gaz, frein, F_com


    start = time.time()
    pas_simul=pas_simul+1   # dont la première animation est au pas=1 et au temps = dt, mais avance en pause
    dt=pas_de_temps.get()/1000.
    if (dt!=0):            # pas_com pour indexer le fichier de commande, inutile en pause
        pas_com=pas_com+1
        temps=temps+dt

    # on lit les controles
    h_cdg=kart.empattement /100.*H_cdg.get()  # pour l'avoir en mêtre à partir du controle en % de l'empattement
    scale=10000/cam_alt.get()

    # Propagation par méthode d'Euler. Comme le dt doit être faible pour l'affichage, inutile de faire mieux.
    detat=deriv_etat(etat)
    etat=etat+detat*dt

    #LECTURE ET ENREGISTREMENT COMMANDES
    volant =volant_curseur.get()
    if (dt!=0 and commandes.get()==1) :    # commandes=1 : on enregistre le fichier commande
        F_com.append([volant, gaz, frein])
    elif (dt!=0 and commandes.get()==2):             # commandes=1 : replay
        try:
            volant,gaz, frein = F_com[pas_simul]
        except IndexError:
            commandes.set(0)
    elif (commandes.get()==3): # commandes=3 : reset du fichier commande
        F_com=[]

    #Regul vitesse: si on, on fige le module du vecteur vitesse à la valeur demandée
    V=norme_vecteur(etat[1,:])
    if regul.get(): etat[1,:]=Vold/V*etat[1,:]

    #Asservissement V_lacet: Si on, on asservi en statique sur la dérive  demandée et en dynamique sur vitesse lacet
    if ass_d.get():
        correction=ass_dgain_stat.get()*(ass_d0.get()-etat[3,0])-ass_dgain_dyn.get()*detat[3,0]
        volant=max(min(volant+correction, +45), -45)
        volant_curseur.set(volant)

    #on affiche les lignes de télémesures
    f_cdg=piste2vehicule(force_cdg, etat[2,0])
    texteaff=f"N= {pas_simul:10}  T = {temps:6.2f}  Tcyclemax = {int(t_cyclemax*1000):5d}\
        F_com = {len(F_com):5d}  X = {etat[0,0]:6.2f}   Y = {etat[0,1]:6.2f}   Z = {etat[0,2]:6.2f} \
            Vx = {etat[1,0]:6.2f}  Vy = {etat[1,1]:6.2f}   Teta = {etat[3,0]*180./np.pi:6.2f} \
            V =  {V:6.2f} m/s =  {V*3.6:6.2f} km/h     Gaz = {gaz:3.0f} ch Vold = {Vold:6.2f}"
    telemesure1.config(text=str(texteaff))

    # Calcul du rayon du cercle osculateur à peaufiner je pense....
    Radius=1000000000. if (norme_vecteur(force_cdg)<0.00001) else kart.masse*V*V/norme_vecteur(force_cdg)
    texteaff=f"FORCES APPLIQUES AU CDG:  \
    Fcdg x ={f_cdg[0]:^+10.2f}  Fcdg y ={f_cdg[1]:^+10.2f}  Fcdg z ={f_cdg[2]:^+10.2f} \
    F_cdg = {norme_vecteur(force_cdg):^+10.2f} Mcdg ={moment_cdg[2]:^+10.2f}   Radius ={Radius:^+10.2f}\
    Varbre = {Varbre:^+10.2f}  Vstab = {np.dot(force_cdg,vehicule2piste(etat[1,:],etat[2,0])):^+10.2f}"
    telemesure2.config(text=str(texteaff))

    # on calcule la position du drone caméra, qui suit la voiture avec un lag:
    speedcam=cam_speed.get()
    xcam=(speedcam*etat[0,0]+(cam_speedmax-speedcam)*xcam)/cam_speedmax
    ycam=(speedcam*etat[0,1]+(cam_speedmax-speedcam)*ycam)/cam_speedmax

    # on affiche le fond de piste, le kart, sa queue, et les infos dynamiques:
    Dessin(xcam, ycam,scale,echelle_dyn.get())

    # on regarde combien de temps on a pris pour tout ça, et on attend la fin du dt avant de relancer
    # pour que la fenètre soit appelée toutes les dt millisecondesl utilisé !

    t_cycle=time.time()-start
    if (temps>1.) : t_cyclemax=max(t_cycle, t_cyclemax)   # à partir d'une seconde,on observe le tcycle

    fenetre.after(max(1,int((dt-t_cycle)*1000)), Animation)

if __name__ == "__main__":
    # commençons le mouvement et démarrons la fenêtre
    print("Lancement animation")
    Animation()
    fenetre.mainloop()