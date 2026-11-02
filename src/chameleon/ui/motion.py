"""Motion policy shared by native controls; no background animation loop."""

import ctypes
import os


def motion_enabled() -> bool:
    if os.environ.get("CHAMELEON_REDUCED_MOTION") == "1":
        return False
    if os.name == "nt":
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return bool(enabled.value)
    return True
