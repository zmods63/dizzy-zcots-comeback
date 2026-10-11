"""Synthesised sound effects (numpy -> 16-bit WAV, cached in assets/sfx/)."""

import os
import wave

import numpy as np

from . import kit as K

RATE = 44100
SFX_DIR = os.path.join(K.ROOT, "assets", "sfx")


def _env(n, attack=0.005, release=0.1):
    t = np.arange(n) / RATE
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.clip((n / RATE - t) / max(release, 1e-4), 0, 1)
    return a * r


def _noise(n, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def _lowpass(x, k):
    """Cheap one-pole low-pass (k in 0..1, smaller = darker)."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


def beep():
    n = int(0.13 * RATE)
    t = np.arange(n) / RATE
    return 0.35 * np.sin(2 * np.pi * 1000 * t) * _env(n, 0.004, 0.03)


def flatline():
    n = int(3.5 * RATE)
    t = np.arange(n) / RATE
    return 0.28 * np.sin(2 * np.pi * 1000 * t) * _env(n, 0.01, 0.4)


def thump(seed=1):
    n = int(0.35 * RATE)
    t = np.arange(n) / RATE
    body = np.sin(2 * np.pi * (90 - 50 * t / t[-1]) * t) * np.exp(-t * 14)
    grit = _lowpass(_noise(n, seed), 0.08) * np.exp(-t * 30)
    return 0.8 * body + 0.6 * grit


def punch():
    n = int(0.6 * RATE)
    t = np.arange(n) / RATE
    crack = _noise(n, 3) * np.exp(-t * 60)
    boom = np.sin(2 * np.pi * (70 - 30 * t / t[-1]) * t) * np.exp(-t * 6)
    return 0.55 * crack + 0.9 * boom


def slash():
    n = int(0.5 * RATE)
    t = np.arange(n) / RATE
    x = _noise(n, 5)
    k = 0.05 + 0.6 * (t / t[-1])                 # brightening sweep
    y = np.empty_like(x)
    acc = 0.0
    for i in range(n):
        acc += k[i] * (x[i] - acc)
        y[i] = acc
    ring = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 18) * 0.25
    return (0.9 * y + ring) * _env(n, 0.02, 0.2)


def bang():
    n = int(0.7 * RATE)
    t = np.arange(n) / RATE
    metal = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((220, 9), (370, 12), (523, 14), (811, 20)))
    return 0.35 * metal + 0.5 * _noise(n, 7) * np.exp(-t * 40)


def scream():
    n = int(1.3 * RATE)
    t = np.arange(n) / RATE
    f = 620 + 90 * np.sin(2 * np.pi * 5.5 * t)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    v = sum(np.sin(phase * h) / h for h in (1, 2, 3, 4))
    return 0.3 * v * _env(n, 0.05, 0.4) + 0.08 * _noise(n, 9) * _env(n, 0.05, 0.4)


SOUNDS = {"beep": beep, "flatline": flatline, "thump": thump, "punch": punch, "slash": slash, "bang": bang,
          "scream": scream}


def path(name):
    """WAV for a named effect (written on first use)."""
    os.makedirs(SFX_DIR, exist_ok=True)
    p = os.path.join(SFX_DIR, f"{name}.wav")
    if not os.path.exists(p):
        x = np.clip(SOUNDS[name](), -1, 1)
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes((x * 32000).astype(np.int16).tobytes())
    return p
