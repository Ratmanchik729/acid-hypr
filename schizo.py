#!/usr/bin/python3
"""Полный шизо-режим для Hyprland.

  * по углам выскакивают твари и несут бред (про твою же систему)
  * каждое окно получает свою кислотную рамку, и она постоянно меняется
  * обои генерятся на лету: кислотная воронка + абсурдный заголовок + эмодзи
  * поверх всего работает acid.py (дышащие гэпы, скругления, прозрачность)

Ctrl+C -> всё возвращается: обои, цвета окон, конфиг.

  ./schizo.py            # обычная шиза
  ./schizo.py --music    # шиза под музыку
"""
import argparse
import colorsys
import json
import math
import os
import random
import signal
import subprocess
import sys
import threading
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = "/usr/lib/libgtk4-layer-shell.so"

# gtk4-layer-shell должен загрузиться раньше libwayland, иначе окна не станут оверлеем
if LIB not in os.environ.get("LD_PRELOAD", ""):
    os.environ["LD_PRELOAD"] = (LIB + " " + os.environ.get("LD_PRELOAD", "")).strip()
    os.execv(sys.executable, [sys.executable] + sys.argv)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LS  # noqa: E402

WP_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "schizo-wallpapers")
BG_LINK = os.path.expanduser("~/.local/state/omarchy/current/background")


# ───────────────────────── бред ─────────────────────────

CREATURES = list("🐸🦆🥒👁🐌🦑🧠🍄🐙🦐🥔🧀🐀🦷👽🤡🗿🦩🐓🥚🫠🪱🦔🍆🐟🛸🧄🦞")

SUBJ = ["огурец", "мой внутренний голос", "твой процессор", "голубь у подъезда", "холодильник",
        "ядро Linux", "соседская кошка", "Hyprland", "бабушкин сервант", "этот пиксель",
        "квантовый пельмень", "systemd", "мышь (компьютерная)", "мышь (настоящая)", "луна",
        "твоя клавиатура", "pacman", "дед из третьего подъезда", "картошка", "весь Arch Linux"]
VERB = ["следит за тобой", "знает пароль от вайфая", "уже пять минут смотрит в стену",
        "хочет стать композитором", "задолжал мне 300 рублей", "ушёл в монастырь",
        "сегодня какой-то не такой", "отказывается компилироваться", "шепчет на ассемблере",
        "передаёт привет", "вчера плакал", "учит китайский", "ест оперативку ложкой",
        "в сговоре с принтером", "мечтает о море", "скрывает что-то в /tmp"]
FREE = [
    "а ты точно закрыл холодильник?",
    "пиксель в левом верхнем углу немного влажный",
    "я — процесс без PID. меня не убить",
    "кажется, обои на меня посмотрели",
    "вчера sudo спросил у меня пароль. я сказал «нет»",
    "если долго смотреть на курсор, курсор начинает смотреть на тебя",
    "мама, я в терминале",
    "этот бред сгенерирован вручную, честно",
    "rm -rf / — это шутка. наверное",
    "кто-то перевернул все нули в единицы, пока ты моргал",
    "у меня 8 пальцев и все в разной временной зоне",
    "я видел RGB. он видел меня",
    "сколько огурцов в одном гигабайте?",
    "ГДЕ МОЙ БУТЕРБРОД",
    "не оборачивайся. там просто стена. или нет",
    "я нашёл баг в реальности, заводить issue?",
    "ты моргнул. я заметил",
    "через 3 секунды все окна станут фиолетовыми. шучу. или да",
    "привет из /dev/null, тут уютно",
    "хочу на ручки",
]


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return ""


