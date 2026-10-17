"""Where the finished picture goes and where the keys come from.

* :class:`TkBackend` -- a window (tkinter, which comes with Python).
* :class:`ScriptBackend` -- a list of keys and, optionally, a folder to write each
  screen the game waits at as a PNG. It is how the tests and the screen-by-screen
  checks run without a display.
"""

from __future__ import annotations

import base64
import io
import os
import time

__all__ = ["TkBackend", "ScriptBackend"]


class ScriptBackend:
    def __init__(self, keys="", frames_dir: str | None = None, scale: int = 1):
        self.keys = list(keys)
        self.frames_dir = frames_dir
        self.scale = scale
        self.frame = None
        self.count = 0
        if frames_dir:
            os.makedirs(frames_dir, exist_ok=True)

    def show(self, img):
        self.frame = img

    def _dump(self):
        if self.frames_dir and self.frame is not None:
            im = self.frame
            if self.scale != 1:
                im = im.resize((im.width * self.scale, im.height * self.scale))
            im.save(os.path.join(self.frames_dir, f"frame_{self.count:04d}.png"))
            self.count += 1

    def read(self):
        self._dump()
        return self.keys.pop(0) if self.keys else None

    def read_timeout(self, seconds):
        return self.read()

    def poll(self):
        return None

    def pump(self):
        pass

    def flush(self):
        pass


class TkBackend:
    """A tkinter window. Keys: letters and digits as typed, Return, Backspace, Control-S."""

    def __init__(self, scale: int = 4, title: str = "The Oregon Trail"):
        import tkinter as tk
        self.tk = tk
        self.scale = scale
        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg="black")
        self.label = tk.Label(self.root, bd=0, bg="black")
        self.label.pack()
        self.queue = []
        self.root.bind("<Key>", self._on_key)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.closed = False

    def _close(self):
        self.closed = True
        self.root.destroy()

    def _on_key(self, e):
        if e.keysym == "Return":
            self.queue.append("\r")
        elif e.keysym == "BackSpace":
            self.queue.append("\x7f")
        elif e.keysym in ("Up", "Down", "Left", "Right"):
            self.queue.append({"Up": "\x1e", "Down": "\x1f", "Left": "\x1c",
                               "Right": "\x1d"}[e.keysym])
        elif e.state & 0x4 and e.keysym.lower() == "s":
            self.queue.append("\x13")
        elif e.char and e.char.isprintable():
            self.queue.append(e.char)

    def show(self, img):
        if self.closed:
            raise SystemExit
        im = img.resize((img.width * self.scale, img.height * self.scale))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        photo = self.tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        self.label.configure(image=photo)
        self.label.image = photo
        self.root.update()

    def read(self):
        while not self.queue:
            if self.closed:
                raise SystemExit
            self.root.update()
            time.sleep(0.01)
        return self.queue.pop(0)

    def read_timeout(self, seconds):
        """Like :meth:`read`, but returns ``""`` when no key came within *seconds*
        (the cursor blinks on this)."""
        end = time.monotonic() + seconds
        while not self.queue:
            if self.closed:
                raise SystemExit
            if time.monotonic() >= end:
                return ""
            self.root.update()
            time.sleep(0.01)
        return self.queue.pop(0)

    def pump(self):
        if self.closed:
            raise SystemExit
        self.root.update()

    def poll(self):
        if self.closed:
            raise SystemExit
        self.root.update()
        return self.queue.pop(0) if self.queue else None

    def flush(self):
        self.queue.clear()
