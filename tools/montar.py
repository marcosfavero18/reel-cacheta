"""Monta o reel vertical 9:16 "Sábado é dia de mesa".

Uso: python3 montar.py cortes.txt pasta_videos trilha.wav saida.mp4 abertura.mp4 [encerramento.mp4]
(abertura e encerramento são gerados por abertura_animada.py)

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


def run(cmd):
    subprocess.run(cmd, check=True)


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
        "-vf", vf, "-frames:v", str(round(dur * FPS)), "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium", out,
    ])


def duracao(arq):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", arq], capture_output=True, text=True, check=True)
    return float(out.stdout)


def main(cortes, pasta, trilha, saida, abertura, encerramento=None):
    tmp = tempfile.mkdtemp(prefix="reel_")
    partes = [os.path.abspath(abertura)]
    with open(cortes) as f:
        linhas = [l.split() for l in f if l.strip() and not l.startswith("#")]
    for i, (arq, ini, dur, *rec) in enumerate(linhas, 1):
        out = os.path.join(tmp, f"{i:02d}.mp4")
        take(os.path.join(pasta, arq), float(ini), float(dur), out, *map(float, rec))
        partes.append(out)
    if encerramento:
        partes.append(os.path.abspath(encerramento))
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    video = os.path.join(tmp, "video.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
         "-c", "copy", video])
    total = sum(duracao(p) for p in partes)
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
    main(*sys.argv[1:7])
