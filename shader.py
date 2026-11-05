"""Генератор GLSL-шейдеров на весь экран для Hyprland."""
import os
import random

DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "schizo-shaders")

HEAD = """#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
uniform float time;
out vec4 fragColor;

float hash(float n) { return fract(sin(n) * 43758.5453); }

vec3 hue(vec3 c, float a) {
    const mat3 toYIQ = mat3(0.299, 0.596, 0.211, 0.587, -0.274, -0.523, 0.114, -0.322, 0.312);
    const mat3 toRGB = mat3(1.0, 1.0, 1.0, 0.956, -0.272, -1.106, 0.621, -0.647, 1.703);
    vec3 yiq = toYIQ * c;
    float h = atan(yiq.z, yiq.y) + a;
    float ch = length(yiq.yz);
    return toRGB * vec3(yiq.x, ch * cos(h), ch * sin(h));
}
"""

# Как искажать координаты в разных режимах
UV = {
    "calm": "",
    "flip": "uv.y = 1.0 - uv.y;",
    "mirror": "uv.x = 1.0 - uv.x;",
    "kaleido": "uv = abs(uv * 2.0 - 1.0); uv = vec2(1.0) - uv;",
    "pixel": "uv = floor(uv * vec2(96.0, 60.0)) / vec2(96.0, 60.0);",
    "tunnel": """vec2 p = uv - 0.5; float r = length(p); float a = atan(p.y, p.x) + sin(t * 2.0) * (0.6 - r);
                 uv = 0.5 + vec2(cos(a), sin(a)) * r * (1.0 + 0.15 * sin(t * 6.0 - r * 20.0));""",
    "melt": "uv.y -= abs(sin(uv.x * 40.0 + hash(floor(uv.x * 40.0)) * 6.28)) * 0.08 * (0.5 + 0.5 * sin(t));",
    "drunk": "uv += vec2(sin(t * 1.3), cos(t * 1.7)) * 0.03; uv = (uv - 0.5) * (1.0 + 0.05 * sin(t * 2.1)) + 0.5;",
}

COLOR = {
    "calm": "",
    "invert": "c = vec3(1.0) - c;",
    "thermal": "float l = dot(c, vec3(0.3, 0.59, 0.11)); c = hue(vec3(1.0, 0.0, 0.0), l * 6.0 + t) * (0.4 + l);",
    "poster": "c = floor(c * 3.0) / 3.0;",
    "bw": "c = vec3(step(0.45, dot(c, vec3(0.3, 0.59, 0.11))));",
    "swap": "c = c.brg;",
}


def build(wave, ca, glitch, hue_speed, hue_mix, uv_mode="calm", color_mode="calm"):
    return HEAD + f"""
void main() {{
    float t = time;
    vec2 uv = v_texcoord;
    {UV[uv_mode]}
    uv.x += sin(uv.y * 18.0 + t * 3.0) * {wave:.4f};
    uv.y += cos(uv.x * 12.0 + t * 2.2) * {wave * 0.6:.4f};

    // глитч-полосы
    float g = floor(t * 9.0);
    float band = floor(uv.y * 30.0);
    if (hash(band + g * 13.1) > {1.0 - glitch:.3f}) uv.x += (hash(band * 7.3 + g) - 0.5) * 0.2;

    float ca = {ca:.4f} * (1.0 + sin(t * 5.0));
    vec3 c = vec3(texture(tex, uv + vec2(ca, 0.0)).r,
                  texture(tex, uv).g,
                  texture(tex, uv - vec2(ca, ca * 0.5)).b);
    c = mix(c, hue(c, t * {hue_speed:.3f}), {hue_mix:.3f});
    {COLOR[color_mode]}
    c *= 0.93 + 0.07 * sin(uv.y * 1100.0 + t * 30.0);
    fragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}}
"""


_n = 0


def write(src):
    """Пишем в новый файл каждый раз, чтобы Hyprland точно перечитал."""
    global _n
    os.makedirs(DIR, exist_ok=True)
    _n += 1
    path = os.path.join(DIR, f"s{_n % 4}.frag")
    with open(path, "w") as f:
        f.write(src)
    return path


def base(level):
    return build(wave=0.002 * level, ca=0.002 * level, glitch=0.02 * level,
                 hue_speed=0.25 * level, hue_mix=0.25 * level)


def burst(level):
    uv = random.choice(["flip", "mirror", "kaleido", "pixel", "tunnel", "melt", "drunk", "calm"])
    col = random.choice(["invert", "thermal", "poster", "bw", "swap", "calm"])
    return build(wave=0.012 * level, ca=0.012 * level, glitch=0.15 * level,
                 hue_speed=1.5, hue_mix=1.0, uv_mode=uv, color_mode=col), f"{uv}+{col}"