def system_bred():
    """Бред на основе того, что реально творится в системе."""
    opts = []
    top = sh(["ps", "-eo", "comm,%cpu,rss", "--sort=-%cpu", "--no-headers"]).splitlines()
    if top:
        p = top[0].split()
        if len(p) >= 3:
            name, cpu, mb = p[0], p[1], int(p[2]) // 1024
            opts += [f"{name} жрёт {cpu}% процессора. я считаю это неуважением",
                     f"{name} съел {mb} МБ памяти и даже не поделился",
                     f"я поговорил с {name}. он просил передать, что устал"]
    try:
        w = json.loads(sh(["hyprctl", "activewindow", "-j"]) or "{}")
        if w.get("class"):
            c = w["class"].split(".")[-1]
            opts += [f"зачем тебе {c}? подумай об этом",
                     f"{c} сегодня подозрительно тихий",
                     f"у {c} есть секрет. я знаю какой"]
        if w.get("title"):
            opts.append(f"«{w['title'][:40]}»… звучит как пророчество")
    except Exception:
        pass
    try:
        load = os.getloadavg()[0]
        opts.append(f"нагрузка {load:.2f}. это число мне снилось")
    except Exception:
        pass
    return random.choice(opts) if opts else random.choice(FREE)


def bred():
    r = random.random()
    if r < 0.3:
        return system_bred()
    if r < 0.65:
        return f"{random.choice(SUBJ)} {random.choice(VERB)}"
    return random.choice(FREE)


def headline():
    s = random.choice(SUBJ).upper()
    v = random.choice(VERB).upper()
    return f"{s}\n{v}"


# ───────────────────────── цвета ─────────────────────────

def bright(h, a=255):
    r, g, b = colorsys.hsv_to_rgb(h % 1, 1, 1)
    return f"rgba({int(r*255):02x}{int(g*255):02x}{int(b*255):02x}{a:02x})"


