#!/usr/bin/env python3
"""Hyprland на кислоте: рабочий стол дышит синусоидой или качается под музыку.

Все изменения только в рантайме (hyprctl eval), конфиги не трогаются.
Ctrl+C -> hyprctl reload -> всё как было.

  ./acid.py            # синусоида
  ./acid.py --music    # под то, что играет из колонок
  ./acid.py --speed 3  # быстрее
"""
import argparse
import array
import colorsys
import math
import signal
import subprocess
import sys
import threading
import time


def hypr(lua: str) -> None:
    subprocess.run(["hyprctl", "eval", lua], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def rgba(h: float, s: float = 1.0, v: float = 1.0, a: int = 255) -> str:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return f"rgba({int(r*255):02x}{int(g*255):02x}{int(b*255):02x}{a:02x})"


class Ears:
    """Слушает монитор дефолтного аудиовыхода, отдаёт громкость 0..1 и удары."""

    def __init__(self):
        self.level = 0.0
        self.kick = 0.0
        self._peak = 1000.0
        self._avg = 0.0
        self.proc = subprocess.Popen(
            ["parec", "-d", "@DEFAULT_MONITOR@", "--format=s16le", "--rate=22050",
             "--channels=1", "--latency-msec=15"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        chunk = 512 * 2
        while True:
            data = self.proc.stdout.read(chunk)
            if not data:
                return
            s = array.array("h", data)
            rms = math.sqrt(sum(x * x for x in s) / len(s))
            self._peak = max(rms, self._peak * 0.9995, 300.0)
            lvl = min(rms / self._peak, 1.0)
            # быстрый подъём, медленный спад
            self.level = lvl if lvl > self.level else self.level * 0.9 + lvl * 0.1
            # удар = громкость резко выше среднего
            if lvl > self._avg * 1.4 + 0.08:
                self.kick = 1.0
            self._avg = self._avg * 0.95 + lvl * 0.05

    def tick(self):
        self.kick *= 0.82

    def close(self):
        self.proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--music", action="store_true", help="качаться под звук")
    ap.add_argument("--speed", type=float, default=1.0, help="скорость трипа")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--zoom", action="store_true", help="экран пульсирует зумом")
    ap.add_argument("--intensity", type=float, default=1.0, help="насколько сильно плющит")
    args = ap.parse_args()

    ears = Ears() if args.music else None

    def bye(*_):
        if ears:
            ears.close()
        subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL)
        print("\n🧘 отпустило. конфиг перезагружен.")
        sys.exit(0)

    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)

    print("🍄 поехали. Ctrl+C чтобы вернуться в реальность.")
    t0 = time.time()
    dt = 1.0 / args.fps
    k = args.intensity
    while True:
        t = (time.time() - t0) * args.speed
        lvl = kick = 0.0
        if ears:
            ears.tick()
            lvl, kick = ears.level, ears.kick

        breath = 0.5 + 0.5 * math.sin(t * 0.9)          # медленное дыхание
        wobble = 0.5 + 0.5 * math.sin(t * 2.3 + 1.0)    # побыстрее
        hue = t * 0.08 + lvl * 0.3

        gaps_in = int(2 + k * (6 * breath + 14 * kick + 6 * lvl))
        gaps_out = int(4 + k * (14 * wobble + 25 * kick + 10 * lvl))
        border = int(2 + k * (3 * breath + 6 * kick))
        rounding = int(k * (4 + 18 * wobble + 10 * lvl))
        angle = int(t * 40 + kick * 90) % 360
        a_op = max(0.6, 1.0 - k * (0.08 * wobble + 0.15 * kick))
        i_op = max(0.4, 0.92 - k * (0.25 * breath + 0.1 * lvl))
        sat = min(1.0, 0.75 + 0.25 * lvl + 0.3 * kick)

        active = ", ".join(f'"{rgba(hue + i / 4, sat, 1.0)}"' for i in range(4))
        inactive = ", ".join(f'"{rgba(hue + 0.5 + i / 3, 0.6, 0.45, 0xaa)}"' for i in range(3))

        hypr(
            "hl.config({"
            f" general = {{ gaps_in = {gaps_in}, gaps_out = {gaps_out}, border_size = {border},"
            f"   col = {{ active_border = {{ colors = {{ {active} }}, angle = {angle} }},"
            f"           inactive_border = {{ colors = {{ {inactive} }}, angle = {(360 - angle) % 360} }} }} }},"
            f" decoration = {{ rounding = {rounding}, active_opacity = {a_op:.3f}, inactive_opacity = {i_op:.3f} }}"
            + (f", cursor = {{ zoom_factor = {1.0 + k * (0.05 * breath + 0.06 * lvl + 0.18 * kick) + (0.25 if math.sin(t * 0.37) > 0.97 else 0):.3f} }}" if args.zoom else "")
            + " })"
        )
        time.sleep(dt)


if __name__ == "__main__":
    main()
