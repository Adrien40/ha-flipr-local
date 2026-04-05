# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

"""Initialisation Flipr AnalysR 3."""
import logging, asyncio
from datetime import timedelta
import homeassistant.util.dt as dt_util
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth import async_ble_device_from_address, async_last_service_info
from .chemistry import compute_isl, compute_active_chlorine, get_mv_from_input
from .const import *

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select"]

async def update_listener(hass, entry):
    """Mise à jour dynamique lors du changement d'options."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if not coordinator:
        return

    use_gateway = entry.options.get(CONF_USE_GATEWAY, entry.data.get(CONF_USE_GATEWAY, False))
    if use_gateway:
        coordinator.update_interval = None
        _LOGGER.info("Mode passerelle : Intervalle local désactivé pour préserver la batterie.")
    else:
        coordinator.update_interval = timedelta(minutes=75)

    await coordinator.async_refresh()

async def async_setup_entry(hass, entry):
    """Configuration de l'entrée Flipr Local."""
    hass.data.setdefault(DOMAIN, {})
    mac = entry.data[CONF_MAC_ADDRESS]
    use_gateway = entry.options.get(CONF_USE_GATEWAY, entry.data.get(CONF_USE_GATEWAY, False))
    
    if mac not in hass.data[DOMAIN]:
        hass.data[DOMAIN][mac] = {}
        
    last_data = {}

    entry.async_on_unload(entry.add_update_listener(update_listener))

    async def async_update_data():
        nonlocal last_data
        
        try:
            async with asyncio.timeout(20):
                device = async_ble_device_from_address(hass, mac, connectable=True)
                
                if not device:
                    if last_data: return last_data
                    raise UpdateFailed("Flipr hors de portée Bluetooth")

                client = await establish_connection(BleakClient, device, mac)
                data = await client.read_gatt_char(FLIPR_CHARACTERISTIC_UUID)
                await client.disconnect()
                
        except (asyncio.TimeoutError, Exception) as err:
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
        cya = float(entry.options.get(CONF_CYA) or entry.data.get(CONF_CYA, 40))
        chlore_model = entry.options.get("chlore_model", "stabilized")

        service_info = async_last_service_info(hass, mac, connectable=True)
        rssi_val = service_info.rssi if service_info else getattr(device, "rssi", None)

        last_data = {
            "temperature": round(temp, 2), "ph": round(ph_calc, 2), "ph_raw": ph_raw_mv,
            "ph_usine": round(ph_usine, 2), "orp": round(orp), 
            "chlore_actif": compute_active_chlorine(orp, ph_calc, temp, cya, chlore_model),
            "isl": compute_isl(temp, ph_calc, mac_data.get("tac", 0), mac_data.get("th", 0), mac_data.get("tds", 0)),
            "battery": int.from_bytes(data[11:13], 'little'), "rssi": rssi_val,
            "last_received": dt_util.utcnow(), "raw_frame": hex_frame
        }
        return last_data

    interval = None if use_gateway else timedelta(minutes=75)
    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, 
        name=f"Flipr {mac}", 
        update_method=async_update_data, 
        update_interval=interval
    )
    
    hass.async_create_task(coordinator.async_refresh())
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    """Déchargement propre."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
