"""Anima a arte de abertura e gera o encerramento com o logo Cacheta League.

Uso: python3 abertura_animada.py pasta_camadas saida_abertura.mp4 saida_encerramento.mp4

pasta_camadas precisa ter (recortados da arte original 899x1599):
  fundo.png    arte sem o título (feltro reconstruído)
  azul.png     faixa "SÁBADO É DIA DE MESA" (RGBA) -> posição (36, 555)
  amarela.png  faixa "BORA MOSTRAR ..." (RGBA) -> posição (100, 650)
  carta.png    carta do coringa (RGBA)        -> posição (718, 520)
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw

W, H, FPS = 1080, 1920, 30
S = W / 899  # escala da arte original para 1080x1920
DUR_ABERTURA = 4.8
DUR_FIM = 2.4


def ease_out_cubic(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def ease_out_back(t, k=1.7):
    t = min(max(t, 0), 1)
    return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2


def prog(t, a, b):
    return min(max((t - a) / (b - a), 0), 1)


def carregar(pasta):
    def up(nome, modo="RGB"):
        im = Image.open(os.path.join(pasta, nome)).convert(modo)
        return im.resize((round(im.width * S), round(im.height * S)), Image.LANCZOS)
    return up("fundo.png"), up("azul.png", "RGBA"), up("amarela.png", "RGBA"), up("carta.png", "RGBA")


def fundo_zoom(fundo, z, cx, cy):
    # recorta uma janela 1/z da imagem centrada em (cx, cy) e amplia
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    return fundo.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


def escurecer(im, f):
    if f >= 1:
        return im
    return Image.blend(Image.new("RGB", im.size, "black"), im, f)


def quadro_abertura(t, fundo, azul, amarela, carta):
    frame = fundo_zoom(fundo, 1 + 0.05 * t / DUR_ABERTURA, W / 2, 0.42 * H)
    frame = escurecer(frame, ease_out_cubic(prog(t, 0, 0.5)))

    # faixa azul desliza da esquerda
    pa = ease_out_back(prog(t, 0.35, 0.85), 1.2)
    xa = round(36 * S - (1 - pa) * (azul.width + 60))
    frame.paste(azul, (xa, round(555 * S)), azul)

    # brilho passando pela faixa azul
    pb = prog(t, 1.9, 2.5)
    if 0 < pb < 1:
        brilho = Image.new("L", azul.size, 0)
        bx = -200 + pb * (azul.width + 400)
        ImageDraw.Draw(brilho).polygon(
            [(bx, 0), (bx + 90, 0), (bx + 30, azul.height), (bx - 60, azul.height)], fill=110)
        branco = Image.new("RGB", azul.size, "white")
        brilho.paste(0, mask=Image.eval(azul.getchannel("A"), lambda v: 255 - v))
        frame.paste(branco, (round(36 * S), round(555 * S)), brilho)

    # faixa amarela desliza da direita
    py = ease_out_cubic(prog(t, 0.75, 1.2))
    xy = round(100 * S + (1 - py) * (W - 100 * S + 40))
    frame.paste(amarela, (xy, round(650 * S)), amarela)

    # carta do coringa: salta girando e depois flutua de leve
    pc = prog(t, 1.1, 1.6)
    if pc > 0:
        esc = max(ease_out_back(pc, 2.2), 0.01)
        ang = -25 * (1 - ease_out_cubic(pc)) + 3 * math.sin(2 * math.pi * max(t - 1.6, 0) / 1.6)
        c = carta.resize((max(1, round(carta.width * esc)), max(1, round(carta.height * esc))),
                         Image.LANCZOS).rotate(ang, Image.BICUBIC, expand=True)
        cx = 718 * S + carta.width / 2
        cy = 520 * S + carta.height / 2
        frame.paste(c, (round(cx - c.width / 2), round(cy - c.height / 2)), c)
    return frame


def quadro_fim(t, fundo):
    # zoom lento no logo Cacheta League (centro do logo ~ (450, 250) na arte)
    p = ease_out_cubic(t / DUR_FIM)
    frame = fundo_zoom(fundo, 1.15 + 0.35 * p, 450 * S, 250 * S)
    return escurecer(frame, ease_out_cubic(prog(t, 0, 0.4)))


def gravar(quadros, n, saida):
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", saida],
        stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(quadros(i / FPS).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise SystemExit("ffmpeg falhou")


def main(pasta, saida_abertura, saida_fim):
    fundo, azul, amarela, carta = carregar(pasta)
    gravar(lambda t: quadro_abertura(t, fundo, azul, amarela, carta),
           round(DUR_ABERTURA * FPS), saida_abertura)
    gravar(lambda t: quadro_fim(t, fundo), round(DUR_FIM * FPS), saida_fim)


if __name__ == "__main__":
    main(*sys.argv[1:4])
