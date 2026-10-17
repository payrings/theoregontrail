"""Sound for the graphical mode: soft triangle-wave tunes made here, played by the system.

The original plays its tunes through ``& PT`` (the speaker, a click at a time). The tune data
is in a disk file that is not part of this program, so the two sounds the BASIC calls for are
made up here and are meant only to do the same jobs, in the same style:

* ``wait`` -- OREGON TRAIL lines 950-957: ``IF PEEK(975) THEN & PT,1,1`` while the program waits
  for a key at "Press SPACE BAR to continue": a soft little tune, repeated until the key arrives;
* ``collision`` -- FLOAT line 740: ``FOR S1 = 0 TO 3: & PT,1: NEXT``, four soft whumps when the raft hits the shore or a rock.

Control-S switches the sound on and off (``POKE 975, NOT PEEK(975)``); the flag lives in
memory byte 975 and is read through ``Sound.enabled``.

Nothing here needs a sound library: the tunes are written as 8-bit mono WAV files in a
temporary folder and handed to whichever player the system has (``pw-play``, ``paplay``,
``aplay``, ``afplay``, ``ffplay``, ``play``; ``winsound`` on Windows). With none, the program
stays silent and says so once.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

__all__ = ["Sound", "wait_tune", "collision_tune", "write_wav"]

RATE = 22050

_NOTE = 0.17           # seconds in one step of the waiting tune


def _hz(semitones_from_a4: float) -> float:
    return 440.0 * 2 ** (semitones_from_a4 / 12)


# One tune for each tune file the original loads (see ``tunes.py``): MS0 at the start, MS1 to MS16
# on arriving at each landmark (MAIN 1005), MS17 for Oregon, TS for the tombstone. Each is made up
# and as long as the original's, and plays through before it starts again.
from . import tunes as _tunes

TUNES = {name: None for name in _tunes.names()}
_NOTE = _tunes.STEP


def _soft(freq: float, seconds: float, volume: float = 0.32, decay: float = 3.0, slide: float = 0.0):
    """A triangle wave with a gentle attack and a slow fade: the mellow voice of the old
    sound chips. *slide* bends the pitch down (a fraction of the pitch over the note)."""
    n = int(RATE * seconds)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        f = freq * (1.0 - slide * t) if freq else 0.0
        phase = (phase + f / RATE) % 1.0
        tri = 4 * abs(phase - 0.5) - 1 if freq else 0.0
        attack = min(1.0, i / (RATE * 0.02))
        out.append(tri * volume * attack * math.exp(-decay * t))
    return out


def _voice(steps, volume, decay_long, decay_short, lift=0):
    samples = []
    for semis, n in steps:
        if semis is None:
            samples += [0.0] * int(RATE * n * _NOTE)
        else:
            samples += _soft(_hz(semis + lift), n * _NOTE, volume=volume,
                             decay=decay_long if n > 1 else decay_short)
    return samples


def wait_tune(repeats: int = 1, name: str = "ms0"):
    """The tune named, melody over a soft low bass, *repeats* times."""
    melody, bass = _tunes.melody_and_bass(name)
    top = _voice(melody, 0.30, 1.6, 2.4)
    low = _voice(bass, 0.16, 0.9, 0.9)
    n = max(len(top), len(low))
    top += [0.0] * (n - len(top))
    low += [0.0] * (n - len(low))
    return [a + b for a, b in zip(top, low)] * repeats


def _thud(seconds: float = 0.6, volume: float = 0.6, seed: int = 1):
    """A soft 'whump': low rumbling noise whose colour darkens a little as it fades, over a
    faint low tone that sinks just a bit. A bump, not a laser."""
    n = int(RATE * seconds)
    out = []
    phase, lp1, lp2, state = 0.0, 0.0, 0.0, seed * 7919 + 17
    for i in range(n):
        t = i / n
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        white = (state >> 8) / 0x7FFFFF - 1.0
        k = 0.22 - 0.15 * t                              # the filter closes: the noise gets duller
        lp1 += k * (white - lp1)
        lp2 += k * (lp1 - lp2)
        f = 130.0 - 22.0 * t                             # a little drop in pitch
        phase = (phase + f / RATE) % 1.0
        tone = (4 * abs(phase - 0.5) - 1) * 0.35
        attack = min(1.0, i / (RATE * 0.012))
        env = attack * math.exp(-4.2 * t)
        out.append((lp2 * 3.2 + tone) * env)
    peak = max(abs(x) for x in out) or 1.0
    return [x / peak * volume for x in out]       # never clip: the level is set here


def collision_tune(runs: int = 4):
    """Four short soft whumps, each a little quieter. FLOAT 740 plays its tune four times; that
    tune is 21 notes of one unit each, so the whole sound lasts about half a second."""
    samples = []
    for k in range(runs):
        samples += _thud(0.125, volume=0.6 * (1 - 0.15 * k), seed=k + 1)
    return samples


def write_wav(path: str, samples) -> None:
    """Unsigned 8-bit mono, the grain of the old machines."""
    data = bytes(max(0, min(255, int(128 + s * 127))) for s in samples)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(RATE)
        w.writeframes(data)


def duration(samples) -> float:
    return len(samples) / RATE


class Sound:
    """Plays the tunes when ``enabled()`` says so. All failures are silent."""

    PLAYERS = (("pw-play",), ("paplay",), ("aplay", "-q"), ("afplay",),
               ("ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"), ("play", "-q"))

    def __init__(self, enabled=lambda: True):
        self.enabled = enabled
        self.toggle = lambda: None
        self._dir = None
        self._files = {}
        self._proc = None
        self._told = False
        self.length = {"collision": duration(collision_tune())}
        self.tune = "ms0"                       # the tune file in memory (MS0 until a landmark loads its own)

    # ---------------------------------------------------------------- files
    def select(self, name: str) -> None:
        """Load another tune file: ``"ms5"``, ``"ts"`` ... (an unknown name is ignored)."""
        if name in TUNES:
            self.tune = name

    def _file(self, name: str) -> str:
        if name not in self._files:
            if self._dir is None:
                self._dir = tempfile.mkdtemp(prefix="oregon-sound-")
            path = os.path.join(self._dir, name.replace(":", "_") + ".wav")
            if name.startswith("wait:"):
                tune = wait_tune(repeats=1, name=name[5:])
                write_wav(path, tune * max(2, int(300 / duration(tune))))   # about five minutes of it
            else:
                write_wav(path, collision_tune())
            self._files[name] = path
        return self._files[name]

    # -------------------------------------------------------------- playing
    def _start(self, name: str) -> None:
        self.stop()
        try:
            path = self._file(name)
        except OSError:
            return
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:                              # noqa: BLE001
                pass
            return
        for cmd in self.PLAYERS:
            exe = shutil.which(cmd[0])
            if exe:
                try:
                    self._proc = subprocess.Popen([exe, *cmd[1:], path], stdin=subprocess.DEVNULL,
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except OSError:
                    continue
        if not self._told:
            self._told = True
            print("Sound is on, but no audio player was found (pw-play, paplay, aplay ...).",
                  file=sys.stderr)

    def stop(self) -> None:
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:                              # noqa: BLE001
                pass
        proc, self._proc = self._proc, None
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def waiting(self) -> None:
        """The tune that plays at "Press SPACE BAR to continue", until stopped."""
        if self.enabled():
            self._start("wait:" + self.tune)

    def collision(self) -> float:
        """Start the collision sound; returns how long it lasts (seconds), 0 when silent."""
        if not self.enabled():
            return 0.0
        self._start("collision")
        return self.length["collision"]

    def close(self) -> None:
        self.stop()
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
            self._dir = None
            self._files = {}
