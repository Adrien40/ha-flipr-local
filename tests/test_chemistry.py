# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import math

import pytest

from custom_components.flipr_local.chemistry import (
    compute_active_chlorine_from_fc,
    compute_isl,
    compute_ph_equilibrium,
    estimate_free_chlorine,
    get_mv_from_input,
)

# ==========================================
# Conversion des entrées utilisateur (pH <-> mV)
# ==========================================


def test_hybrid_input_logic():
    """Distingue une saisie en pH d'une saisie directe en mV."""
    # Une valeur dans [2, 14] est interprétée comme un pH et convertie en mV.
    mv_converted = get_mv_from_input(7.02)
    assert 1700 < mv_converted < 1900  # conversion usine ~1798 mV

    # Une valeur dans [500, 3000] est déjà en mV : passthrough.
    assert get_mv_from_input(1600.0) == 1600.0


def test_get_mv_accepts_comma_and_string():
    """Accepte les nombres sous forme de chaîne."""
    assert get_mv_from_input("7.02") == get_mv_from_input(7.02)


def test_get_mv_rejects_out_of_range():
    """Rejette les valeurs hors des plages pH et mV."""
    with pytest.raises(ValueError):
        get_mv_from_input(20.0)  # ni pH plausible, ni mV plausible
    with pytest.raises(ValueError):
        get_mv_from_input(4000.0)  # mV hors borne
    with pytest.raises(ValueError):
        get_mv_from_input("not-a-number")


# ==========================================
# Indice de saturation de Langelier (ISL) & pH d'équilibre
# ==========================================


def test_compute_isl_robustness():
    """Renvoie None si un paramètre clé (TAC/TH/TDS) est nul ou négatif."""
    assert compute_isl(temp=25, ph=7.2, tac=0, th=200, tds=1000) is None
    assert compute_isl(temp=25, ph=7.2, tac=100, th=0, tds=1000) is None
    assert compute_isl(temp=25, ph=7.2, tac=100, th=200, tds=0) is None


def test_isl_balanced_water():
    """Une eau standard ressort dans la bande d'équilibre (±0.3)."""
    isl = compute_isl(temp=25, ph=7.5, tac=100, th=200, tds=1000)
    assert isl is not None
    assert -0.3 <= isl <= 0.3


def test_isl_extreme_temperature_does_not_crash():
    """Les températures élevées ne font pas planter le calcul."""
    assert compute_isl(temp=35, ph=7.4, tac=120, th=250, tds=1000) is not None


def test_isl_matches_equilibrium_ph():
    """ISL = pH mesuré - pH d'équilibre, par construction."""
    equilibrium = compute_ph_equilibrium(temp=25, tac=100, th=200, tds=1000)
    isl = compute_isl(temp=25, ph=7.5, tac=100, th=200, tds=1000)
    assert equilibrium is not None and isl is not None
    assert isl == pytest.approx(round(7.5 - equilibrium, 2), abs=0.01)


def test_equilibrium_ph_robustness():
    """pH d'équilibre renvoie None sur des paramètres invalides."""
    assert compute_ph_equilibrium(temp=25, tac=0, th=200, tds=1000) is None


# ==========================================
# Estimation du chlore libre à partir de l'ORP
# ==========================================


def test_free_chlorine_increases_with_orp():
    """À pH et CyA constants, un ORP plus élevé donne plus de chlore libre."""
    low = estimate_free_chlorine(orp=415, ph=7.4, cya=40)
    high = estimate_free_chlorine(orp=750, ph=7.4, cya=40)
    assert low is not None and high is not None
    assert high > low


def test_free_chlorine_cya_amplification():
    """En dessous de 40 mg/L de CyA, aucun bonus (plancher à 1.0) ;
    au-dessus, l'estimation augmente proportionnellement."""
    fc_20 = estimate_free_chlorine(orp=650, ph=7.4, cya=20)
    fc_40 = estimate_free_chlorine(orp=650, ph=7.4, cya=40)
    fc_80 = estimate_free_chlorine(orp=650, ph=7.4, cya=80)
    assert fc_20 == fc_40  # plancher : pas de pénalité sous la référence
    assert fc_80 > fc_40  # au-delà de 40, la demande en chlore augmente


def test_free_chlorine_is_clamped():
    """Le chlore libre estimé reste borné dans [0, 15] ppm."""
    saturated = estimate_free_chlorine(orp=1000, ph=7.0, cya=120)
    assert saturated == 15.0


# ==========================================
# Chlore actif (HOCl) à partir du chlore libre
# ==========================================


def test_active_chlorine_none_and_zero_inputs():
    """Gère proprement les entrées nulle, zéro et négative."""
    assert compute_active_chlorine_from_fc(None, ph=7.2, temp_c=25, cya=40) is None
    assert compute_active_chlorine_from_fc(0.0, ph=7.2, temp_c=25, cya=40) == 0.0
    assert compute_active_chlorine_from_fc(-1.0, ph=7.2, temp_c=25, cya=40) == 0.0


def test_active_chlorine_decreases_with_ph():
    """À chlore libre constant, la fraction active (HOCl) chute quand le pH monte."""
    low_ph = compute_active_chlorine_from_fc(2.0, ph=7.0, temp_c=25, cya=40)
    high_ph = compute_active_chlorine_from_fc(2.0, ph=8.0, temp_c=25, cya=40)
    assert low_ph > high_ph


def test_active_chlorine_decreases_with_cya():
    """À chlore libre constant, plus de stabilisant => moins de chlore actif."""
    low_cya = compute_active_chlorine_from_fc(2.0, ph=7.4, temp_c=25, cya=20)
    high_cya = compute_active_chlorine_from_fc(2.0, ph=7.4, temp_c=25, cya=150)
    assert low_cya > high_cya


def test_active_chlorine_extreme_temperature_does_not_crash():
    """Une eau très froide ne fait pas planter le calcul HOCl."""
    fc = estimate_free_chlorine(orp=700, ph=7.2, cya=40)
    assert compute_active_chlorine_from_fc(fc, ph=7.2, temp_c=2.0, cya=40) is not None


# ==========================================
# Chaîne réaliste : estimation -> chlore actif
# ==========================================


def test_chain_active_chlorine_drops_with_ph():
    """Bout en bout (ORP -> FC -> HOCl), le chlore actif baisse quand le pH monte."""
    fc_low = estimate_free_chlorine(orp=650, ph=7.0, cya=40)
    fc_high = estimate_free_chlorine(orp=650, ph=8.0, cya=40)
    active_low = compute_active_chlorine_from_fc(fc_low, ph=7.0, temp_c=25, cya=40)
    active_high = compute_active_chlorine_from_fc(fc_high, ph=8.0, temp_c=25, cya=40)
    assert active_low > active_high
    assert not math.isnan(active_low)
