# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import math
import logging

_LOGGER = logging.getLogger(__name__)

def get_mv_from_input(val):
    try:
        val_f = float(val)
        if val_f < 20.0: 
            return round((val_f - 22.2083) / -0.0084494)
        return val_f
    except (ValueError, TypeError): 
        return 1600.0

def compute_ph_equilibrium(temp, tac, th, tds):
    if not all(v is not None and v > 0 for v in [temp, tac, th, tds]):
        return None
    try:
        A = (math.log10(tds) - 1) / 10
        B = -13.12 * math.log10(temp + 273.15) + 34.55
        C = math.log10(th) - 0.4
        D = math.log10(tac)
        return round((9.3 + A + B) - (C + D), 2)
    except Exception as e:
        _LOGGER.error("Erreur calcul pH d'équilibre : %s", e)
        return None

def compute_isl(temp, ph, tac, th, tds):
    phs = compute_ph_equilibrium(temp, tac, th, tds)
    if phs is None or ph is None:
        return None
    return round(ph - phs, 2)

def compute_active_chlorine(orp, ph, temp, cya=40, model="stabilized"):
    if not all(v is not None for v in [orp, ph, temp]):
        return None
        
    try:
        if model == "nernst":
            resultat = math.exp((orp + (ph - 7.4) * 40 - 655) / 32)
            return round(max(0.0, min(resultat, 15.0)), 2)

        if model == "bromine":
            base_resultat = math.exp((orp + (ph - 7.4) * 40 - 655) / 32) * 2.25
        elif model == "custom":
            base_resultat = math.exp(-6.1715 + (0.1899 * ph) + (0.0081 * orp) + (0.0217 * temp))
        else:
            base_resultat = math.exp(-7.5 + (0.18 * ph) + (0.009 * orp) + (0.02 * temp))

        _cya = max(5.0, min(float(cya), 150.0))
        ratio_evolution = 40.0 / _cya
        
        final_result = base_resultat * ratio_evolution
        return round(max(0.0, min(final_result, 15.0)), 2)
        
    except Exception as e:
        _LOGGER.error("Erreur lors du calcul du désinfectant : %s", e)
        return None