"""Monta o reel vertical 9:16 "Sábado é dia de mesa".

Uso: python3 montar.py cortes.txt pasta_videos fonte.ttf trilha.wav saida.mp4

cortes.txt: uma linha por take -> "ARQUIVO INICIO DURACAO [ZOOM CX CY]".
ZOOM = fração da altura mantida (1 = quadro inteiro); CX/CY = posição do
recorte (0 = esquerda/topo, 1 = direita/base). O recorte mantém 9:16, então
o resultado preenche a tela de stories sem barras pretas.
Linhas iniciadas com # são ignoradas.
"""
import os
import subprocess
import sys
import tempfile

W, H, FPS = 1080, 1920, 30
TITULO = "SÁBADO É DIA DE MESA"
DUR_TITULO = 4.8  # 2 compassos da trilha: os cortes caem no tempo forte


def run(cmd):
    subprocess.run(cmd, check=True)


def abertura(fonte, out):
    # Fundo verde-feltro escuro com vinheta; letreiro entra com fade.
    linhas = ["SÁBADO É", "DIA DE MESA"]
    draws = []
    for i, txt in enumerate(linhas):
        y = f"(h/2)-160+{i}*190"
        st = 0.25 + 0.35 * i
        draws.append(
            f"drawtext=fontfile='{fonte}':text='{txt}':fontsize=170:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}:"
            f"alpha='if(lt(t,{st}),0,min(1,(t-{st})/0.5))*if(gt(t,{DUR_TITULO-0.4}),max(0,({DUR_TITULO}-t)/0.4),1)':"
            f"shadowcolor=black@0.6:shadowx=4:shadowy=4"
        )
    # fio dourado embaixo do título
    draws.append(
        f"drawbox=x=(iw-360)/2:y=ih/2+250:w='360':h=8:color=0xE8B64C@1:t=fill:"
        f"enable='between(t,0.9,{DUR_TITULO-0.4})'"
    )
    vf = f"vignette=PI/4," + ",".join(draws) + ",format=yuv420p"
    run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
        "-i", f"color=c=0x0E3B2A:s={W}x{H}:r={FPS}:d={DUR_TITULO}",
        "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "medium", out,
    ])


def take(src, ini, dur, out, zoom=1.0, cx=0.5, cy=0.5):
    # Corta, enquadra em 9:16 (sem barras), leve ajuste de cor, sem áudio.
    rec = ""
    if zoom < 1:
        rec = (f"crop=w=iw*{zoom}:h=ih*{zoom}:"
               f"x=(iw-iw*{zoom})*{cx}:y=(ih-ih*{zoom})*{cy},")
    vf = (
        f"{rec}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"fps={FPS},eq=contrast=1.06:saturation=1.12,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-v", "error", "-ss", str(ini), "-t", str(dur), "-i", src,
        "-vf", vf, "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium", out,
    ])


def main(cortes, pasta, fonte, trilha, saida):
    tmp = tempfile.mkdtemp(prefix="reel_")
    partes = [os.path.join(tmp, "00_abertura.mp4")]
    abertura(fonte, partes[0])
    with open(cortes) as f:
        linhas = [l.split() for l in f if l.strip() and not l.startswith("#")]
    for i, (arq, ini, dur, *rec) in enumerate(linhas, 1):
        out = os.path.join(tmp, f"{i:02d}.mp4")
        take(os.path.join(pasta, arq), float(ini), float(dur), out, *map(float, rec))
        partes.append(out)
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    video = os.path.join(tmp, "video.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
         "-c", "copy", video])
    total = DUR_TITULO + sum(float(l[2]) for l in linhas)
    run([
        "ffmpeg", "-y", "-v", "error", "-i", video, "-i", trilha,
        "-filter_complex", f"[1:a]atrim=0:{total},afade=t=out:st={total-1.5}:d=1.5[a]",
        "-vf", f"fade=t=out:st={total-1.0}:d=1.0",
        "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "18",
        "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest", saida,
    ])
    print(saida, f"{total:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:6])
