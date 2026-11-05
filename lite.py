#!/usr/bin/env python3
"""Лайтовая шиза для Hyprland: всё плывёт, но ничего не лезет поверх экрана.

  * экран плывёт волной (текст тоже плывёт), цвета медленно переливаются
  * гэпы/рамки/скругления дышат (acid.py, без зума)
  * у каждого окна своя кислотная рамка
  * иногда мягкая волна посильнее — без инверта, переворотов и скримеров
  * никаких тварей, пузырей и баннеров

Ctrl+C -> всё возвращается (hyprctl reload).

  ./lite.py              # обычно
  ./lite.py --music      # дышит под музыку
  ./lite.py --wave 2     # плывёт сильнее
  ./lite.py --no-bursts  # только ровное плавание
"""
import argparse
import colorsys
import json
import os
import random
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shader  # noqa: E402


def hypr_eval(lua):
    subprocess.Popen(["hyprctl", "eval", lua], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def bright(h, a=255):
    r, g, b = colorsys.hsv_to_rgb(h % 1, 1, 1)
    return f"rgba({int(r*255):02x}{int(g*255):02x}{int(b*255):02x}{a:02x})"


def clients():
    try:
        out = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=2).stdout
        return [c["address"] for c in json.loads(out or "[]")]
    except Exception:
        return []


def set_prop(addr, prop, value):
    hypr_eval(f"hl.dispatch(hl.dsp.window.set_prop({{ window = 'address:{addr}', prop = '{prop}', value = '{value}' }}))")


def paint_windows():
    for a in clients():
        h = random.random()
        act = " ".join(bright(h + i * random.uniform(0.15, 0.4)) for i in range(3))
        set_prop(a, "active_border_color", f"{act} {random.randint(0, 359)}deg")
        set_prop(a, "inactive_border_color", f"{bright(h + 0.5, 0xcc)} {bright(h + 0.7, 0xcc)} {random.randint(0, 359)}deg")


def unpaint_windows():
    for a in clients():
        set_prop(a, "active_border_color", "unset")
        set_prop(a, "inactive_border_color", "unset")

def sway_uv(side, depth):
    """Экран качается из стороны в сторону и уходит вдаль (scale < 1 = дальше)."""
    return (f"uv += vec2(sin(t * 0.9) * {side:.4f} + sin(t * 2.3) * {side * 0.3:.4f},"
            f" cos(t * 1.1) * {side * 0.4:.4f});"
            f" uv = (uv - 0.5) * (1.0 + {depth:.4f} * (0.5 + 0.5 * sin(t * 0.6))) + 0.5;")


def soft(wave, glitch, hue_mix, side, depth):
    shader.UV["sway"] = sway_uv(side, depth)
    # ca и glitch как во 2-м уровне schizo — от них текст и плывёт красиво
    return shader.build(wave=0.004 * wave, ca=0.004 * wave, glitch=glitch,
                        hue_speed=0.5, hue_mix=hue_mix, uv_mode="sway")


def set_shader(src):
    path = shader.write(src)
    hypr_eval(f"hl.config({{ decoration = {{ screen_shader = '{path}' }} }})")


def main():
    ap = argparse.ArgumentParser(description="Лайтовая шиза для Hyprland")
    ap.add_argument("--music", action="store_true", help="дышать под музыку")
    ap.add_argument("--wave", type=float, default=1.0, help="насколько сильно плывёт экран")
    ap.add_argument("--sway", type=float, default=1.0, help="насколько качает и уводит вдаль")
    ap.add_argument("--no-acid", action="store_true", help="без дышащих гэпов/рамок")
    ap.add_argument("--no-paint", action="store_true", help="не красить рамки окон")
    ap.add_argument("--no-bursts", action="store_true", help="без периодических волн посильнее")
    args = ap.parse_args()

    acid = None
    if not args.no_acid:
        cmd = [sys.executable, os.path.join(HERE, "acid.py"), "--intensity", "0.8"]
        if args.music:
            cmd.append("--music")
        acid = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)

    def bye(*_):
        if acid:
            acid.send_signal(signal.SIGINT)
            try:
                acid.wait(timeout=3)
            except Exception:
                acid.kill()
        if not args.no_paint:
            unpaint_windows()
        subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL)
        print("\n🧘 отпустило. всё как было.")
        sys.exit(0)

    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)

    # без этого шейдер не анимируется
    hypr_eval("hl.config({ debug = { damage_tracking = 0 } })")
    calm = soft(args.wave, glitch=0.04 * args.wave, hue_mix=0.5,
                side=0.025 * args.sway, depth=0.08 * args.sway)
    set_shader(calm)

    print("🌊 плывём. Ctrl+C чтобы вернуться.")
    next_paint = 0.0
    next_burst = time.time() + random.uniform(8, 15)
    burst_end = 0.0
    while True:
        now = time.time()
        if not args.no_paint and now >= next_paint:
            paint_windows()
            next_paint = now + 3
        if not args.no_bursts:
            if burst_end and now >= burst_end:
                set_shader(calm)
                burst_end = 0.0
            elif not burst_end and now >= next_burst:
                set_shader(soft(args.wave * 2.2, glitch=0.08 * args.wave, hue_mix=0.8,
                                side=0.045 * args.sway, depth=0.15 * args.sway))
                burst_end = now + random.uniform(1.5, 3.5)
                next_burst = burst_end + random.uniform(10, 25)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
