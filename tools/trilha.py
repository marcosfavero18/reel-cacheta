"""Gera uma trilha original e inspiradora (sem direitos autorais de terceiros).

Progressão I–V–vi–IV em Dó maior, 100 BPM, com piano em arpejo, pad,
baixo e percussão que entra aos poucos até um clímax final.
Uso: python3 trilha.py saida.wav [duracao_segundos]
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4

# Acordes (notas MIDI): C, G, Am, F
CHORDS = [
    [48, 55, 60, 64, 67],
    [43, 50, 59, 62, 67],
    [45, 52, 57, 60, 64],
    [41, 48, 57, 60, 65],
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a=0.01, r=0.3):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * np.exp(-t / r)
    return e


def piano(m, dur, vel=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.6 for k in range(1, 6))
    return vel * s * env(n, 0.005, 0.9)


def pad(notes, dur, vel=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.08):
            s += np.sin(2 * np.pi * hz(m + 12) * (1 + det / 100) * t)
    a = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.5)
    return vel * s / (3 * len(notes)) * a


def bass(m, dur, vel=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * hz(m - 12) * t) + 0.3 * np.sin(2 * np.pi * hz(m) * t)
    return vel * s * env(n, 0.01, 1.2)


def kick(vel=0.8):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return vel * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def snare(vel=0.25):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    return vel * rng.standard_normal(n) * np.exp(-t * 18)


def hat(vel=0.06):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0)
    return vel * x * np.exp(-t * 60)


def add(buf, sig, start):
    i = int(start * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def main(out, total):
    n = int(total * SR)
    L = np.zeros(n)
    bars = int(np.ceil(total / BAR))
    for b in range(bars):
        t0 = b * BAR
        ch = CHORDS[b % 4]
        section = b / max(1, bars - 1)  # 0 → 1 ao longo da música
        add(L, pad(ch, BAR + 0.4, 0.10 + 0.08 * section), t0)
        add(L, bass(ch[0], BAR), t0)
        # arpejo de piano em colcheias
        arp = [ch[2], ch[3], ch[4], ch[3] + 12, ch[4], ch[3], ch[2] + 12, ch[4]]
        for k, m in enumerate(arp):
            add(L, piano(m + 12, BEAT, 0.16 + 0.06 * section), t0 + k * BEAT / 2)
        # melodia simples nas barras pares a partir do 2º ciclo
        if b >= 4:
            mel = [ch[4] + 12, ch[3] + 12, ch[2] + 12, ch[3] + 12]
            for k, m in enumerate(mel):
                add(L, piano(m, BEAT * 1.5, 0.22), t0 + k * BEAT)
        # percussão entra aos poucos
        if b >= 2:
            for k in range(4):
                add(L, kick(0.55 if b < 6 else 0.8), t0 + k * BEAT)
        if b >= 4:
            for k in (1, 3):
                add(L, snare(0.22), t0 + k * BEAT)
            for k in range(8):
                add(L, hat(), t0 + k * BEAT / 2)

    # reverb simples (ecos amortecidos) e estéreo leve
    rev = L.copy()
    for d, g in ((0.031, 0.35), (0.053, 0.28), (0.089, 0.22), (0.131, 0.16), (0.197, 0.1)):
        k = int(d * SR)
        rev[k:] += g * L[:-k]
    Lc = rev
    Rc = np.roll(rev, int(0.012 * SR))
    # fade-out final
    fo = int(2.5 * SR)
    fade = np.ones(n)
    fade[-fo:] = np.linspace(1, 0, fo)
    st = np.stack([Lc * fade, Rc * fade], axis=1)
    st /= np.max(np.abs(st)) / 0.89
    data = (st * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 31.0)
