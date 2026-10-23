"""Streamlit wrapper for the interactive campus map component (ui/map_component/index.html). Presentation only."""
import shutil
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from logic import mapfile
from ui.icons import icon
from ui.theme import mode

_DIR = Path(__file__).resolve().parent / "map_component"
_component = components.declare_component("campus_map", path=str(_DIR))


_SERVICE_ICONS = {"helpdesk": "headset", "security": "shield-check", "medical": "stethoscope", "it_support": "laptop",
                  "info": "info", "check": "check", "locate-fixed": "locate-fixed"}


def _sync_image() -> None:
    """The component serves its own folder, so keep a copy of the map image next to index.html."""
    src, dst = mapfile.MAP_IMAGE_PATH, _DIR / "campus_map.png"
    if src.exists() and (not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime):
        shutil.copyfile(src, dst)


def outline(landmark: dict | None) -> list[list[tuple[float, float]]]:
    """Polygons to highlight for a landmark (one for places, several rectangles for roads)."""
    return [list(p) for p in landmark["shapes"]] if landmark else []


def focus_on(landmark: dict | None, zoom: float = 2.2) -> dict | None:
    """A fly-to request centred on a landmark. A fresh seq makes the component animate once."""
    if not landmark:
        return None
    return {"x": landmark["map_x"], "y": landmark["map_y"], "zoom": zoom, "seq": time.time_ns()}


def campus_map(key: str, overlay: dict | None = None, map_mode: str = "view", pin: tuple[float, float] | None = None,
               highlight: list | None = None, focus: dict | None = None, height: int = 560) -> dict | None:
    """Draw the map and return a NEW click as {nx, ny, scale, badge?} or None.

    map_mode: 'view' (browse) or 'pick' (crosshair + hint to drop a pin). Clicks repeat on every rerun, so they are
    de-duplicated by their sequence number here.
    """
    _sync_image()
    m = mapfile.meta()
    value = _component(
        key=key, overlay=overlay or {"badges": [], "issues": [], "services": []}, mode=map_mode,
        pin={"x": pin[0], "y": pin[1]} if pin else None, outline=highlight or [], focus=focus, height=height,
        width_px=m["width_px"], height_px=m["height_px"], theme=mode(),
        icons={k: icon(v, 16, 2.2) for k, v in _SERVICE_ICONS.items()}, default=None,
    )
    if not value:
        return None
    seen = f"_mapseq_{key}"
    if st.session_state.get(seen) == value.get("seq"):
        return None
    st.session_state[seen] = value.get("seq")
    return value
