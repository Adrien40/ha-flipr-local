# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

import logging, asyncio
from datetime import timedelta
import homeassistant.util.dt as dt_util
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth import async_ble_device_from_address, async_last_service_info
from .chemistry import compute_isl, compute_active_chlorine, get_mv_from_input, compute_ph_equilibrium
from .const import (
    DOMAIN, CONF_MAC_ADDRESS, CONF_PH_CALIB_4, CONF_PH_CALIB_7,
    CONF_PH_REF_7, CONF_PH_REF_4, CONF_CYA, CONF_CHLORE_MODEL,
    FLIPR_CHARACTERISTIC_UUID
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select"]

async def update_listener(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    mac = entry.data[CONF_MAC_ADDRESS]
    
    if mac not in hass.data[DOMAIN]:
        hass.data[DOMAIN][mac] = {}
        
    # FIX ANTI-INCONNU : On récupère la mémoire de l'instant précédent
    last_data = hass.data[DOMAIN][mac].get("last_data", {})

    entry.async_on_unload(entry.add_update_listener(update_listener))

    async def async_update_data():
        nonlocal last_data
        
        try:
            async with asyncio.timeout(60):
                device = async_ble_device_from_address(hass, mac, connectable=True)
                
                if not device:
                    if last_data: return last_data
                    raise UpdateFailed("Flipr hors de portée Bluetooth")

                client = await establish_connection(BleakClient, device, mac, max_attempts=3)
                try:
                    data = await client.read_gatt_char(FLIPR_CHARACTERISTIC_UUID)
                finally:
                    await client.disconnect()
                
        except Exception as err:
            if last_data: return last_data
            raise UpdateFailed(f"Erreur de communication : {err}")

        hex_frame = data.hex().upper()
        if data == bytearray(13) or hex_frame.startswith("0000"):
            if last_data: return last_data
            raise UpdateFailed("Sonde en veille ou trame vide")

        raw_c4 = entry.options.get(CONF_PH_CALIB_4) or entry.data.get(CONF_PH_CALIB_4, 1900.0)
        raw_c7 = entry.options.get(CONF_PH_CALIB_7) or entry.data.get(CONF_PH_CALIB_7, 1600.0)
        c4_mv, c7_mv = get_mv_from_input(raw_c4), get_mv_from_input(raw_c7)
        ph_ref_7 = entry.options.get(CONF_PH_REF_7, 7.02)
        ph_ref_4 = entry.options.get(CONF_PH_REF_4, 4.00)

        temp = int.from_bytes(data[0:2], 'little') * 0.06
        ph_raw_mv = int.from_bytes(data[2:4], 'little')
        orp = int.from_bytes(data[4:6], 'little') / 2.0
        
        pente = (float(c4_mv) - float(c7_mv)) / (ph_ref_4 - ph_ref_7)
        ph_calc = ph_ref_7 + ((ph_raw_mv - float(c7_mv)) / pente) if pente != 0 else 7.0
        ph_usine = -0.0084494 * ph_raw_mv + 22.2083
        
        mac_data = hass.data[DOMAIN].get(mac, {})
        tac_val = mac_data.get("tac", 0)
        th_val = mac_data.get("th", 0)
        tds_val = mac_data.get("tds", 0)
        cya = float(entry.options.get(CONF_CYA) or entry.data.get(CONF_CYA, 40))
        chlore_model = entry.options.get(CONF_CHLORE_MODEL, entry.data.get(CONF_CHLORE_MODEL, "stabilized"))

        service_info = async_last_service_info(hass, mac, connectable=True)
        rssi_val = service_info.rssi if service_info else getattr(device, "rssi", None)

        isl_val = compute_isl(temp, ph_calc, tac_val, th_val, tds_val)
        isl_statut = None
        if isl_val is not None:
            if isl_val < -0.3: isl_statut = "Eau corrosive"
            elif isl_val > 0.3: isl_statut = "Eau entartrante"
            else: isl_statut = "Eau équilibrée"

        last_data = {
            "temperature": round(temp, 2), "ph": round(ph_calc, 2), "ph_raw": ph_raw_mv,
            "ph_usine": round(ph_usine, 2), "orp": round(orp), 
            "chlore_actif_hocl": compute_active_chlorine(orp, ph_calc, temp, cya, chlore_model),
            "ph_equilibre_cible": compute_ph_equilibrium(temp, tac_val, th_val, tds_val),
            "isl": isl_val, "isl_statut": isl_statut,
            "battery": int.from_bytes(data[11:13], 'little'), "rssi": rssi_val,
            "last_received": dt_util.utcnow(), "raw_frame": hex_frame
        }
        
        # FIX ANTI-INCONNU : On met en cache la dernière lecture
        hass.data[DOMAIN][mac]["last_data"] = last_data
        
        return last_data

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, 
        name=f"Flipr {mac}", 
        update_method=async_update_data, 
        update_interval=None
    )
    
    # FIX ANTI-INCONNU : On injecte les anciennes données avant même de charger les entités
    if last_data:
        coordinator.data = last_data
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(hass, coordinator.async_request_refresh(), "Flipr_Init_Refresh")
    
    return True

async def async_unload_entry(hass, entry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # FIX ANTI-INCONNU : On a supprimé la ligne qui effaçait brutalement hass.data[DOMAIN][mac]
        # Cela permet à la mémoire (TAC, TH, last_data) de survivre pendant le reload !
    return ok