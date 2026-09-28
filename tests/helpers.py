"""Shared test utilities: frame building and fake BLE client."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

MAC = "AA:BB:CC:DD:EE:FF"

# Realistic defaults: water at 25 °C, pH ≈ 7.4, ORP 700 mV, battery at 3.3 V.
DEFAULT_TEMP_C = 25.02
DEFAULT_PH_MV = 1600  # ≈ pH 7.4 with the default calibration
DEFAULT_ORP_MV = 700.0
DEFAULT_BATTERY_MV = 3300


def build_frame(
    temp_c: float = DEFAULT_TEMP_C,
    ph_mv: int = DEFAULT_PH_MV,
    orp_mv: float = DEFAULT_ORP_MV,
    sync_mode: int = 2,
    battery_mv: int = DEFAULT_BATTERY_MV,
) -> bytes:
    """Build a 13-byte Flipr frame (see frame.py for the layout)."""
    frame = bytearray(13)
    frame[0:2] = round(temp_c / 0.06).to_bytes(2, "little")
    frame[2:4] = int(ph_mv).to_bytes(2, "little")
    frame[4:6] = round(orp_mv * 2).to_bytes(2, "little")
    frame[8] = sync_mode
    frame[11:13] = int(battery_mv).to_bytes(2, "little")
    return bytes(frame)


STANDBY_FRAME = bytes(13)


class FakeBleakClient:
    """Replaces BleakClient: returns the planned frames on each GATT write.

    - `frames`: frames delivered (via notification, or via read for
      Start Max) on each successful write;
    - `write_errors`: exceptions raised successively by write_gatt_char.
    """

    def __init__(
        self,
        frames: list[bytes] | None = None,
        write_errors: list[BaseException | None] | None = None,
        start_notify_hangs: bool = False,
        stop_notify_hangs: bool = False,
        disconnect_hangs: bool = False,
        frames_per_trigger: int = 1,
    ) -> None:
        self.frames: list[bytes] = list(frames or [])
        self.write_errors: list[BaseException | None] = list(write_errors or [])
        self.is_connected = True
        self.writes: list[tuple[str, bytes]] = []
        self.notify_started = False
        self.notify_stopped = False
        self.disconnected = False
        self._handler: Callable[[Any, bytearray], None] | None = None
        self.reads = 0
        # Never resolve on their own: only end if the calling code protects
        # them with a timeout (asyncio.wait_for).
        self._start_notify_hangs = start_notify_hangs
        self._stop_notify_hangs = stop_notify_hangs
        self._disconnect_hangs = disconnect_hangs
        # Number of frames delivered at once by the same write: >1 simulates
        # a burst of notifications, to test queue-full behavior.
        self.frames_per_trigger = frames_per_trigger

    async def start_notify(self, uuid: str, handler: Callable) -> None:
        if self._start_notify_hangs:
            await asyncio.Event().wait()
        self.notify_started = True
        self._handler = handler

    async def stop_notify(self, uuid: str) -> None:
        if self._stop_notify_hangs:
            await asyncio.Event().wait()
        self.notify_stopped = True

    async def write_gatt_char(self, uuid: str, data, response: bool = True) -> None:
        self.writes.append((uuid, bytes(data)))
        if self.write_errors:
            error = self.write_errors.pop(0)
            if error is not None:
                raise error
        if self._handler is not None:
            for _ in range(self.frames_per_trigger):
                if not self.frames:
                    break
                self._handler(None, bytearray(self.frames.pop(0)))

    async def read_gatt_char(self, uuid: str) -> bytearray:
        self.reads += 1
        if not self.frames:
            raise TimeoutError("no frame")
        return bytearray(self.frames.pop(0))

    async def disconnect(self) -> None:
        if self._disconnect_hangs:
            await asyncio.Event().wait()
        self.disconnected = True
        self.is_connected = False
