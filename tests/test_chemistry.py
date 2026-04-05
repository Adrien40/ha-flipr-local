import pytest
import math
from custom_components.flipr_local.chemistry import compute_isl, compute_active_chlorine

def test_compute_isl_robustness():
    """Vérifie que l'ISL ne plante pas (renvoie None) si on lui donne une valeur nulle."""
    assert compute_isl(temp=25, ph=7.2, tac=0, th=200, tds=1000) is None

def test_compute_active_chlorine_model():
    """Vérifie que notre formule sur-mesure ne bouge pas."""
    # Test avec tes valeurs réelles (pH 7.21, ORP 611, Temp 15.78)
    chlore = compute_active_chlorine(orp=611, ph=7.21, temp=15.78)
    # L'arrondi du test doit faire exactement 1.63
    assert chlore == 1.63
