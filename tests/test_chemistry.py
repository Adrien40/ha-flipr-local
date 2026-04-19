from custom_components.flipr_local.chemistry import (
    compute_active_chlorine,
    compute_isl,
    get_mv_from_input,
    compute_flipr_active_chlorine,
    compute_flipr_theoretical_orp,
)

# ==========================================
# TESTS : Indice de Langelier (ISL)
# ==========================================


def test_compute_isl_robustness():
    """Vérifie que l'ISL ne plante pas (renvoie None) si on lui donne une valeur nulle."""
    assert compute_isl(temp=25, ph=7.2, tac=0, th=200, tds=1000) is None
    assert compute_isl(temp=25, ph=7.2, tac=100, th=0, tds=1000) is None


def test_isl_precision():
    """Vérifie le calcul de l'indice de Langelier avec des valeurs standards."""
    isl = compute_isl(temp=25, ph=7.5, tac=100, th=200, tds=1000)
    assert isl is not None
    assert -0.3 <= isl <= 0.3  # Eau parfaitement équilibrée


# ==========================================
# TESTS : Conversion des entrées utilisateur
# ==========================================


def test_hybrid_input_logic():
    """Vérifie que le système distingue correctement un pH d'une valeur mV."""
    # Cas d'un utilisateur saisissant un pH (ex: 7.02)
    mv_converted = get_mv_from_input(7.02)
    assert 1500 < mv_converted < 1800  # La conversion usine donne environ 1640 mV

    # Cas d'un utilisateur saisissant directement des mV (ex: 1600)
    mv_direct = get_mv_from_input(1600.0)
    assert mv_direct == 1600.0


# ==========================================
# TESTS : Le VRAI Chlore Actif (Scientifique)
# ==========================================


def test_active_chlorine_logic():
    """Vérifie la cohérence chimique du VRAI chlore actif selon le pH et le CyA."""
    # À ORP égal (650mV), le chlore actif doit baisser si le pH augmente
    chlore_ph_bas = compute_active_chlorine(orp=650, ph=7.0, temp=25, cya=40)
    chlore_ph_haut = compute_active_chlorine(orp=650, ph=8.0, temp=25, cya=40)
    assert chlore_ph_bas > chlore_ph_haut

    # À ORP égal, le chlore actif doit s'effondrer si le stabilisant (CyA) augmente
    chlore_cya_bas = compute_active_chlorine(orp=650, ph=7.4, temp=25, cya=20)
    chlore_cya_haut = compute_active_chlorine(orp=650, ph=7.4, temp=25, cya=150)
    assert chlore_cya_bas > chlore_cya_haut


def test_chemistry_extreme_temperatures():
    """Vérifie que les formules ne plantent pas avec des températures extrêmes."""
    assert compute_active_chlorine(orp=700, ph=7.2, temp=2.0, cya=40) is not None
    assert compute_isl(temp=35, ph=7.4, tac=120, th=250, tds=1000) is not None


# ==========================================
# TESTS : Algorithmes Reverse-Engineered Flipr
# ==========================================


def test_flipr_theoretical_orp():
    """Vérifie que l'algorithme de l'ORP cible de l'appli Flipr n'est pas altéré."""
    # Test validé avec les données bandelettes de l'utilisateur (pH 7.4, CyA 40, Libre 2 -> 623 mV)
    orp_cible = compute_flipr_theoretical_orp(ph=7.4, cya=40, chlore_libre_cible=2.0)
    assert orp_cible == 623


def test_flipr_fake_active_chlorine_lazy_mode():
    """Vérifie le 'mode fainéant' de l'appli Flipr (Chlore Actif = Chlore Libre)."""
    # Dans des conditions standards ou imprécises, le ratio est de 1
    actif = compute_flipr_active_chlorine(ph=7.4, cya=40, chlore_libre=2.0)
    assert actif == 2.0


def test_flipr_fake_active_chlorine_acid_multipliers():
    """Vérifie que l'intégration reproduit bien les bugs de multiplicateurs acides de l'appli."""
    # Bug constaté le jour 1 : pH 7.0 et CyA 40 -> Ratio de 2.38
    actif_7_0 = compute_flipr_active_chlorine(ph=7.0, cya=40, chlore_libre=2.0)
    assert actif_7_0 == 4.76

    # Bug constaté le jour 2 : pH 6.4 et CyA 40 -> Ratio de 1.99
    actif_6_4 = compute_flipr_active_chlorine(ph=6.4, cya=40, chlore_libre=0.5)
    assert actif_6_4 == 1.0  # (0.5 * 1.99 = 0.995 arrondi à 1.0)
