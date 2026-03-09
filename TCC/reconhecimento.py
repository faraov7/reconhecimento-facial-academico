import pickle
import time
from typing import Dict, List, Optional, Tuple

import cv2
import face_recognition
import numpy as np

from config import EMBEDDINGS_PATH
from detector_face import DetectorFace
from logs import registrar_acesso


class ReconhecedorFacial:
    def __init__(self, threshold: float = 0.53, log_interval_s: int = 7) -> None:
        self.threshold = threshold
        self.log_interval_s = log_interval_s
        self.detector = DetectorFace()
        self.embeddings = np.empty((0, 128), dtype=np.float32)
        self.labels: List[int] = []
        self.names: Dict[str, str] = {}
        self._ultima_gravacao: Dict[str, float] = {}
        self.load_embeddings()

    def load_embeddings(self) -> None:
        if not EMBEDDINGS_PATH.exists():
            self.embeddings = np.empty((0, 128), dtype=np.float32)
            self.labels = []
            self.names = {}
            return

        with EMBEDDINGS_PATH.open("rb") as f:
            data = pickle.load(f)

        emb_list = data.get("embeddings", [])
        if emb_list:
            self.embeddings = np.array(emb_list, dtype=np.float32)
        else:
            self.embeddings = np.empty((0, 128), dtype=np.float32)
        self.labels = list(data.get("labels", []))
        self.names = dict(data.get("names", {}))

    def _registrar_com_cooldown(
        self,
        usuario_id: Optional[int],
        status: str,
        turma_id: Optional[int] = None,
    ) -> None:
        chave = f"{usuario_id or 0}:{status}:{turma_id or 0}"
        agora = time.time()
        ultimo = self._ultima_gravacao.get(chave, 0.0)
        if agora - ultimo >= self.log_interval_s:
            registrar_acesso(usuario_id, status, turma_id=turma_id)
            self._ultima_gravacao[chave] = agora

    def _extrair_embedding(self, frame_bgr, box_xywh):
        x, y, w, h = box_xywh
        top, right, bottom, left = y, x + w, y + h, x
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        embeddings = face_recognition.face_encodings(frame_rgb, [(top, right, bottom, left)])
        if not embeddings:
            return None
        return embeddings[0].astype(np.float32)

    def reconhecer_frame(
        self,
        frame_bgr,
        turma_id: Optional[int] = None,
        allowed_user_ids: Optional[set[int]] = None,
    ) -> Tuple[np.ndarray, List[Dict[str, str]]]:
        resultados = []
        faces = self.detector.detect_faces(frame_bgr)

        for x, y, w, h in faces:
            nome = "Desconhecido"
            status = "DESCONHECIDO"
            usuario_id: Optional[int] = None
            cor = (0, 110, 255)

            embedding = self._extrair_embedding(frame_bgr, (x, y, w, h))

            if embedding is not None and len(self.embeddings) > 0:
                dists = np.linalg.norm(self.embeddings - embedding, axis=1)
                idx_ordenados = np.argsort(dists)
                for idx in idx_ordenados:
                    candidato_id = int(self.labels[int(idx)])
                    if allowed_user_ids and candidato_id not in allowed_user_ids:
                        continue
                    melhor_dist = float(dists[int(idx)])
                    if melhor_dist <= self.threshold:
                        usuario_id = candidato_id
                        nome = self.names.get(str(usuario_id), f"Usuario {usuario_id}")
                        status = "RECONHECIDO"
                        cor = (40, 210, 120)
                    break

            self._registrar_com_cooldown(usuario_id, status, turma_id=turma_id)
            cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), cor, 2)
            cv2.putText(
                frame_bgr,
                f"{nome} - {status}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                cor,
                2,
                cv2.LINE_AA,
            )

            resultados.append(
                {
                    "nome": nome,
                    "status": status,
                    "usuario_id": str(usuario_id or ""),
                }
            )

        return frame_bgr, resultados
