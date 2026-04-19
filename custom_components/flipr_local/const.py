# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.

from datetime import timedelta
from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "flipr_local"

PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select", "switch"]

CONF_MAC_ADDRESS = "mac_address"
CONF_USE_GATEWAY = "use_gateway"

CONF_PH_CALIB_4 = "ph_calib_4"
CONF_PH_CALIB_7 = "ph_calib_7"
CONF_PH_REF_7 = "ph_ref_7"
CONF_PH_REF_4 = "ph_ref_4"
CONF_ORP_CALIB = "orp_calib"
CONF_ORP_REF = "orp_ref"
CONF_TEMP_OFFSET = "temp_offset"

PH_FACTORY_OFFSET = 22.2083
PH_FACTORY_SLOPE = -0.0084494

CONF_PH_MIN = "ph_min"
CONF_PH_MAX = "ph_max"
CONF_ORP_MIN = "orp_min"
CONF_ORP_MAX = "orp_max"
CONF_TEMP_MIN = "temp_min"
CONF_TEMP_MAX = "temp_max"

CONF_TAC = "tac"
CONF_TH = "th"
CONF_TDS = "tds"
CONF_CYA = "cya"
CONF_CHLORINE_MODEL = "chlorine_model"

CONF_SYNC_MODE = "sync_mode"
CONF_SCAN_INTERVAL = "scan_interval"

FLIPR_CHARACTERISTIC_UUID = "00000006-0000-1000-8000-00805f9b34fb"
FLIPR_ANALYZE_UUID = "0000940d-0000-1000-8000-00805f9b34fb"
SYNC_CHAR_UUID = "000073b4-0000-1000-8000-00805f9b34fb"

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=60)
TIMEOUT_BLE_CONN = 30.0
TIMEOUT_FORCE_REFRESH = 180.0
DEBOUNCE_COOLDOWN = 0.3
SAVE_DEBOUNCE_DELAY = 2.0

BLE_RECENTLY_SEEN_THRESHOLD_S: int = 120

BATTERY_MIN_MV = 2500
BATTERY_MAX_MV = 3600

VALID_SYNC_MODES = {"0", "1", "2", "3"}

# FIX: named constant instead of magic number "26" scattered in code.
# A Flipr BLE frame is always 13 bytes → 26 hex characters when encoded.
EXPECTED_FRAME_HEX_LEN: int = 26

BT_STATUS_WAITING = "waiting"
BT_STATUS_CONNECTING = "connecting"
BT_STATUS_WAKING_UP = "waking_up"
BT_STATUS_REQUESTING = "requesting"
BT_STATUS_READING = "reading"
BT_STATUS_WRITING_SYNC = "writing_sync"
BT_STATUS_SUCCESS = "success"
BT_STATUS_SYNC_APPLIED = "sync_applied"
BT_STATUS_ERROR = "error"
BT_STATUS_ERROR_RETRY = "error_retry"
BT_STATUS_WRITE_FAILED = "write_failed"
BT_STATUS_PAUSED = "paused"
BT_STATUS_OUT_OF_RANGE = "out_of_range"

DATA_ESTIMATED_FREE_CHLORINE = "estimated_free_chlorine"
DATA_ACTIVE_CHLORINE_HOCL = "active_chlorine_hocl"

DEFAULT_PH_MIN: float = 6.90
DEFAULT_PH_MAX: float = 7.50
DEFAULT_ORP_MIN: float = 650.0
DEFAULT_ORP_MAX: float = 800.0
DEFAULT_TEMP_MIN: float = 6.0
DEFAULT_TEMP_MAX: float = 32.0

DEFAULT_ORP_CALIB: float = 650.0
DEFAULT_ORP_REF: float = 650.0

DEFAULT_PH_CALIB_7: float = 8.40
DEFAULT_PH_CALIB_4: float = 6.02
DEFAULT_PH_REF_7: float = 7.02
DEFAULT_PH_REF_4: float = 4.00


def get_flipr_model(name: str | None) -> str:
    if not name:
        return "Flipr"
    name_upper = name.upper()
    if name_upper.startswith("F3"):
        return "Flipr AnalysR 3"
    if name_upper.startswith("F2"):
        return "Flipr AnalysR"
    if name_upper.startswith(("FLIPR 01", "FLIPR 00")):
        return "Flipr Start Max"
    return "Flipr"


def flipr_device_info(mac: str, model_name: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, mac)},
        name=model_name,
        manufacturer="Flipr",
        model=model_name,
    )
