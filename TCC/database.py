import sqlite3
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                matricula TEXT NOT NULL UNIQUE,
                pasta_dataset TEXT NOT NULL,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS acessos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                turma_id INTEGER,
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('RECONHECIDO', 'DESCONHECIDO')),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(turma_id) REFERENCES turmas(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS turmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                disciplina TEXT NOT NULL,
                periodo TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuario_turmas (
                usuario_id INTEGER NOT NULL,
                turma_id INTEGER NOT NULL,
                PRIMARY KEY (usuario_id, turma_id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(turma_id) REFERENCES turmas(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS presencas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                turma_id INTEGER NOT NULL,
                data DATE NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PRESENTE', 'AUSENTE')),
                acesso_id INTEGER,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(turma_id) REFERENCES turmas(id),
                FOREIGN KEY(acesso_id) REFERENCES acessos(id),
                UNIQUE(usuario_id, turma_id, data)
            )
            """
        )

        cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(acessos)").fetchall()
        }
        if "turma_id" not in cols:
            conn.execute("ALTER TABLE acessos ADD COLUMN turma_id INTEGER")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_acessos_data_hora ON acessos(data_hora DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_acessos_usuario ON acessos(usuario_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_acessos_turma ON acessos(turma_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_presencas_data ON presencas(data DESC)"
        )