def hex_bright(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1, 0.85, 1)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def hypr_eval(lua):
    subprocess.Popen(["hyprctl", "eval", lua], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def clients():
    try:
        return [c["address"] for c in json.loads(sh(["hyprctl", "clients", "-j"]) or "[]")]
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
    return True


def unpaint_windows():
    for a in clients():
        set_prop(a, "active_border_color", "unset")
        set_prop(a, "inactive_border_color", "unset")


# ───────────────────────── обои ─────────────────────────

WP_EMOJI = list("🥒👁🐸🦆🍄🧠🐌🗿🤡🦑🫠🥔🛸🐓🧀")
_wp_n = 0
_wp_busy = False


def make_wallpaper():
    global _wp_n, _wp_busy
    os.makedirs(WP_DIR, exist_ok=True)
    _wp_n += 1
    out = os.path.join(WP_DIR, f"wp{_wp_n % 3}.jpg")
    em = "".join(random.sample(WP_EMOJI, random.randint(1, 3)))
    em2 = random.choice(WP_EMOJI)
    rot = random.randint(-15, 15)
    seed = random.randint(1, 1_000_000)
    text = headline()
    longest = max(len(l) for l in text.splitlines())
    fit = int(min(150, 2050 / (0.68 * longest)))
    style = random.choice([
        ["-swirl", str(random.randint(120, 600))],
        ["-implode", "-1.5"],
        ["-wave", "40x300"],
        ["-paint", "4"],
    ])
    cmd = [
        "magick", "-seed", str(seed), "-size", "640x400", "plasma:fractal",
        "-blur", "0x2", *style,
        "-modulate", f"100,{random.randint(180, 260)},{random.randint(0, 200)}",
        "-resize", "2304x1440!",
        "-font", "Liberation-Sans-Bold", "-pointsize", str(fit),
        "-gravity", "center", "-interline-spacing", "10",
        "-stroke", "black", "-strokewidth", "14", "-fill", "black",
        "-annotate", f"{rot}x{rot}+0-40", text,
        "-stroke", "none", "-fill", random.choice(["white", "yellow", "#7fffd4", "#ff9ff3"]),
        "-annotate", f"{rot}x{rot}+0-40", text,
        "(", "-background", "none", "-pointsize", "160",
        f"pango:<span font='Noto Color Emoji'>{em}</span>", "-bordercolor", "none", "-border", "30", ")",
        "-gravity", random.choice(["southeast", "southwest", "northeast", "northwest"]),
        "-geometry", "+60+60", "-composite",
        "(", "-background", "none", "-pointsize", "260",
        f"pango:<span font='Noto Color Emoji'>{em2}</span>", "-bordercolor", "none", "-border", "30",
        "-rotate", str(random.randint(-40, 40)), ")",
        "-gravity", random.choice(["north", "south", "east", "west"]), "-geometry", "+0+40", "-composite",
        "-quality", "85", out,
    ]

    def work():
        global _wp_busy
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            if os.path.exists(out):
                subprocess.run(["omarchy-shell", "-q", "background", "set", out],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        finally:
            _wp_busy = False

    if not _wp_busy:
        _wp_busy = True
        threading.Thread(target=work, daemon=True).start()
    return True


# ───────────────────────── шейдер на весь экран ─────────────────────────

sys.path.insert(0, HERE)
import shader  # noqa: E402


class Screen:
    def __init__(self, level):
        self.level = level
        self.burst_until = 0
        hypr_eval("hl.config({ debug = { damage_tracking = 0 } })")
        self.calm()

    def _set(self, src):
        path = shader.write(src)
        hypr_eval(f"hl.config({{ decoration = {{ screen_shader = '{path}' }} }})")

    def calm(self):
        self._set(shader.base(self.level))
        return False

    def burst(self, seconds=1.2):
        src, _ = shader.burst(self.level)
        self._set(src)
        GLib.timeout_add(int(seconds * 1000), self._maybe_calm, GLib.get_monotonic_time())
        self.burst_until = GLib.get_monotonic_time()
        return False

    def _maybe_calm(self, stamp):
        if stamp == self.burst_until:  # не было нового взрыва
            self.calm()
        return False


# ───────────────────────── твари ─────────────────────────

CSS = b"""
window.schizo { background: transparent; }
.bubble {
  border-radius: 22px; padding: 10px 16px; border: 4px solid black;
  font-family: "Liberation Sans"; font-weight: 900; font-size: 18px; color: black;
  box-shadow: 5px 5px 0 rgba(0,0,0,.6);
}
.creature { font-family: "Noto Color Emoji"; }
.scream { font-family: "Liberation Sans"; font-weight: 900; font-size: 150px; color: white; }
.screambg { background: black; }
.screambg.alt { background: #ff0040; }
@keyframes wob {
  0% { transform: rotate(-14deg) scale(1.0); }
  50% { transform: rotate(14deg) scale(1.2); }
  100% { transform: rotate(-14deg) scale(1.0); }
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes pop {
  0% { opacity: 0; transform: scale(0.1) rotate(60deg); }
  70% { opacity: 1; transform: scale(1.3) rotate(-8deg); }
  100% { opacity: 1; transform: scale(1) rotate(0); }
}
@keyframes shake {
  0% { transform: translate(0,0); } 25% { transform: translate(-12px,6px); }
  50% { transform: translate(10px,-8px); } 75% { transform: translate(-6px,-10px); } 100% { transform: translate(0,0); }
}
.wob { animation: wob 0.6s ease-in-out infinite; }
.spin { animation: spin 1.2s linear infinite; }
.pop { animation: pop 0.4s ease-out 1; }
.shake { animation: shake 0.12s linear infinite; }
"""

OUCH = ["АЙ", "НАС СТАЛО БОЛЬШЕ", "ты не можешь нас убить", "ЕЩЁ", "больно, но приятно",
        "я позову брата", "ХА-ХА-ХА", "ты кликаешь по мне, а я кликаю по тебе", "МИТОЗ!!!"]


def bubble_css(widget):
    prov = Gtk.CssProvider()
    h = random.random()
    prov.load_from_data(
        f".bubble {{ background: linear-gradient({random.randint(0, 359)}deg, "
        f"{hex_bright(h)}, {hex_bright(h + 0.25)}); }}".encode())
    widget.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)


class Creature:
    def __init__(self, swarm, x=None, y=None, emoji=None, size=None):
        self.swarm = swarm
        W, H = swarm.W, swarm.H
        self.size = size or random.randint(50, 110)
        self.x = x if x is not None else random.uniform(0, W - self.size)
        self.y = y if y is not None else random.uniform(0, H - self.size)
        sp = random.uniform(2, 7) * swarm.level
        a = random.uniform(0, 6.283)
        self.vx, self.vy = sp * math.cos(a), sp * math.sin(a)
        self.alive = True

        win = Gtk.Window(application=swarm.app)
        win.add_css_class("schizo")
        LS.init_for_window(win)
        LS.set_layer(win, LS.Layer.OVERLAY)
        LS.set_keyboard_mode(win, LS.KeyboardMode.NONE)
        LS.set_namespace(win, "schizo")
        LS.set_exclusive_zone(win, -1)
        LS.set_anchor(win, LS.Edge.TOP, True)
        LS.set_anchor(win, LS.Edge.LEFT, True)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.box.add_css_class("pop")
        self.face = Gtk.Label(label=emoji or random.choice(CREATURES))
        self.face.add_css_class("creature")
        self.face.add_css_class(random.choice(["wob", "wob", "spin", "shake"]))
        prov = Gtk.CssProvider()
        prov.load_from_data(f"label {{ font-size: {self.size}px; }}".encode())
        self.face.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.say_lbl = Gtk.Label(wrap=True, max_width_chars=22, justify=Gtk.Justification.CENTER)
        self.say_lbl.add_css_class("bubble")
        bubble_css(self.say_lbl)
        self.say_lbl.set_visible(False)
        self.box.append(self.say_lbl)
        self.box.append(self.face)

        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: swarm.hit(self))
        self.box.add_controller(click)

        win.set_child(self.box)
        self.win = win
        self.place()
        win.present()

    def place(self):
        LS.set_margin(self.win, LS.Edge.LEFT, int(self.x))
        LS.set_margin(self.win, LS.Edge.TOP, int(self.y))

    def say(self, text, secs=3.5):
        if not self.alive:
            return
        self.say_lbl.set_label(text)
        self.say_lbl.set_visible(True)
        GLib.timeout_add(int(secs * 1000), lambda: (self.alive and self.say_lbl.set_visible(False)) and False)

    def step(self, cx, cy):
        W, H = self.swarm.W, self.swarm.H
        # убегает от курсора
        dx, dy = self.x + self.size / 2 - cx, self.y + self.size / 2 - cy
        d2 = dx * dx + dy * dy
        if d2 < 260 ** 2:
            d = math.sqrt(d2) + 1
            push = 2.2 * self.swarm.level
            self.vx += dx / d * push
            self.vy += dy / d * push
        # немного случайности
        self.vx += random.uniform(-0.6, 0.6)
        self.vy += random.uniform(-0.6, 0.6)
        lim = 9 * self.swarm.level
        sp = math.hypot(self.vx, self.vy)
        if sp > lim:
            self.vx *= lim / sp
            self.vy *= lim / sp
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > W - self.size:
            self.vx *= -1
            self.x = max(0, min(self.x, W - self.size))
        if self.y < 0 or self.y > H - self.size - 40:
            self.vy *= -1
            self.y = max(0, min(self.y, H - self.size - 40))
        self.place()

    def die(self):
        if self.alive:
            self.alive = False
            self.win.destroy()


