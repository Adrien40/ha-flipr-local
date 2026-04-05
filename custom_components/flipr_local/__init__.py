# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Initialisation Flipr AnalysR 3."""
import logging, math, asyncio
from datetime import timedelta
import homeassistant.util.dt as dt_util
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth import async_ble_device_from_address, async_last_service_info
from .chemistry import compute_isl, compute_active_chlorine
from .const import *

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select"]

async def update_listener(hass, entry):
    """Gère le changement de calibration sans relancer le Bluetooth."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if not coordinator or not coordinator.data:
        return

    new_data = dict(coordinator.data)
    ph_raw_mv = new_data.get("ph_raw")
    if not ph_raw_mv:
        return

    raw_c4 = entry.options.get(CONF_PH_CALIB_4) or entry.data.get(CONF_PH_CALIB_4) or 1900.0
    raw_c7 = entry.options.get(CONF_PH_CALIB_7) or entry.data.get(CONF_PH_CALIB_7) or 1600.0
    ph_ref_7 = entry.options.get(CONF_PH_REF_7, 7.02)
    ph_ref_4 = entry.options.get(CONF_PH_REF_4, 4.00)

    def get_mv_from_input(val):
        try:
            val_f = float(val)
            if val_f < 20.0: return round((val_f - 22.2083) / -0.0084494)
            return val_f
        except Exception: return 1600.0

    c4_mv = get_mv_from_input(raw_c4)
    c7_mv = get_mv_from_input(raw_c7)

    pente = (float(c4_mv) - float(c7_mv)) / (ph_ref_4 - ph_ref_7)
    ph_calc = ph_ref_7 + ((ph_raw_mv - float(c7_mv)) / pente) if pente != 0 else 7.0
    new_data["ph"] = round(ph_calc, 2)

    mac = entry.data[CONF_MAC_ADDRESS]
    mac_data = hass.data[DOMAIN].get(mac, {})
    
    try:
        tac = float(entry.options.get("tac") or entry.data.get("tac") or mac_data.get("tac") or 0)
        th = float(entry.options.get("th") or entry.data.get("th") or mac_data.get("th") or 0)
        tds = float(entry.options.get("tds") or entry.data.get("tds") or mac_data.get("tds") or 0)
        cya = float(entry.options.get("cya") or entry.data.get("cya") or mac_data.get("cya") or 40)
    except ValueError:
        tac, th, tds, cya = 0.0, 0.0, 0.0, 40.0

    temp = new_data.get("temperature")
    orp = new_data.get("orp")
    chlore_model = entry.options.get("chlore_model", "stabilized")

    if temp is not None and orp is not None:
        new_data["isl"] = compute_isl(temp, ph_calc, tac, th, tds)
        new_data["chlore_actif"] = compute_active_chlorine(orp, ph_calc, temp, cya, chlore_model)

    coordinator.async_set_updated_data(new_data)

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    mac = entry.data[CONF_MAC_ADDRESS]
    
    if mac not in hass.data[DOMAIN]:
        hass.data[DOMAIN][mac] = {}
        
    last_data = {}

    entry.async_on_unload(entry.add_update_listener(update_listener))

    async def async_update_data():
        nonlocal last_data
        
        raw_c4 = entry.options.get(CONF_PH_CALIB_4) or entry.data.get(CONF_PH_CALIB_4) or 1900.0
        raw_c7 = entry.options.get(CONF_PH_CALIB_7) or entry.data.get(CONF_PH_CALIB_7) or 1600.0
        ph_ref_7 = entry.options.get(CONF_PH_REF_7, 7.02)
        ph_ref_4 = entry.options.get(CONF_PH_REF_4, 4.00)

        def get_mv_from_input(val):
            try:
                val_f = float(val)
                if val_f < 20.0: return round((val_f - 22.2083) / -0.0084494)
                return val_f
            except Exception: return 1600.0

        c4_mv = get_mv_from_input(raw_c4)
        c7_mv = get_mv_from_input(raw_c7)

        device = async_ble_device_from_address(hass, mac, connectable=True)
        if not device: 
            if last_data: return last_data
            raise UpdateFailed("Hors de portée")

        try:
            client = await establish_connection(BleakClient, device, mac)
            data = await client.read_gatt_char(FLIPR_CHARACTERISTIC_UUID)
            await client.disconnect()
            
            hex_frame = data.hex().upper()
            if data == bytearray(13) or hex_frame.startswith("0000"):
                if last_data: 
                    last_data["raw_frame"] = hex_frame + " (Veille/Reset)"
                    return last_data
                raise UpdateFailed("Données non disponibles (Sonde en veille)")

            temp = int.from_bytes(data[0:2], 'little') * 0.06
            ph_raw_mv = int.from_bytes(data[2:4], 'little')
            orp = int.from_bytes(data[4:6], 'little') / 2.0
            
            pente = (float(c4_mv) - float(c7_mv)) / (ph_ref_4 - ph_ref_7)
            ph_calc = ph_ref_7 + ((ph_raw_mv - float(c7_mv)) / pente) if pente != 0 else 7.0
            ph_usine = -0.0084494 * ph_raw_mv + 22.2083
            
            mac_data = hass.data[DOMAIN].get(mac, {})
            try:
                tac = float(entry.options.get("tac") or entry.data.get("tac") or mac_data.get("tac") or 0)
                th = float(entry.options.get("th") or entry.data.get("th") or mac_data.get("th") or 0)
                tds = float(entry.options.get("tds") or entry.data.get("tds") or mac_data.get("tds") or 0)
                cya = float(entry.options.get("cya") or entry.data.get("cya") or mac_data.get("cya") or 40)
            except ValueError:
                tac, th, tds, cya = 0.0, 0.0, 0.0, 40.0

            chlore_model = entry.options.get("chlore_model", "stabilized")
            
            isl = compute_isl(temp, ph_calc, tac, th, tds)
            chlore = compute_active_chlorine(orp, ph_calc, temp, cya, chlore_model)

            service_info = async_last_service_info(hass, mac, connectable=True)
            rssi_val = service_info.rssi if service_info else getattr(device, "rssi", None)

            new_timestamp = dt_util.utcnow() if hex_frame != last_data.get("raw_frame") else last_data.get("last_received", dt_util.utcnow())

            last_data = {
                "temperature": round(temp, 2), "ph": round(ph_calc, 2), "ph_raw": ph_raw_mv,
                "ph_usine": round(ph_usine, 2), "orp": round(orp),
                "chlore_actif": chlore,
                "isl": isl,
                "battery": int.from_bytes(data[11:13], 'little'),
                "rssi": rssi_val,
                "last_received": new_timestamp,
                "raw_frame": hex_frame
            }
            return last_data
        except Exception as err: 
            if last_data: return last_data
            raise UpdateFailed(err)

    # Initialisation à 75 par défaut, le number.py prendra le relais instantanément pour mettre ta vraie valeur
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name=f"Flipr {mac}", update_method=async_update_data, update_interval=timedelta(minutes=75))
    await coordinator.async_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok: hass.data[DOMAIN].pop(entry.entry_id)
    return ok