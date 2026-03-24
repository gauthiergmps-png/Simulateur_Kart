import numpy as np
try:
    from .utils import *
    from .wheel import Wheel
except ImportError:
    from utils import *
    from wheel import Wheel


class Mobile():
    """Classe parente de la classe Kart, représentant un mobile avec ses propriétés physiques,
    statiques et dynamiques. Le repère mobile est un repère de véhicule (angles de Bryant)."""

    # les methodes "update_" ont vocation à être appelées par la simulation

    def __init__(self, masse=450, inertie_lacet=1000):
        """ Initialise un nouveau mobile avec ses paramètres dynamiques"""
        # Variables statiques: Masse, poids et inertie:
        self.masse = masse             # Masse mobile en Kg
        self.inertie_lacet = inertie_lacet  # inertie en Lacet, Kgm²

        # Variables des forces et moments
        self.force_cdg = np.array([0., 0., 0.])   # force appliquée au cdg en repère absolu
        self.moment_cdg = np.array([0., 0., 0.])  # moment appliqué au cdg en repère absolu

        self.init_state()

    def init_state(self, position=np.array([0., 0., 0.]), vitesse=np.array([0., 0., 0.]), 
                         angles=np.array([0., 0., 0.]), vitangul=np.array([0., 0., 0.])):
        # Variables dynamiques: positions, vitesses, angles et vitesses angulaires, vecteurs 3D
        self.position = position  # vecteur position du cdg en repère piste
        self.vitesse = vitesse    # vecteur vitesse en repère véhicule, donc attention, il faut le détourner d'un cran !
        self.angles = angles      # angles de Bryant (phi(z), teta(y), psi(x))
        self.vitangul = vitangul  # les vitesses angulaires en rd/s, attention, omega = np.flip(vitangul)


    def _update_dynamique(self, dt):
        """ Propage la dynamique du mobile en fonction de la force appliquée au cdg et du moment appliqué au cdg """
        
        # Propage la position absolue du mobile en fonction de sa vitesse qui est en repère mobile 
        self.position = self.position + vehicule2piste(self.vitesse, self.angles[0]) * dt

        # Propage les positions angulaires du mobile (angles de Bryant, soit phi(z), teta(y), psi(x)),
        # en fonction de ses vitesses angulaires qui sont en rd/s """
        self.angles = self.angles + self.vitangul * dt

        # propage la vitesse du mobile (en repère véhicule) en fonction de la force appliquée au cdg
        Omeg_cdg = np.flip(self.vitangul)
        self.vitesse = (self.vitesse
                        + piste2vehicule(self.force_cdg/self.masse, self.angles[0]) * dt
                        + np.cross(self.vitesse, Omeg_cdg) * dt)  # détourne le vecteur vitesse pour le mettre en repère véhicule

        # Propage les vitesses angulaires du mobile en fonction du moment Z appliqués au cdg
        # idem rotations pour l'instant en 2D, seul moment lacet: dérivée lacet = vlacet, et dérivée vlacet = moment / inertie
        # il faudra remettre moment_cdg dans le bon ordre d'ailleurs !
        self.vitangul = self.vitangul + np.array([self.moment_cdg[2]/self.inertie_lacet,0.,0.]) * dt

    def _update_force_et_moment_cdg(self, forces_elements):
        """Calcule les forces et moments appliquées au cdg en repère absolu
        à partir de forces élémentaires appliquées en certains points du mobile et définie par le dictionnaire suivant:
        forces_elements = { (point_application, force_elementaire) }
        où point_application [Float, Float, Float] avec coordonnées en repère mobile
        et force élémentaire [Float, Float, Float] un vecteur 3D en newtons donnée en repère du mobile.

        et calcule self.force_cdg en repère absolu, et self.moment_cdg en repère mobile, égal au repère absolu en 2D.
        """
        force_cdg = np.array([0., 0., 0.])
        moment_cdg = np.array([0., 0., 0.])

        # calcul des forces et moments résultants des forces élémentaires au cdg du mobile, en repère mobile
        for point_application, force_elementaire in forces_elements.items():
            force_cdg = force_cdg + force_elementaire
            moment_cdg = moment_cdg + np.cross(point_application, force_elementaire)

        # forces ramenées en repère piste, puis ajout de la force de gravité dans ce repère:
        force_cdg = vehicule2piste(force_cdg, self.angles[0]) + np.array([0.,0.,self.masse*9.81 ])
        if (abs(force_cdg[2])>1e-5): print("Problème, le mobile a une force Z !", force_cdg[2])  # on vérifie qu'il s'envole pas

        # Ajout force_aero = -Cx * V², en repère véhicule - A VENIR
        self.force_cdg = force_cdg
        self.moment_cdg = moment_cdg

