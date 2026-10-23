"""Gera 3 vídeos crus de 15 s (sem texto, sem música, sem filtro): mãos, cartas, súmula.

Uso: python3 crus.py pasta_videos pasta_saida

Cada take: (arquivo, inicio, duracao, zoom, cx, cy). zoom = fração da altura do
quadro original (recorte 9:16, sem barras); cx/cy = posição do recorte
(0 = esquerda/topo, 1 = direita/base). Nenhum take mostra rostos ou bebidas.
Mantém o som ambiente original, com microfades nos cortes para evitar estalos.
"""
import os
import subprocess
import sys
import tempfile

W, H, FPS = 1080, 1920, 30

VIDEOS = {
    "mesa_de_verdade_1_maos": [
        ("IMG_7442.MOV", 0.3, 4.0, 1.00, 0.5, 0.5),
        ("IMG_7404.MOV", 2.0, 4.0, 0.55, 0.5, 1.0),
        ("IMG_7441.MOV", 3.5, 3.0, 0.55, 0.5, 1.0),
        ("IMG_7455.MOV", 1.8, 4.0, 0.55, 0.5, 1.0),
    ],
    "mesa_de_verdade_2_cartas": [
        ("IMG_7414.MOV", 0.4, 4.0, 0.50, 0.5, 1.0),
        ("IMG_7258.MOV", 4.6, 1.5, 1.00, 0.5, 0.5),
        ("IMG_7361.MOV", 3.9, 3.5, 0.75, 0.5, 1.0),
        ("IMG_7653.MOV", 1.0, 3.0, 0.50, 0.5, 1.0),
        ("IMG_7402.MOV", 0.2, 3.0, 0.50, 0.0, 1.0),
    ],
    "mesa_de_verdade_3_sumula": [
        ("IMG_7379.MOV", 0.2, 4.0, 0.45, 0.4, 1.0),
        ("IMG_7408.MOV", 4.5, 4.0, 1.00, 0.5, 0.5),
        ("IMG_7291.MOV", 2.0, 3.0, 0.45, 0.5, 1.0),
        ("IMG_7426.MOV", 1.0, 4.0, 0.40, 0.15, 1.0),
    ],
}


def run(cmd):
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)


def take(src, ini, dur, zoom, cx, cy, out):
    n = round(dur * FPS)
    rec = ""
    if zoom < 1:
        rec = f"crop=w=iw*{zoom}:h=ih*{zoom}:x=(iw-iw*{zoom})*{cx}:y=(ih-ih*{zoom})*{cy},"
    vf = f"{rec}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},format=yuv420p"
    af = f"atrim=0:{dur},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={dur - 0.03}:d=0.03,aresample=48000"
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(ini), "-t", str(dur + 0.2), "-i", src,
         "-vf", vf, "-af", af, "-frames:v", str(n), "-c:v", "libx264", "-crf", "16",
         "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", out])


def main(pasta, saida_dir):
    os.makedirs(saida_dir, exist_ok=True)
    for nome, takes in VIDEOS.items():
        tmp = tempfile.mkdtemp(prefix=nome + "_")
        partes = []
        for i, (arq, ini, dur, z, cx, cy) in enumerate(takes):
            out = os.path.join(tmp, f"{i:02d}.mp4")
            take(os.path.join(pasta, arq), ini, dur, z, cx, cy, out)
            partes.append(out)
        lista = os.path.join(tmp, "lista.txt")
        with open(lista, "w") as f:
            f.writelines(f"file '{p}'\n" for p in partes)
        saida = os.path.join(saida_dir, nome + ".mp4")
        # concat com recodificação curta para timestamps contínuos de áudio e vídeo
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", saida])
        total = sum(t[2] for t in takes)
        print(saida, f"{total:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:3])
