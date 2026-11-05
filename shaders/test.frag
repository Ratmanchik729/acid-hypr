#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
uniform float time;
out vec4 fragColor;
void main() {
    vec2 uv = v_texcoord;
    uv.x += sin(uv.y * 20.0 + time * 3.0) * 0.01;
    vec4 c = texture(tex, uv);
    fragColor = vec4(c.b, c.r, c.g, c.a);
}
