from pathlib import Path
from typing import List
from uuid import uuid4
import base64

from werkzeug.datastructures import FileStorage

from config import DATASET_DIR
from database import get_connection


def criar_usuario(nome: str, matricula: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO usuarios (nome, matricula, pasta_dataset)
            VALUES (?, ?, '')
            """,
            (nome.strip(), matricula.strip()),
        )
        usuario_id = cur.lastrowid
        pasta = DATASET_DIR / f"usuario_{usuario_id:03d}"
        pasta.mkdir(parents=True, exist_ok=True)
        conn.execute(
            "UPDATE usuarios SET pasta_dataset = ? WHERE id = ?",
            (str(pasta), usuario_id),
        )
    return int(usuario_id)


def salvar_fotos_usuario(usuario_id: int, arquivos: List[FileStorage]) -> int:
    pasta = DATASET_DIR / f"usuario_{usuario_id:03d}"
    pasta.mkdir(parents=True, exist_ok=True)
    permitidos = {".jpg", ".jpeg", ".png"}
    salvas = 0

    for arquivo in arquivos:
        if not arquivo or not arquivo.filename:
            continue
        ext = Path(arquivo.filename).suffix.lower()
        if ext not in permitidos:
            continue

        nome_arquivo = f"{uuid4().hex}{ext}"
        destino = pasta / nome_arquivo
        arquivo.save(destino)
        salvas += 1

    return salvas


def salvar_fotos_base64_usuario(usuario_id: int, fotos_base64: List[str]) -> int:
    pasta = DATASET_DIR / f"usuario_{usuario_id:03d}"
    pasta.mkdir(parents=True, exist_ok=True)
    salvas = 0

    for foto_str in fotos_base64:
        if not foto_str:
            continue
        if "," in foto_str:
            _, foto_str = foto_str.split(",", 1)
        try:
            raw = base64.b64decode(foto_str, validate=True)
        except Exception:
            continue

        nome_arquivo = f"{uuid4().hex}.jpg"
        destino = pasta / nome_arquivo
        destino.write_bytes(raw)
        salvas += 1

    return salvas


def listar_usuarios():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                id,
                nome,
                matricula,
                pasta_dataset,
                criado_em
            FROM usuarios
            ORDER BY id DESC
            """
        ).fetchall()