class Kart(Mobile):
    """Classe représentant un kart héritant d'une classe "Mobile" qui a les variables dynamiques

    Les methodes suivantes ont vocation à être appelées par la simulation:
    - init_state()
    - init_parametres(h_cdg, ouverture, transm)  si on veut changer des paramètres sans reset
    - update_state(dt, volant, gaz, frein) pour propager l'état du kart à partir des contrôles

    Et pour un affichage:    
    - profil_absolu() - retourne le profil du kart en repère absolu pour affichage

    """

    def __init__(self, empattement=2.0 , pos_cdg=0.4 , voie_av=0.8 , voie_ar=1.2 ):
        """ Initialise un nouveau kart """

        # Définition paramètres géométrie véhicule, longeurs en mètres
        self.empattement=empattement   # longueur entre axes roues avant et arrière
        self.pos_cdg=pos_cdg       # position longitudinale du cdg en %: 0 sur train arrière, 1 sur train avant.
        self.voie_av=voie_av       # largeur avant du chassis       
        self.voie_ar=voie_ar       # largeur arrière du chassis    
        self.axar=self.empattement*self.pos_cdg  ;   self.axav=self.empattement*(1-self.pos_cdg)  # valeur absolue des absisses des axes roues av / ar
        self.lav= self.voie_av/2                ;   self.lar=self.voie_ar/2                     # ordonnées des angles chassis av/ar
        
        # Variables statiques: Masse, poids et inertie: 
        self.masse=450             # Masse véhicule en Kg
        self.inertie_lacet = self.masse/2*self.empattement**2*((1-self.pos_cdg)**2+self.pos_cdg**2)  # inertie en Lacet, Kgm²
        self.pavg= self.masse*9.81*self.axar/self.empattement/2 ; self.pavd=self.pavg    # calcul des poids statiques du véhicule sur chaque roue 
        self.parg= self.masse*9.81*self.axav/self.empattement/2 ; self.pard=self.parg  

        # appel au constructeur de Mobile avec masse et inertie du kart
        super().__init__(masse=self.masse, inertie_lacet=self.inertie_lacet)

        # et il a quatre roues
        self.roue_avg = Wheel("AVG", self)
        self.roue_avd = Wheel("AVD", self)
        self.roue_arg = Wheel("ARG", self)
        self.roue_ard = Wheel("ARD", self)

        # Variables des contrôle
        self.puis_mot=0.            # commande de puissance motrice (dérive de gaz demandé par simulation)
        self.frein=0          # commande de frein
        self.volant=0.         # commande de volant en degrés

        # Variables des forces et moments
        self.tetag = 0.       # angle de braquage roue gauche en radians
        self.tetad = 0.       # angle de braquage roue droite
        self.v_arbre = 0.     # vitesse de l'arbre arrière issue de la méthode varbre pour télémesur
        self.forces_z = np.array([0., 0., 0., 0.])  # forces verticales sur les 4 roues

        self.favg = np.array([0., 0., 0.]) # force appliquée à la roue gauche en repère véhicule
        self.favd = np.array([0., 0., 0.]) # force appliquée à la roue droite en repère véhicule
        self.farg = np.array([0., 0., 0.]) # force appliquée à la roue arrière gauche en repère véhicule
        self.fard = np.array([0., 0., 0.]) # force appliquée à la roue arrière droite en repère véhicule
        self.gavg = 0 # glissement de la roue avant gauche
        self.gavd = 0 # glissement de la roue avant droite
        self.garg = 0 # glissement de la roue arrière gauche
        self.gard = 0 # glissement de la roue arrière droite

        # initialisation état et paramètres du Kart, modifiables par la simulation
        self.init_state()
        self.init_parametres()

    def init_state(self, position=None, vitesse=None, angles=None, vitangul=None):
        # Arguments optionnels comme dans Mobile.init_state (ligne 23) ; None = valeur par défaut
        if position is None:
            position = np.array([0., 0., 0.])
        if vitesse is None:
            vitesse = np.array([0., 0., 0.])
        if angles is None:
            angles = np.array([0., 0., 0.])
        if vitangul is None:
            vitangul = np.array([0., 0., 0.])
        super().init_state(position=position, vitesse=vitesse, angles=angles, vitangul=vitangul)

    def init_parametres(self, h_cdg=0., ouverture=0, transm=0):
        """ initialise ou met à jour les paramètres réglables du kart
            indépendant du reset, car on peut ainsi modifier les paramètres sans reset pendant une simulation 
            en mode interactif
        """
        self.h_cdg = h_cdg
        self.transm=transm        # Transmission: 0: roues independantes propulsion, 1: pont arrière rigide, 2: 4 Wheels intégral
        self.h_cdg=h_cdg               # hauteur du cdg par rapport au sol en % de l'empattement
        self.ouverture = ouverture   # réglage d'ouverture
        self.coul_chassis = 4        # couleur du chassis (4 = normal)

    @property   
    def profil_absolu(self):    
        """Retourne un profil complet x,y à plotter du véhicule, c'est à dire la liste des vecteurs necessaires 
        au tracé du kart en repère absolu"""

        # Tracons d'abord le profil en repère véhicule
        # D'abord les quatres vecteurs position des angles chassis """
        # premier point = coin ARD près de la roue, deuxième en arg, puis avg puis avd
        X = np.array([[-self.axar, self.lar,0], [-self.axar,-self.lar,0],
                         [ self.axav, -self.lav,0] ,[ self.axav,self.lav,0]])

        # puis on colle les quatres polygones des roues
        X = np.append(X, tourne_vecteur(self.roue_avg.profil(), self.tetag) + self.roue_avg.position, axis=0)
        X = np.append(X, tourne_vecteur(self.roue_avd.profil(), self.tetad) + self.roue_avd.position, axis=0)
        X = np.append(X, self.roue_arg.profil() + self.roue_arg.position, axis=0)
        X = np.append(X, self.roue_ard.profil() + self.roue_ard.position, axis=0)

        # passage en absolu: on tourne la voiture de l'angle lacet, puis on la place à sa position
        X_abs = vehicule2piste(X, self.angles[0]) + np.array([self.position[0], self.position[1], 0.])
        return list(X_abs[:, 0]), list(X_abs[:, 1]) # x,y du profil du kart en repère absolu

    def _update_controles(self, volant, gaz, frein):
        """ Met à jour les contrôles du kart """
        self.puis_mot = 735.5 * gaz    # gaz recu en ch, on passe ici en puissance motrice en watt
        self.frein = frein
        """ calcul des angles de braquage roues avant G et D en repère véhicule en radians
            à partir des commandes angle volant et réglage d'ouverture en deg """
        braquage=np.radians(volant)
        ouv=np.radians(self.ouverture)
        if (abs(braquage)>1e-10):
            R=self.empattement/np.tan(braquage)
            self.tetag =np.arctan(self.empattement/(R-self.roue_avg.position[1]))-ouv
            self.tetad =np.arctan(self.empattement/(R-self.roue_avd.position[1]))+ouv
        else: 
            self.tetag = -ouv
            self.tetad = ouv

    def set_forces_Z_roues(self):
        # calcul de la force verticale appliquée par le sol à chaque roue, donc en général négative car Z vers le bas.
        # d'abord la gravité
        Fzt = np.array([-self.pavg, -self.pavd, -self.parg, -self.pard])
      
        #Calcul couple induit par transfert de masse si h_cdg non nul: en repère véhicule:
        couple_transfert=np.cross(np.array([0.,0.,-self.h_cdg]),piste2vehicule(self.force_cdg, self.angles[0])) # car les forces sont en dessous du cdg
        Fdy = couple_transfert[1]/2./self.empattement ; #  Force dynamique pour compenser le couple Cy entrainé par les Fx
        Fdxav = couple_transfert[0]/2./self.voie_av  ; #  Force dynamique à l'avant pour compenser le couple Cx entrainé par les Fy
        Fdxar = couple_transfert[0]/2./self.voie_ar  ; #  Force dynamique à l'arrière pour compenser le couple Cx entrainé par les Fy
        F_transfert = np.array([-Fdy-Fdxav, -Fdy+Fdxav, Fdy-Fdxar, Fdy+Fdxar])
        Fzt = Fzt + F_transfert

        # Traitement d'un éventuel décollage d'une roue
        # print (f" Avant corrections : Fzt = {Fzt[0]:.3f}   {Fzt[1]:.3f}  {Fzt[2]:.3f}  {Fzt[3]:.3f}total =",Fzt[0]+Fzt[1]+Fzt[2]+Fzt[3])
        # On vérifie qu'aucune roue est tirée vers le bas (Fz>0.), si oui on ajoute du poid aux trois autres
        if (np.count_nonzero(Fzt>0.)==1): # test si une roue décolle
            Nup= np.argmax(Fzt) # index de la roue en l'air
            Fzt[(Nup+1)%4]+=Fzt[Nup]/3. # on transfère un tiers de poid manquant sur chaque autre roue
            Fzt[(Nup+2)%4]+=Fzt[Nup]/3. # en fait faudrait faire au prorata des poids statiques je pense
            Fzt[(Nup+3)%4]+=Fzt[Nup]/3.
            Fzt[Nup]=0.

        # on vérifie si le kart fait un tonneau
        self.coul_chassis=4
        if (np.count_nonzero(Fzt>0.)!=0) :# si malgré ça, une deuxième  roue décolle, tonneau
            self.coul_chassis=3    # Si le kart fait un tonneau, il devient rouge - et on revient au statique pour pas crasher
            # print ("CRASH - TONNEAUX : Fzt =", Fzt)
            Fzt = np.array([-self.pavg, -self.pavd, -self.parg, -self.pard])

        self.forces_z = Fzt
        self.roue_avg.update_fz(Fzt[0])
        self.roue_avd.update_fz(Fzt[1])
        self.roue_arg.update_fz(Fzt[2])
        self.roue_ard.update_fz(Fzt[3])
        return

    def set_vitesses_roues(self):
        # calcul des vitesses des  centres de chaque roue en repère roue, (donc du sol, =vsol)
        # En repère véhicule la vitesse roue est Vcdg + Omega ^ R, donc à tourner pour roues avant
        omega=np.flip(self.vitangul)
        vavg =vehicule2roue(self.vitesse+ np.cross(omega,self.roue_avg.position),self.tetag)
        self.roue_avg.update_vsol(vavg)
        vavd =vehicule2roue(self.vitesse+ np.cross(omega,self.roue_avd.position),self.tetad)
        self.roue_avd.update_vsol(vavd)
        varg = self.vitesse + np.cross(omega,self.roue_arg.position)
        self.roue_arg.update_vsol(varg)
        vard = self.vitesse + np.cross(omega,self.roue_ard.position)
        self.roue_ard.update_vsol(vard)

    def set_varbre(self, puis_mot): 
        """ Renvoie la vitesse de l'arbre AR fixe """
        # Calcul de la vitesse de rotation de l'abre arrière, exprimée sous la forme de la vitesse tangentielle 
        # imposée par l'arbre au point de contact de la roue concernée % au repère roue 
        # fonction d'une puissance sur l'arbre ici en watt
        vg=self.roue_arg.vsol
        vd=self.roue_ard.vsol
        rgg = self.roue_arg.adherence * abs(self.forces_z[2])       # rayon du cone de glissement sec, module de la force max induite par la roue AR concernée
        rgd = self.roue_ard.adherence * abs(self.forces_z[3])
        frein=self.frein
        
        # fonction dont on cherche le zéro pour determiner la vitesse d'arbre vt
        def gg5(vg, vd, rgg, rgd, puis_mot, vt):

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
            gg_value= alphag * rgg * gg_g + alphad * rgd * gg_d - puis_mot * gg_m # -Sigma(F) = Alpha.Rg*Cos(teta) + Id - puis_mot / Vt
            return (gg_value)

        # Recherche du zéro de gg par méthode itérative stupide, Newton marchant moins bien sur cette fonction peu C²
        erreur = 1.
        vt =min(-0.0001, -0.5*(vg[0]+vd[0]))   # on part d'une vitesse estimée moyenne pas trop con, toujours négative
        vtmin = vt ; vtmax=0.
        boucle=0
        while (gg5(vg, vd, rgg, rgd, puis_mot, vtmin)>0.)and(boucle<100) :
            boucle+=1
            vtmin = 2. * vtmin  # recherche d'un vtmin tel que gg(vtmin) <0.
        if (boucle>99): print("      WARNING - BOUCLE 100 pour Vtmin =", Vtmin)

        boucle=0
        while (abs(erreur) >0.000001*abs(vt)) and (boucle<100) :
            boucle+=1
            vt = 0.5 *(vtmin+vtmax)
            if gg5(vg, vd, rgg, rgd, puis_mot, vt) >0. :
                vtmax=vt
            else:
                vtmin=vt
            erreur = vtmax-vtmin
        if (vt>0.):
            print("      WARNING - ANNULATION VT >0.")
            vt=0

        # application du frein:
        match self.frein:  
            case 0 : vtf=vt
            case 1 : vtf=0.98*vt    # Freinage: 1 = 98%, léger lineaire
            case 2 : vtf=0.96*vt    # Freinage: 1 = 96%, fort linéraire
            case 3 : vtf=0.9*vt
            case 4:  vtf=0.1*vt

        self.v_arbre = vtf
        return

    def set_forces_roues(self):
        """ Calcul des forces d'interaction roue-piste en repère véhicule """

        # Calcul des forces verticales sur les quatre roues
        self.set_forces_Z_roues()

        # Calcul des vitesses des roues en repère véhicule
        self.set_vitesses_roues()

        # Gestion des types de transmissions
        if (self.transm==0):       
            # Cas roues indépendantes....
            # et propulsion, donc puis_mot sur les roues arrières, qu'on envoie en watt
            self.roue_avg.update_controles(False, 0., self.frein)
            self.roue_avd.update_controles(False, 0., self.frein)
            self.roue_arg.update_controles(False, self.puis_mot/2.0, self.frein)
            self.roue_ard.update_controles(False, self.puis_mot/2.0, self.frein)

        elif (self.transm==1):     
            # Cas d'un pont arrière rigide, roues avant libres
            self.set_varbre(self.puis_mot)   # un seul appel du calcul de la vitesse d'arbre, c'est mieux
            self.roue_avg.update_controles(False, 0., self.frein)
            self.roue_avd.update_controles(False, 0., self.frein)
            self.roue_arg.update_controles(self.v_arbre, 0., 0.)
            self.roue_ard.update_controles(self.v_arbre, 0., 0.)

        else:  
            # Cas d'un 4 Wheels intégral, quatre roues asservies à une même vitesse de rotation
            # Calcul de la vitesse de rotation de l'arbre arrière, au prorata de la puissance prise à l'AR,
            self.set_varbre(self.puis_mot*(1.-self.pos_cdg))  
            # vitesse imposée ensuite aux quatres roues (sinon faut faire un Varbre 4WD dédié)
            # ce qui fait un truc bizarre, le Fx des roues avant varie avec H cdg en zone linéaire ???            
            self.roue_avg.update_controles(self.v_arbre, 0., 0.)
            self.roue_avd.update_controles(self.v_arbre, 0., 0.)
            self.roue_arg.update_controles(self.v_arbre, 0., 0.)
            self.roue_ard.update_controles(self.v_arbre, 0., 0.)

        #favg=[0.,0.,0.] ; favd=[0.,0.,0.] ; farg=[0.,0.,0.] ; fard=[0.,0.,0.]
        self.favg, self.gavg = self.roue_avg.force()
        self.favg=roue2vehicule(self.favg, self.tetag)
        self.favd, self.gavd = self.roue_avd.force()
        self.favd=roue2vehicule(self.favd, self.tetad)
        self.farg, self.garg = self.roue_arg.force()
        self.fard, self.gard = self.roue_ard.force()

    def _update_force_et_moment_cdg(self):
        """Calcule les forces et moments appliquées au cdg du Kart en repère absolu à partir des forces roues.
        Cette méthode spécialise update_force_et_moment_cdg de la classe Mobile.
        
               et qui recoie en paramètre les forces élémentaires appliquées en certains points du mobile

        et retourne force_cdg en repère absolu, et moment_cdg en repère mobile , égal au repère absolu en 2D.          
        """
        # calcul des forces roues en repère véhicule
        self.set_forces_roues()
                            
        # construction du dictionnaire des forces élémentaires appliquées en certains points du mobile
        forces_elements = {
            tuple(self.roue_avg.position): self.favg,
            tuple(self.roue_avd.position): self.favd,
            tuple(self.roue_arg.position): self.farg,
            tuple(self.roue_ard.position): self.fard,
        }
        # appel à la méthode générique de Mobile qui met à jour self.force_cdg et self.moment_cdg
        super()._update_force_et_moment_cdg(forces_elements)

    def update_state(self, dt, volant, gaz, frein):
        """ Seule méthode à appeler par une simulation pour propager l'état du kart
         sur un pas de temps dt en fonction des contrôles
         """

        # Application des contrôles
        self._update_controles(volant, gaz, frein)

        # Propagation de la dynamique
        self._update_dynamique(dt)

        # Calcul des forces et moments appliqués au cdg dans le nouvel état
        self._update_force_et_moment_cdg()