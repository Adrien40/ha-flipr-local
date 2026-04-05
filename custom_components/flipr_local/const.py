# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Constantes pour l'intégration Flipr Local."""

DOMAIN = "flipr_local"

# Configuration
CONF_MAC_ADDRESS = "mac_address"
CONF_USE_GATEWAY = "use_gateway"

# Calibration pH
CONF_PH_CALIB_4 = "ph_calib_4"
CONF_PH_CALIB_7 = "ph_calib_7"
CONF_PH_REF_7 = "ph_ref_7"
CONF_PH_REF_4 = "ph_ref_4"

# Seuils d'alerte
CONF_PH_MIN = "ph_min"
CONF_PH_MAX = "ph_max"
CONF_ORP_MIN = "orp_min"
CONF_TEMP_MIN = "temp_min"
CONF_TEMP_MAX = "temp_max"

# Chimie
CONF_TAC = "tac"
CONF_TH = "th"
CONF_TDS = "tds"
CONF_CYA = "cya"

# Intervalle
CONF_SCAN_INTERVAL = "scan_interval"

CONF_CHLORE_MODEL = "chlore_model"

# UUIDs Bluetooth
FLIPR_CHARACTERISTIC_UUID = "00000006-0000-1000-8000-00805f9b34fb"
FLIPR_COMMAND_UUID = "0000940d-0000-1000-8000-00805f9b34fb"

def get_flipr_model(name: str | None) -> str:
    """Détermine le modèle du Flipr en fonction de son nom."""
    if not name:
        return "Flipr"
    name_upper = name.upper()
    if name_upper.startswith("F3") or ("ANALYS" in name_upper and "3" in name_upper):
        return "Flipr AnalysR 3"
    if name_upper.startswith("F2") or ("ANALYS" in name_upper and "2" in name_upper):
        return "Flipr AnalysR 2"
    if name_upper.startswith("FLIPR 01"):
        return "Flipr Start"
    return "Flipr"