class Swarm:
    def __init__(self, app, args):
        self.app = app
        self.args = args
        self.level = args.level
        self.creatures = []
        self.cx = self.cy = -9999
        self.max = 6 + 8 * self.level
        try:
            m = json.loads(sh(["hyprctl", "monitors", "-j"]))[0]
            self.W, self.H = m["width"] / m["scale"], m["height"] / m["scale"]
        except Exception:
            self.W, self.H = 1600, 1000
        self.orig_bg = os.path.realpath(BG_LINK) if os.path.exists(BG_LINK) else None
        self.acid = None

        from gi.repository import Gdk
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ── запуск ──
    def start(self):
        if not self.args.no_acid:
            cmd = [sys.executable, os.path.join(HERE, "acid.py"), "--zoom",
                   "--intensity", str(0.6 + 0.4 * self.level)]
            if self.args.music:
                cmd.append("--music")
            self.acid = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)

        self.screen = Screen(self.level) if not self.args.no_shader else None
        paint_windows()
        GLib.timeout_add(1500, paint_windows)
        if not self.args.no_wallpaper:
            make_wallpaper()
            GLib.timeout_add_seconds(self.args.wallpaper_every, make_wallpaper)

        for _ in range(3 + self.level):
            self.spawn()
        GLib.timeout_add(33, self.frame)
        GLib.timeout_add(120, self.poll_cursor)
        GLib.timeout_add(int(4000 / self.level), self.breed)
        GLib.timeout_add(2500, self.chatter)
        GLib.timeout_add(int(random.uniform(8, 20) * 1000 / self.level), self.random_scream)
        GLib.timeout_add(int(random.uniform(5, 12) * 1000 / self.level), self.random_burst)
        threading.Thread(target=self.listen, daemon=True).start()

    # ── рой ──
    def spawn(self, **kw):
        if len(self.creatures) >= self.max:
            return None
        c = Creature(self, **kw)
        self.creatures.append(c)
        return c

    def frame(self):
        for c in self.creatures:
            c.step(self.cx, self.cy)
        return True

    def poll_cursor(self):
        try:
            x, y = sh(["hyprctl", "cursorpos"]).split(",")
            self.cx, self.cy = float(x), float(y)
        except Exception:
            pass
        return True

    def breed(self):
        self.spawn()
        # старые иногда дохнут, чтобы рой обновлялся
        if len(self.creatures) > self.max * 0.7 and random.random() < 0.5:
            old = self.creatures.pop(0)
            old.die()
        return True

    def chatter(self):
        if self.creatures and random.random() < 0.7:
            random.choice(self.creatures).say(bred())
        return True

    def hit(self, c):
        """Кликнул по твари — она делится."""
        if not c.alive:
            return
        for _ in range(2):
            kid = self.spawn(x=c.x, y=c.y, emoji=c.face.get_label(), size=max(40, int(c.size * 0.8)))
            if kid:
                kid.vx, kid.vy = random.uniform(-25, 25), random.uniform(-25, 25)
        if c in self.creatures:
            self.creatures.remove(c)
        c.die()
        if self.creatures:
            random.choice(self.creatures).say(random.choice(OUCH), 2)
        if self.screen:
            self.screen.burst(0.4)

    def everyone_says(self, text, n=3):
        for c in random.sample(self.creatures, min(n, len(self.creatures))):
            c.say(text, 3)

    # ── скример на весь экран ──
    def scream(self, text=None):
        text = text or random.choice(["ОНИ ЗНАЮТ", "НЕ ОБОРАЧИВАЙСЯ", "ОГУРЕЦ", "ТЫ МОРГНУЛ",
                                      "sudo rm -rf /ты", "ПРОСНИСЬ", "ЭТО НЕ ТВОЙ КОМП", "БУ"])
        win = Gtk.Window(application=self.app)
        LS.init_for_window(win)
        LS.set_layer(win, LS.Layer.OVERLAY)
        LS.set_keyboard_mode(win, LS.KeyboardMode.NONE)
        LS.set_exclusive_zone(win, -1)
        LS.set_namespace(win, "schizo")
        for e in (LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT, LS.Edge.RIGHT):
            LS.set_anchor(win, e, True)
        box = Gtk.Box()
        box.add_css_class("screambg")
        lbl = Gtk.Label(label=text, hexpand=True, vexpand=True, wrap=True)
        lbl.add_css_class("scream")
        lbl.add_css_class("shake")
        box.append(lbl)
        win.set_child(box)
        win.present()
        flips = [0]

        def blink():
            flips[0] += 1
            if flips[0] % 2:
                box.add_css_class("alt")
            else:
                box.remove_css_class("alt")
            if flips[0] > 6:
                win.destroy()
                return False
            return True

        GLib.timeout_add(70, blink)
        if self.screen:
            self.screen.burst(0.8)
        return False

    def random_scream(self):
        self.scream()
        GLib.timeout_add(int(random.uniform(15, 40) * 1000 / self.level), self.random_scream)
        return False

    def random_burst(self):
        if self.screen:
            self.screen.burst(random.uniform(0.6, 2.5))
        GLib.timeout_add(int(random.uniform(5, 14) * 1000 / self.level), self.random_burst)
        return False

    # ── реакция на твои действия ──
    def listen(self):
        import socket
        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
        path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr", sig, ".socket2.sock")
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
        except Exception as e:
            print("не смог подслушать Hyprland:", e)
            return
        buf = b""
        while True:
            data = s.recv(4096)
            if not data:
                return
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                ev, _, arg = line.decode(errors="replace").partition(">>")
                GLib.idle_add(self.on_event, ev, arg)

    def on_event(self, ev, arg):
        if ev == "openwindow":
            cls = arg.split(",")[2].split(".")[-1] if arg.count(",") >= 2 else "что-то"
            if self.screen:
                self.screen.burst(1.5)
            for _ in range(2 + self.level):
                self.spawn()
            self.everyone_says(random.choice([
                f"ОН ОТКРЫЛ {cls.upper()}!!!", f"{cls}? серьёзно?", f"мы ждали {cls}. мы всегда ждали",
                f"не трогай {cls}, он кусается", f"{cls} пришёл. все в укрытие"]), 4)
            paint_windows()
        elif ev == "closewindow":
            if self.screen:
                self.screen.burst(0.8)
            self.everyone_says(random.choice([
                "ТЫ УБИЛ ЕГО", "минута молчания…", "он был хорошим окном", "КТО СЛЕДУЮЩИЙ?",
                "мы запомним это"]), 3)
        elif ev == "workspace":
            if self.screen:
                self.screen.burst(1.0)
            if random.random() < 0.3:
                self.scream(random.choice(["КУДА ТЫ БЕЖИШЬ", f"ВОРКСПЕЙС {arg}", "ОТ НАС НЕ СПРЯТАТЬСЯ"]))
            elif not self.args.no_wallpaper:
                make_wallpaper()
            self.everyone_says(random.choice(["эй, подожди нас!", "мы уже тут", "ТЕЛЕПОРТ!!!"]), 2)
        elif ev == "activewindow" and random.random() < 0.25:
            cls = arg.split(",")[0].split(".")[-1]
            if cls:
                self.everyone_says(random.choice([
                    f"опять {cls}…", f"{cls} смотрит на тебя", f"фу, {cls}", f"я люблю {cls}"]), 1)
        elif ev == "fullscreen" and arg == "1":
            self.scream("НЕ ПРЯЧЬСЯ")
        return False

    # ── выход ──
    def stop(self, *_):
        print("\n🧘 отпускает... возвращаю реальность")
        for c in self.creatures:
            c.die()
        if self.acid:
            self.acid.send_signal(signal.SIGINT)
            try:
                self.acid.wait(timeout=3)
            except Exception:
                self.acid.kill()
        unpaint_windows()
        if self.orig_bg:
            subprocess.run(["omarchy-shell", "-q", "background", "set", self.orig_bg],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL)
        self.app.quit()
        return False


def main():
    ap = argparse.ArgumentParser(description="Полный пиздец для Hyprland")
    ap.add_argument("--level", type=int, default=2, choices=[1, 2, 3], help="1 — терпимо, 3 — ад")
    ap.add_argument("--music", action="store_true", help="качаться под музыку")
    ap.add_argument("--no-acid", action="store_true")
    ap.add_argument("--no-shader", action="store_true", help="без искажения экрана")
    ap.add_argument("--no-wallpaper", action="store_true")
    ap.add_argument("--wallpaper-every", type=int, default=10)
    args = ap.parse_args()

    from gi.repository import Gio
    app = Gtk.Application(application_id="dev.schizo.hypr", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def on_activate(a):
        a.hold()
        s = Swarm(a, args)
        for sig in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, s.stop)
        s.start()
        print(f"🍄 уровень {args.level}. Ctrl+C — вернуться в реальность (или: hyprctl reload)")

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
