"""Reel v3 — "Dá pra ler um atleta só pelas mãos?" (Cacheta League, ~24 s).

Uso:
  python3 reel_v3.py pasta_videos pasta_camadas fonte.ttf trilha.wav saida.mp4

pasta_camadas: fundo.png e carta.png gerados da arte de abertura (ver arte/camadas).
Trilha recomendada: trilha.py saida.wav 25 120 0  (120 BPM -> cada tempo = 0,5 s,
então todos os cortes do roteiro caem na batida).
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 24.0
FADE = 1.5

# Paleta da arte de abertura
AZUL = (4, 68, 116)
AZUL_TXT = (212, 236, 252)
AMARELO = (0xFE, 0xB0, 0x24)  # #feb024
ESCURO = (20, 20, 20)

# ---------------------------------------------------------------------------
# Roteiro de imagens: (arquivo, inicio, duracao, zoom, cx, cy)
# zoom = fração da altura do quadro original mantida (recorte 9:16, sem barras);
# cx/cy = posição do recorte (0 = esquerda/topo, 1 = direita/base).
# Nenhum take mostra rostos ou bebidas.
TAKES = [
    # 0–1,5 gancho: mão apontando a carta na mesa amarela
    ("IMG_7442.MOV", 0.5, 1.5, 1.00, 0.5, 0.5),
    # 1,5–4 desafio: mãos de perto com as cartas viradas
    ("IMG_7404.MOV", 2.0, 2.5, 0.55, 0.5, 1.0),
    # 4–9 contexto: backdrop Cacheta League + avental ABEMC
    ("IMG_7530.MOV", 0.3, 2.0, 0.28, 0.72, 0.0),
    ("IMG_7402.MOV", 0.2, 1.5, 0.50, 0.0, 1.0),
    ("IMG_7454.MOV", 0.0, 1.5, 0.55, 1.0, 0.75),
    # 9–16 habilidade: distribuindo / cartas na mesa / súmula na toalha azul
    ("IMG_7455.MOV", 2.0, 2.0, 0.55, 0.5, 1.0),
    ("IMG_7361.MOV", 5.0, 2.0, 0.75, 0.5, 1.0),
    ("IMG_7291.MOV", 2.0, 3.0, 0.45, 0.5, 1.0),
    # 16–20 posicionamento: banner sob o telhado (dia e noite)
    ("IMG_7227.MOV", 0.0, 2.5, 0.32, 0.0, 0.0),
    ("IMG_7453.MOV", 7.8, 1.5, 0.30, 0.3, 0.0),
]
INICIO_CTA = 20.0  # 20–24: volta para a mesa verde com a marca

# Textos: (inicio, fim, [(texto, estilo)], carta_no_fim_da_1a_linha)
# estilos: "azul" (caixa azul, texto claro), "amarela" (faixa #feb024),
#          "destaque" (caixa azul, texto amarelo grande), "azul_p" (azul menor)
TEXTOS = [
    (0.05, 1.5, [("SÁBADO É DIA DE MESA", "azul")], True),
    (1.55, 4.0, [("DÁ PRA LER UM ATLETA", "azul"), ("SÓ PELAS MÃOS?", "amarela")], False),
    (4.1, 6.5, [("MESA DE VERDADE.", "azul")], False),
    (6.5, 9.0, [("MESA DE VERDADE.", "azul"), ("TORNEIO DE VERDADE.", "amarela")], False),
    (9.05, 11.0, [("LEITURA.", "destaque")], False),
    (11.05, 13.0, [("MEMÓRIA.", "destaque")], False),
    (13.05, 16.0, [("DECISÃO", "destaque"), ("SOB PRESSÃO.", "amarela_g")], False),
    (16.1, 20.0, [("AQUI O CARTEADO É", "azul"), ("ESPORTE DA MENTE.", "amarela")], False),
    (20.1, 24.0, [("SÁBADO É DIA DE MESA.", "azul"), ("QUAL VOCÊ DISPUTA HOJE?", "amarela"),
                  ("TRUCO, CACHETA OU POKER?", "azul_p")], True),
]
PASSO_PALAVRA = 0.13  # intervalo entre palavras (legenda palavra a palavra)
REVELADO_DE = {6.5: 3}  # bloco que repete a linha anterior já começa com 3 palavras visíveis

ESTILOS = {
    #            tamanho, caixa,   texto,    pad_x, pad_y, recuo, inclinação
    "azul":      (118, AZUL, AZUL_TXT, 26, 14, 0, 0.0),
    "azul_p":    (86, AZUL, AZUL_TXT, 22, 12, 0, 0.0),
    "amarela":   (84, AMARELO, ESCURO, 18, 8, 70, -1.6),
    "amarela_g": (120, AMARELO, ESCURO, 26, 12, 40, -1.6),
    "destaque":  (190, AZUL, AMARELO, 34, 18, 0, 0.0),
}
X0, Y0 = 48, 640  # canto do bloco de texto (mesma região do título da arte)
LARGURA_MAX = W - X0 - 120  # deixa livre a coluna de botões do Reels


def ease_out_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_out_back(t, k=1.8):
    t = min(max(t, 0.0), 1.0)
    return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2


def run(cmd):
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# Vídeo base
def render_take(src, ini, dur, zoom, cx, cy, out):
    n = round(dur * FPS)
    rec = ""
    if zoom < 1:
        rec = f"crop=w=iw*{zoom}:h=ih*{zoom}:x=(iw-iw*{zoom})*{cx}:y=(ih-ih*{zoom})*{cy},"
    # escala para o dobro e usa zoompan para um zoom lento e suave (1.00 -> 1.08)
    vf = (f"{rec}scale={2 * W}:{2 * H}:force_original_aspect_ratio=increase,crop={2 * W}:{2 * H},"
          f"fps={FPS},zoompan=z='1+0.08*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
          f"d=1:s={W}x{H}:fps={FPS},eq=contrast=1.06:saturation=1.12,format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(ini), "-t", str(dur + 0.2), "-i", src,
         "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "16",
         "-preset", "fast", out])


def video_base(pasta, tmp):
    partes = []
    for i, (arq, ini, dur, z, cx, cy) in enumerate(TAKES):
        out = os.path.join(tmp, f"take_{i:02d}.mp4")
        render_take(os.path.join(pasta, arq), ini, dur, z, cx, cy, out)
        partes.append(out)
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    base = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
         "-c", "copy", base])
    return base


# ---------------------------------------------------------------------------
# Textos no estilo da arte
class Tipografia:
    def __init__(self, fonte):
        self.fonte_path = fonte
        self._cache = {}

    def fonte(self, estilo, esc=1.0):
        tam = round(ESTILOS[estilo][0] * esc)
        if tam not in self._cache:
            self._cache[tam] = ImageFont.truetype(self.fonte_path, tam)
        return self._cache[tam]

    def larg(self, estilo, txt, esc=1.0):
        return self.fonte(estilo, esc).getlength(txt)


def desenhar_linha(camada, tip, estilo, esc, palavras, n_vis, t_ultima, t, x, y):
    """Desenha uma linha com n_vis palavras visíveis; a última entra deslizando."""
    tam, cor_caixa, cor_txt, px, py, recuo, incl = ESTILOS[estilo]
    tam, px, py = tam * esc, round(px * esc), round(py * esc)
    fonte = tip.fonte(estilo, esc)
    asc, desc = fonte.getmetrics()
    alt = round(tam * 0.86) + 2 * py  # caixa justa nas maiúsculas (como na arte)
    if n_vis <= 0:
        return alt
    esp = fonte.getlength(" ")
    larguras = [fonte.getlength(p) for p in palavras]
    # a caixa cresce junto com a palavra que está entrando
    p_ult = ease_out_cubic((t - t_ultima) / 0.12)
    larg_txt = sum(larguras[:n_vis - 1]) + esp * (n_vis - 1) + larguras[n_vis - 1] * p_ult
    larg_total = round(sum(larguras) + esp * (len(palavras) - 1) + 2 * px)
    img = Image.new("RGBA", (larg_total + 4, alt + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, round(larg_txt + 2 * px), alt), fill=cor_caixa + (255,))
    topo_txt = py - round(asc - tam * 0.86) + round(tam * 0.02)
    cx = px
    for i in range(n_vis):
        a = 255
        dy = 0
        if i == n_vis - 1:
            a = round(255 * p_ult)
            dy = round(18 * (1 - p_ult))
        if a > 0:
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((cx, topo_txt + dy), palavras[i], font=fonte,
                                     fill=cor_txt + (a,))
            img.alpha_composite(lay)
        cx += larguras[i] + esp
    if incl:
        img = img.rotate(incl, Image.BICUBIC, expand=True)
    camada.alpha_composite(img, (x + recuo, y))
    return alt


def quebrar(tip, texto, estilo):
    """Uma linha só, reduzindo a fonte até 72% se preciso; senão quebra em linhas."""
    _, _, _, px, _, recuo, _ = ESTILOS[estilo]
    esc = min(1.0, (LARGURA_MAX - 2 * px - recuo) / tip.larg(estilo, texto))
    if esc >= 0.72:
        return [(texto.split(), esc)]
    return [(l, 1.0) for l in quebrar_palavras(tip, texto, estilo)]


def quebrar_palavras(tip, texto, estilo):
    palavras = texto.split()
    linhas, atual = [], []
    for p in palavras:
        teste = " ".join(atual + [p])
        _, _, _, px, _, recuo, _ = ESTILOS[estilo]
        if atual and tip.larg(estilo, teste) + 2 * px + recuo > LARGURA_MAX:
            linhas.append(atual)
            atual = [p]
        else:
            atual.append(p)
    linhas.append(atual)
    return linhas


def camada_textos(t, tip, carta):
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for ini, fim, linhas, com_carta in TEXTOS:
        if not (ini <= t < fim):
            continue
        y = Y0 if linhas[0][1] != "destaque" else Y0 + 60
        k = REVELADO_DE.get(ini, 0)  # palavras já visíveis no início do bloco
        idx = 0
        fim_primeira = None
        for texto, estilo in linhas:
            for palavras, esc in quebrar(tip, texto, estilo):
                tempos = []
                for _ in palavras:
                    tempos.append(ini + max(idx - k, 0) * PASSO_PALAVRA - (1 if idx < k else 0))
                    idx += 1
                n_vis = sum(1 for tp in tempos if t >= tp)
                t_ult = tempos[n_vis - 1] if n_vis else 0
                alt = desenhar_linha(camada, tip, estilo, esc, palavras, n_vis, t_ult, t, X0, y)
                if fim_primeira is None:
                    px = round(ESTILOS[estilo][3] * esc)
                    fim_primeira = (X0 + round(tip.larg(estilo, " ".join(palavras), esc) + 2 * px),
                                    y, alt, tempos[-1])
                y += alt + 12
        if com_carta and fim_primeira:
            xf, yf, alt, t_pal = fim_primeira
            pc = (t - t_pal - 0.08) / 0.35
            if pc > 0:
                esc = max(ease_out_back(pc, 2.2), 0.01)
                h_c = alt * 1.27 * esc
                c = carta.resize((max(1, round(carta.width * h_c / carta.height)), max(1, round(h_c))),
                                 Image.LANCZOS)
                ang = -25 * (1 - ease_out_cubic(pc)) + 3 * math.sin(2 * math.pi * max(t - t_pal, 0) / 1.6)
                c = c.rotate(ang, Image.BICUBIC, expand=True)
                cx = xf + 4 + alt * 1.27 * carta.width / carta.height / 2
                cy = yf + alt / 2 - alt * 0.08
                camada.alpha_composite(c, (round(cx - c.width / 2), round(cy - c.height / 2)))
    return camada


def selo_18(tip, t):
    """Selo 18+ e 'DISPUTE COM RESPONSABILIDADE' na lateral esquerda."""
    p = ease_out_cubic((t - INICIO_CTA - 0.3) / 0.4)
    if p <= 0:
        return None
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    r = 46
    cx, cy = 34 + r, 1240
    a = round(255 * p)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=AZUL + (a,), outline=AMARELO + (a,), width=6)
    f18 = ImageFont.truetype(tip.fonte_path, 50)
    d.text((cx, cy + 2), "18+", font=f18, fill=AMARELO + (a,), anchor="mm")
    fl = ImageFont.truetype(tip.fonte_path, 34)
    txt = "DISPUTE COM RESPONSABILIDADE"
    lw = round(fl.getlength(txt)) + 24
    faixa = Image.new("RGBA", (lw, 50), AZUL + (a,))
    ImageDraw.Draw(faixa).text((lw // 2, 26), txt, font=fl, fill=AZUL_TXT + (a,), anchor="mm")
    faixa = faixa.rotate(90, expand=True)
    camada.alpha_composite(faixa, (cx - faixa.width // 2, cy + r + 14))
    return camada


def fundo_cta(fundo, t):
    # mesa verde da arte, zoom lento
    z = 1 + 0.05 * (t - INICIO_CTA) / (DUR - INICIO_CTA)
    w, h = W / z, H / z
    x0, y0 = (W - w) / 2, (H * 0.45) - h * 0.45
    return fundo.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


# ---------------------------------------------------------------------------
def main(pasta, camadas, fonte, trilha, saida):
    # REEL_TMP permite reaproveitar os takes já renderizados ao ajustar só os textos
    tmp = os.environ.get("REEL_TMP") or tempfile.mkdtemp(prefix="reel_v3_")
    os.makedirs(tmp, exist_ok=True)
    base = os.path.join(tmp, "base.mp4")
    if not os.path.exists(base):
        base = video_base(pasta, tmp)
    tip = Tipografia(fonte)
    fundo = Image.open(os.path.join(camadas, "fundo.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    carta = Image.open(os.path.join(camadas, "carta.png")).convert("RGBA")

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", base, "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", trilha,
        "-filter_complex",
        f"[0:v]fade=t=out:st={DUR - FADE}:d={FADE}[v];"
        f"[1:a]atrim=0:{DUR},afade=t=in:d=0.05,afade=t=out:st={DUR - FADE}:d={FADE}[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", str(DUR), saida], stdin=subprocess.PIPE)
    tam = W * H * 3
    for i in range(round(DUR * FPS)):
        t = i / FPS
        if t < INICIO_CTA:
            buf = dec.stdout.read(tam)
            quadro = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).convert("RGBA")
        else:
            quadro = fundo_cta(fundo, t).convert("RGBA")
        quadro.alpha_composite(camada_textos(t, tip, carta))
        s = selo_18(tip, t)
        if s is not None:
            quadro.alpha_composite(s)
        enc.stdin.write(quadro.convert("RGB").tobytes())
    enc.stdin.close()
    dec.stdout.close()
    dec.wait()
    if enc.wait():
        raise SystemExit("ffmpeg falhou")
    print(saida, f"{DUR:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:6])
