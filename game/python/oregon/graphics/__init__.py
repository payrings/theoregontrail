"""The optional graphical mode (``python -m oregon --graphics``).

It needs Pillow and the pictures in the assets folder (see :mod:`.assets`); the
text mode needs neither and stays the default.
"""

from __future__ import annotations

from .assets import Assets, AssetError, default_folder

__all__ = ["make_ui", "Assets", "AssetError", "default_folder"]


def make_ui(folder: str | None = None, scale: int = 4, backend=None, show_daily: bool = True):
    from .backends import TkBackend
    from .gui import GraphicalUI
    assets = Assets(folder)
    ui = GraphicalUI(assets, backend or TkBackend(scale), show_daily=show_daily)
    if backend is None:
        ui.daily_pause = 1.0            # each day's scene stays up long enough to see; Return stops it
        ui.hunt_pause = 0.02            # a pass of the hunt, so the whole hunt takes up to a minute
        ui.by_pace = True               # ... for a second at a steady pace, less when pushing harder
    return ui
