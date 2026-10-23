"""Lote de vídeos crus de 15 s (mesmo padrão de crus.py) com o restante do material.

Uso: python3 crus_lote.py pasta_videos pasta_saida

Nenhum trecho repete o que já foi usado nos 3 primeiros vídeos (crus.py) nem
entre os vídeos deste lote. Todos os takes foram revisados quadro a quadro e
passaram por detector de rostos (YuNet): sem rostos e sem bebidas.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crus  # noqa: E402

# (arquivo, inicio, duracao, zoom, cx, cy)
LOTE = {
    "mesa_de_verdade_4_maos": [
        ("IMG_7229.MOV", 0.2, 4.0, 0.45, 0.5, 1.0),
        ("IMG_7441.MOV", 0.2, 3.3, 0.45, 0.5, 1.0),
        ("IMG_7430.MOV", 0.3, 4.0, 0.35, 0.6, 1.0),
        ("IMG_7269.MOV", 0.2, 3.7, 0.45, 0.5, 1.0),
    ],
    "mesa_de_verdade_5_maos": [
        ("IMG_7404.MOV", 6.0, 3.6, 0.55, 0.5, 1.0),
        ("IMG_7454.MOV", 1.6, 3.8, 0.50, 0.5, 1.0),
        ("IMG_7506.MOV", 0.2, 4.0, 0.45, 0.5, 1.0),
        ("IMG_7361.MOV", 0.3, 3.6, 0.55, 0.5, 1.0),
    ],
    "mesa_de_verdade_6_maos": [
        ("IMG_7430.MOV", 4.5, 4.0, 0.35, 0.6, 1.0),
        ("IMG_7423.MOV", 1.4, 3.7, 0.40, 0.5, 1.0),
        ("IMG_7700.MOV", 0.3, 4.0, 0.40, 0.5, 1.0),
        ("IMG_7404.MOV", 0.3, 1.7, 0.55, 0.5, 1.0),
        ("IMG_7455.MOV", 0.2, 1.6, 0.50, 0.5, 1.0),
    ],
    "mesa_de_verdade_7_cartas": [
        ("IMG_7704.MOV", 0.3, 4.0, 0.40, 0.5, 1.0),
        ("IMG_7448.MOV", 0.2, 3.8, 0.70, 0.5, 1.0),
        ("IMG_7347.MOV", 0.3, 3.5, 0.50, 0.5, 1.0),
        ("IMG_7436.MOV", 0.2, 2.6, 0.45, 0.5, 1.0),
        ("IMG_7361.MOV", 7.4, 1.1, 0.50, 0.5, 1.0),
    ],
    "mesa_de_verdade_8_cartas": [
        ("IMG_7359.MOV", 2.0, 4.0, 0.70, 0.5, 1.0),
        ("IMG_7704.MOV", 9.8, 4.0, 0.40, 0.5, 1.0),
        ("IMG_7347.MOV", 3.8, 1.7, 0.50, 0.5, 1.0),
        ("IMG_7653.MOV", 4.0, 2.0, 0.50, 0.5, 1.0),
        ("IMG_7402.MOV", 3.2, 2.0, 0.45, 0.5, 1.0),
        ("IMG_7387.MOV", 1.2, 1.3, 0.40, 0.5, 1.0),
    ],
    "mesa_de_verdade_9_sumula": [
        ("IMG_7408.MOV", 0.2, 4.0, 1.00, 0.5, 0.5),
        ("IMG_7388.MOV", 0.3, 3.9, 0.40, 0.5, 1.0),
        ("IMG_7291.MOV", 0.2, 1.8, 0.45, 0.5, 1.0),
        ("IMG_7379.MOV", 4.2, 1.1, 0.45, 0.4, 1.0),
        ("IMG_7426.MOV", 5.0, 1.2, 0.40, 0.15, 1.0),
        ("IMG_7408.MOV", 8.5, 1.0, 1.00, 0.5, 0.5),
        ("IMG_7197.MOV", 0.5, 2.0, 0.45, 0.3, 1.0),
    ],
    "mesa_de_verdade_10_marca": [
        ("IMG_7530.MOV", 0.3, 2.5, 0.28, 0.72, 0.0),
        ("IMG_7454.MOV", 0.0, 1.2, 0.55, 1.0, 0.75),
        ("IMG_7227.MOV", 0.0, 3.9, 0.32, 0.0, 0.0),
        ("IMG_7243.MOV", 0.2, 1.1, 0.35, 0.75, 1.0),
        ("IMG_7453.MOV", 7.8, 1.5, 0.30, 0.3, 0.0),
        ("IMG_7238.MOV", 1.5, 4.8, 0.30, 0.5, 1.0),
    ],
    "mesa_de_verdade_11_mesa": [
        ("IMG_7115.MOV", 0.3, 4.0, 1.00, 0.5, 0.5),
        ("IMG_7704.MOV", 4.3, 3.0, 0.40, 0.5, 1.0),
        ("IMG_7118.MOV", 0.3, 4.0, 1.00, 0.5, 0.5),
        ("IMG_7359.MOV", 6.0, 2.3, 0.70, 0.5, 1.0),
        ("IMG_7700.MOV", 4.3, 0.7, 0.40, 0.5, 1.0),
        ("IMG_7442.MOV", 4.3, 1.0, 1.00, 0.5, 0.5),
    ],
}

if __name__ == "__main__":
    for nome, takes in LOTE.items():
        total = round(sum(t[2] for t in takes), 2)
        assert total == 15.0, (nome, total)
    crus.VIDEOS = LOTE
    crus.main(*sys.argv[1:3])
