from typing import Iterable

from database import get_connection


def criar_turma(nome: str, disciplina: str, periodo: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO turmas (nome, disciplina, periodo)
            VALUES (?, ?, ?)
            """,
            (nome.strip(), disciplina.strip(), periodo.strip()),
        )
        return int(cur.lastrowid)


def listar_turmas():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, nome, disciplina, periodo, criado_em
            FROM turmas
            ORDER BY id DESC
            """
        ).fetchall()


def obter_turma(turma_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, nome, disciplina, periodo FROM turmas WHERE id = ?",
            (int(turma_id),),
        ).fetchone()


def vincular_usuarios_na_turma(turma_id: int, usuarios_ids: Iterable[int]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM usuario_turmas WHERE turma_id = ?", (turma_id,))
        for usuario_id in usuarios_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO usuario_turmas (usuario_id, turma_id)
                VALUES (?, ?)
                """,
                (int(usuario_id), int(turma_id)),
            )


def listar_vinculos_turma(turma_id: int):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT u.id, u.nome, u.matricula
            FROM usuario_turmas ut
            JOIN usuarios u ON u.id = ut.usuario_id
            WHERE ut.turma_id = ?
            ORDER BY u.nome
            """,
            (turma_id,),
        ).fetchall()


def listar_ids_usuarios_turma(turma_id: int) -> set[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT usuario_id FROM usuario_turmas WHERE turma_id = ?",
            (int(turma_id),),
        ).fetchall()
    return {int(r["usuario_id"]) for r in rows}
