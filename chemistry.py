# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import math
import logging

_LOGGER = logging.getLogger(__name__)

def compute_isl(temp, ph, tac, th, tds):
    """Calcule l'Indice de Langelier (ISL). Renvoie None si données invalides."""
    if not all(v is not None and v > 0 for v in [temp, tac, th, tds]) or ph is None:
        return None
        
    try:
        A = (math.log10(tds) - 1) / 10
        B = -13.12 * math.log10(temp + 273.15) + 34.55
        C = math.log10(th) - 0.4
        D = math.log10(tac)
        phs = (9.3 + A + B) - (C + D)
        return round(ph - phs, 2)
    except Exception as e:
        _LOGGER.error("Erreur calcul ISL : %s", e)
        return None

def compute_active_chlorine(orp, ph, temp, cya=40, model="stabilized"):
    """Calcule le Chlore Actif en rendant tous les modèles dynamiques via le CyA."""
    if not all(v is not None for v in [orp, ph, temp]):
        return None
        
    try:
        # 1. CAS PARTICULIER : SEL / NERNST (Jamais de CyA ici)
        if model == "nernst":
            resultat = math.exp((orp + (ph - 7.4) * 40 - 655) / 32)
            return round(max(0.0, min(resultat, 15.0)), 2)

        # 2. CALCUL DE LA BASE SELON LE PROFIL
        if model == "bromine":
            # Modèle Brome
            base_resultat = math.exp((orp + (ph - 7.4) * 40 - 655) / 32) * 2.25
            
        elif model == "custom":
            # Ta Calibration Personnalisée (Modèle Adrien / WaterAir Eva 7)
            base_resultat = math.exp(-6.1715 + (0.1899 * ph) + (0.0081 * orp) + (0.0217 * temp))
            
        else: # "stabilized"
            # Modèle Générique Stabilisé
            base_resultat = math.exp(-7.5 + (0.18 * ph) + (0.009 * orp) + (0.02 * temp))

        # 3. APPLICATION DU FACTEUR D'ÉVOLUTION DU STABILISANT (CyA)
        # On compare le taux actuel au taux de référence (40 mg/L)
        _cya = max(5.0, min(float(cya), 150.0))
        ratio_evolution = 40.0 / _cya
        
        final_result = base_resultat * ratio_evolution
        
        return round(max(0.0, min(final_result, 15.0)), 2)
        
    except Exception as e:
        _LOGGER.error("Erreur calcul Désinfectant : %s", e)
        return None