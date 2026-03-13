import numpy as np
try:
    from .utils import *
except ImportError:
    from utils import *

class Wheel:
    """   Classe représentant une roue avec ses propriétés physiques et comportementales   """
    
    def __init__(self, which_roue, kart):
        """Initialise une nouvelle roue, suivant which_roue="AVG" ou "ARG" ou "AVD" ou "ARD" """
        self.which_roue = which_roue
        self.kart = kart  # Référence vers l'instance de kart

        # on initialise les variables géométriques de la roue
        self.rayon_roue_moyen=0.30      #rayon roue moyen. Les tailles roues sont ensuite % au poid statique
        self.largeur_roue_moyen=0.2     # Largeur roue moyenne
        self.adherence= 1.              # adherence du pneu, 1=cone de frottement à 45°

        # on initialise les variables de contrôle de la roue
        self.vsol = np.array([0.,0.,0.])    # vitesse de la roue par rapport au sol en repère roue (m/s) (et pas vitesse du sol !)
        self.puis_app = 0.                       # puissance appliquée à la roue en watt
        self.frein = 0.                     # 0=pas de freinage, 1=freinage linéaire, 2=freinage saturé, 3=freinage bloqué
        self.varbre = 0.                    # vitesse tangentielle du point de contact roue au sol imposée par un arbre (m/s)

        # self.force = np.array([0.,0.,0.])   # force appliquée par la roue au véhicule en repère véhicule (N)
                                              # c'est une methode/properties, donc pas besoin de l'initialiser
        self.glisse = 0                      # glisse: 0=roue à l'arret, 1=zone linéaire, 2=saturée par couple, 3=saturée par dérive

    @property
    def rayon(self):
        """Retourne le rayon de la roue suivant which="AV" ou "AR" """
        # Les dimensions de roue (rayon et largeur) sont définis proportionnels à la charge statique
        if self.which_roue[:2] == "AV":
            return 2*self.rayon_roue_moyen*self.kart.axar/self.kart.empattement
        elif self.which_roue[:2] == "AR":
            return 2*self.rayon_roue_moyen*self.kart.axav/self.kart.empattement
        else:
            raise ValueError(f"Roue invalide: {self.which_roue}")

    @property
    def largeur(self):
        """Retourne la largeur de la roue suivant which="AV" ou "AR" """
        if self.which_roue[:2] == "AV":
            return 2*self.largeur_roue_moyen*self.kart.axar/self.kart.empattement
        elif self.which_roue[:2] == "AR":
            return 2*self.largeur_roue_moyen*self.kart.axav/self.kart.empattement
        else:
            raise ValueError(f"Roue invalide: {self.which_roue}")

    @property
    def position(self):
        """Retourne le vecteur position I/F roue/sol en repère véhicules (ex ravg)"""
        v=self.largeur_roue_moyen/2    # Ecartement entre angle chassis et bord roue
        if self.which_roue == "AVG":
            x= self.kart.axav
            y = -self.kart.lav-v-self.largeur_roue_moyen/2
        elif self.which_roue == "AVD":
            x= self.kart.axav
            y = self.kart.lav+v+self.largeur_roue_moyen/2
        elif self.which_roue == "ARG":
            x= -self.kart.axar
            y = -self.kart.lar-v-self.largeur_roue_moyen/2
        elif self.which_roue == "ARD":
            x= -self.kart.axar
            y = self.kart.lar+v+self.largeur_roue_moyen/2
        return np.array([x, y, 0])
        
    def profil(self):
        """Retourne un tracé rectangles roue centrés en (0,0), milieu du bord intérieur de la roue"""
        r = self.rayon
        l = self.largeur
        if self.which_roue[2] == "G":
            return np.array([[-r,l/2,0.], [-r,-l/2,0], [r,-l/2,0],[r,l/2,0]], dtype=float) 
        elif self.which_roue[2] == "D":
            return tourne_vecteur(np.array([[-r,l/2,0.], [-r,-l/2,0], [r,-l/2,0],[r,l/2,0]], dtype=float), np.pi) 
        else:
            raise ValueError(f"Roue invalide: {self.which_roue}")
    

    def update_vsol(self, vsol):
        """ Met à jour la vitesse du centre de la roue par rapport au sol en repère roue """
        self.vsol = vsol

    def update_fz(self, fz):
        """ Met à jour la force verticale appliquée par le sol à la roue """
        if (fz>0.): print ("ERREUR: fz > 0 pour la roue", self.which_roue, "fz =", fz)
        self.fz = fz

    def update_controles(self, varbre, puis_app, frein):
        """ Met à jour les controles de la roue """
        # varbre est une éventuelle vitesse tangentielle imposée par une transmission
        # dont nulle=false si la roue est libre, ou  non nul si une vitesse arbre est imposée. puis_app est alors nul
        # puis_app est recu ici en watt
        if varbre and puis_app : print ("ERREUR DE CONTROLE ROUE: Varbre =", varbre, "puis_app =", puis_app)
        self.varbre = varbre
        self.puis_app = puis_app
        self.frein = frein


    def force(self):  # ex adher_roue
        # renvoie la force d'adhérence au sol d'une roue en repère roue, donc qui sera appliquée par la roue au véhicule,
        # cas général: Si Varbre=0. c'est une roue libre, sinon c'est une roue sur arbre arrière ou 4WD

        if not(self.varbre): # cas d'une roue libre, avec puis_app ou frein
            if not(self.frein):
                return self.force_roue_libre()
            else:         # roue libre freinée, on calcule la vitesse imposée par le frein
                match self.frein:
                    case 1 : vf=-0.98*self.vsol[0]   # Freinage: 1 = 98%, on reste linéaire
                    case 2 : vf=-0.96*self.vsol[0]   # Freinage: 1 = 96%, on reste juste linéaire
                    case 3 : vf=-0.90*self.vsol[0]   # Freinage: 1 = 90%, on sature la roue
                    case 4 : vf=0.             # Freinage: 1 = 98%, on bloque la roue
                return self.force_roue_V_force(vf)
        else:
            return self.force_roue_V_force(self.varbre)

    def force_roue_libre(self):
        # En fonction de la vitesse du sol en repère roue, des puis_app (ici en W), et de la fz sur cette roue
        # Renvoie aussi l'état de glisse: Roue à l'arret=0, zone linéaire = 1, saturée par couple = 2, saturée par dérive = 3
        force=[0.,0.,self.fz]    #le pneu renvera Fx=0 si pas de  puis_app et fz en z (négative, vers le haut donc)

        Rg = self.adherence * abs(self.fz)       # rayon du cone de glissement sec, module de la force max donc
        nVsol= (self.vsol[0]**2+self.vsol[1]**2)**0.5
        Vmin=0.4
        d = 0. if (nVsol<0.01) else np.arctan(self.vsol[1]/self.vsol[0])  # dérive en radians
        d_lin = 5./180.*np.pi            # zone de comportement linéaire
        sens = np.sign(self.vsol[0])    # sens de la vitesse roue par rapport au sol en X, 1 ou -1

        # fonction utilisée par force_roue_libre uniquement
        def inversf(ycible, d):
            # Donne le zéro de la fonction f(teta) = ycible - sinus(teta) ( cos(d) + sin(d) tan(teta))
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

        # calcul de la force d'adhérence dans les differents cas de figure
        if (self.fz>=0.):            # Roue "en l'air" donc
            force=[0.,0.,0.]
            glisse=0
        elif nVsol<Vmin:
            if self.puis_app<1.:        # zone de très basse vitesse (<1m/s) sans gaz donc avant arret
                force=[-100*self.vsol[0], -1000*self.vsol[1], self.fz]    # on met une sorte de freinage linéaire pour arret
                glisse=0
            else:                  # zone de très basse vitesse (<1m/s) avec gaz donc il faut décoller de l'arret
                force=[Rg, -1000*self.vsol[1], self.fz]
                glisse = 2
        elif abs(d) < d_lin:       # zone de comportement lineaire
            # Calcul de Fn:
            force[1]=-sens*d/d_lin*Rg
            # calcul de Ft: Calculons Pmax possible avant de saturer le pneu:
            t1 = (d_lin**2-d**2)**0.5 / d_lin   # = sinus teta
            t2 = t1 * Rg                            # = sinus teta * Rg; c'est le Ft max linéaire
            Pmax = t2 * nVsol * np.cos(d)            # = sinus teta * Rg * Vsol * Cos(d)
            if (self.puis_app<Pmax):   # la puissance appliquée ne sature pas le pneu:
                force[0]= self.puis_app/ ( nVsol * np.cos(d) )     # donc on ajoute Ft et on touche pas à Fn
                glisse=1
            else:            # la puissance sature le pneu
                ycible = self.puis_app / (Rg * nVsol )
                teta = inversf(ycible,abs(d))
                force[0] = np.sin(teta) * Rg
                force[1] = -np.cos(teta) * np.sign(self.vsol[1])*Rg
                glisse=2
        else:              # C'est la dérive qui sature le pneu
            ycible = self.puis_app / (Rg * nVsol )              # valeur de sinus teta ( cos(d) + sin(d) tan(teta)) qu'il faut inverser, dans R+
            if (ycible<0.01):
                teta=0.
            else:
                teta = inversf(ycible,abs(d))
            force[0] = np.sin(teta) * Rg
            force[1] = - np.cos(teta) * np.sign(self.vsol[1])*Rg
            glisse=3
        return force, glisse

    def force_roue_V_force(self, vf):
        # renvoie la force d'adhérence d'une roue à vitesse forcée (ex: AR sur un pont rigide, ou roue freiné) 
        # qui sera appliquée au véhicule, en repère roue,
        # en fonction de la vitesse tangentielle vf imposée par le frein ou l'arbre, du point de contact roue % sol en repère roue
        # et de la force verticale appliqués à cette roue uniquement
        # Renvoie aussi l'info de glisse: Roue à l'arret=0, zone linéaire = 1, saturée par couple = 2, saturée par dérive = 3
        force=[0.,0.,self.fz]    #le pneu renvera Fx, Fy et fz en z (négative, vers le haut donc)

        # rayon du cone de glissement sec, module de la force max donc
        Rg = self.adherence * abs(self.fz)      

        # La vitesse de glisse du point de contact pneu % sol 
        #  est la somme de la vitesse tangentielle vf imposée et de la vitesse d'entrainement du centre roue
        Vg =  self.vsol + np.array([vf,0.,0.])      # d'où un glissement dans le plan du sol, du signe de la force qui en résulte sur le véhicule, <0 roue extérieure
        nVg= norme_vecteur(Vg)            # vitesse de glisse totale du point de contcat
        nVsol=norme_vecteur(self.vsol)
        sVy = np.sign(Vg[1])
        if not(sVy) : sVy = 1.   # signe de Vy, forcé à +1 si Vy nul.

        if (self.fz>=0.):            # Roue "en l'air" donc
            force=[0.,0.,0.]
            glisse=0
        elif (nVsol<=0.1)and(abs(vf)<=0.1):  # zone de très basse vitesse (<1m/s) sans gaz avant arret
            force=[-1000*self.vsol[0], -1000*self.vsol[1], self.fz]                 # on met une sorte de freinage linéaire pour arret
            glisse=0
        elif (nVsol<=0.3)and(abs(vf)>0.1):   # centre Roue à l'arret mais il y a vf
            force=[Rg, -1000*self.vsol[1], self.fz]   # pour décoller de l'arret complet après remise de gaz.
            glisse = 2
        else:
            teta=-np.pi/2 if not(Vg[1]) else np.arctan(Vg[0]/Vg[1])
            alpha = min(1., nVg/(0.05*nVsol))  # alpha < 1 en zone de comportement lineaire, glisssement < 5% de Vsol, cohérent de 3° dérive roue libre
            force[0]= -  Rg * np.sin(teta) * alpha* sVy
            force[1]= - Rg * np.cos(teta) * alpha * sVy
            glisse=1 if (alpha<1.) else 3    # le pneu saturé si alpha >=1.
        return force, glisse

