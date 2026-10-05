"""Type at the real game through a pseudo-terminal and check the answers land.

This is the regression test for the input path. Two things went wrong, both
showing as "the keyboard is unresponsive":

* ``tty.setcbreak`` sets the terminal with ``TCSAFLUSH``, which **discards
  anything already typed**. A key pressed while the game was drawing was thrown
  away, so it appeared intermittently, depending on which side of that call the
  keystroke fell. The mode is now built here and set with ``TCSANOW``, which
  leaves pending input alone.
* prompts took a single character and then tried to *drain* the Return that ended
  them -- and lost the race, because the Return often arrives after the drain ran.
  The next prompt was then handed a bare Return, rejected it, and sat there: every
  answer landed one prompt late.

A pty is needed because the whole point is to exercise the terminal path. A pipe
would touch none of it.

Run directly -- ``python tests/pty_check.py`` -- or through pytest, which skips if
a pty cannot be opened.
"""
import os
import pty
import select
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Session:
    """The game running on the far end of a pty, with a rolling output buffer."""

    def __init__(self, extra_args=(), data="/tmp/oregon-pty-data"):
        self.master, slave = pty.openpty()
        env = dict(os.environ, PYTHONUNBUFFERED="1", TERM="xterm")
        env.pop("OREGON_DEBUG_INPUT", None)
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "oregon", "--no-interrupt",
             "--seed", "4242", "--data", data, *extra_args],
            cwd=ROOT, stdin=slave, stdout=slave, stderr=slave, env=env,
            close_fds=True)
        os.close(slave)
        self.buf = ""

    def read(self, timeout=0.3):
        try:
            r, _, _ = select.select([self.master], [], [], timeout)
        except (OSError, ValueError):
            return ""
        if not r:
            return ""
        try:
            chunk = os.read(self.master, 16384)
        except OSError:
            return ""
        if not chunk:
            return ""
        self.buf += chunk.decode("latin-1", "replace")
        return self.buf

    def wait_for(self, needle, timeout=25.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if needle in self.buf:
                return True
            self.read(0.2)
        return False

    def send(self, text, per_char=0.06):
        """Type it a character at a time, the way a person does."""
        for ch in text:
            os.write(self.master, ch.encode())
            time.sleep(per_char)

    def pump(self, seconds=1.0):
        end = time.time() + seconds
        while time.time() < end:
            self.read(0.2)

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:                          # noqa: BLE001
            self.proc.kill()
        try:
            os.close(self.master)
        except OSError:
            pass


#: (what to wait for, what to type, what should appear next)
#: Each answer is checked against the *following* screen, so an answer that landed
#: on the wrong prompt cannot pass. Choices other than 1 are included deliberately:
#: a prompt whose allowed set omitted a digit used to ignore it and sit there, which
#: is the other half of "the keyboard is unresponsive".
STEPS = [
    ("What is your choice?", "1", "Many kinds of people made the trip"),
    ("What is your choice?", "2", "first name of the wagon leader"),
    ("What is the first name of the wagon leader", "Zeke", "four other members"),
    ("(Enter names or press Return)", "", "Are these names correct"),
    ("Are these names correct", "Y", "Going back to 18"),
]


def check(verbose=True, data="/tmp/oregon-pty-data") -> list:
    """Play through the opening of the game and report anything wrong."""
    problems = []
    s = Session(data=data)
    try:
        for needle, answer, expect in STEPS:
            if not s.wait_for(needle):
                problems.append(f"never reached the prompt {needle!r}")
                break
            s.send(answer + "\n")
            s.pump(1.0)
            if verbose:
                print(f"  sent {answer!r:<7} after {needle!r}", flush=True)
            if not s.wait_for(expect, timeout=15.0):
                problems.append(f"{answer!r} did not lead to {expect!r}; "
                                f"the answer landed on the wrong prompt")
                if verbose:
                    print("      tail: " + repr(s.buf[-220:]), flush=True)
                break
    finally:
        s.close()
    return problems


def main() -> int:
    problems = check()
    print(f"{len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())