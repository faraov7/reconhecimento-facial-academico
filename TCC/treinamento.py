import pickle
from pathlib import Path
from typing import Dict, List

import cv2
import face_recognition
import numpy as np

from config import DATASET_DIR, EMBEDDINGS_PATH
from database import get_connection
from detector_face import DetectorFace


def _listar_imagens_da_pasta(pasta: Path):
    extensoes = {".jpg", ".jpeg", ".png"}
    for arquivo in pasta.glob("*"):
        if arquivo.suffix.lower() in extensoes:
            yield arquivo


def treinar_todos_usuarios() -> Dict[str, int]:
    detector = DetectorFace()
    embeddings: List[np.ndarray] = []
    labels: List[int] = []
    nomes: Dict[str, str] = {}
    total_imagens = 0
    total_faces = 0

    with get_connection() as conn:
        usuarios = conn.execute("SELECT id, nome, pasta_dataset FROM usuarios").fetchall()

    for usuario in usuarios:
        usuario_id = int(usuario["id"])
        nomes[str(usuario_id)] = usuario["nome"]
        pasta = Path(usuario["pasta_dataset"])

        if not pasta.exists():
            continue

        for img_path in _listar_imagens_da_pasta(pasta):
            total_imagens += 1
            img_bgr = cv2.imread(str(img_path))
            if img_bgr is None:
                continue

            faces = detector.detect_faces(img_bgr)
            if not faces:
                continue

            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            top, right, bottom, left = y, x + w, y + h, x
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(img_rgb, [(top, right, bottom, left)])
            if not encs:
                continue

            embeddings.append(encs[0].astype(np.float32))
            labels.append(usuario_id)
            total_faces += 1

    payload = {
        "embeddings": embeddings,
        "labels": labels,
        "names": nomes,
    }

    with EMBEDDINGS_PATH.open("wb") as f:
        pickle.dump(payload, f)

    return {
        "usuarios": len(usuarios),
        "imagens_lidas": total_imagens,
        "embeddings_gerados": total_faces,
    }
