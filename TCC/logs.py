from typing import Optional

from database import get_connection


def registrar_acesso(usuario_id: Optional[int], status: str, turma_id: Optional[int] = None) -> None:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO acessos (usuario_id, turma_id, status)
            VALUES (?, ?, ?)
            """,
            (usuario_id, turma_id, status),
        )
        acesso_id = int(cur.lastrowid)

        if usuario_id and turma_id and status == "RECONHECIDO":
            conn.execute(
                """
                INSERT INTO presencas (usuario_id, turma_id, data, status, acesso_id)
                VALUES (?, ?, DATE('now', 'localtime'), 'PRESENTE', ?)
                ON CONFLICT(usuario_id, turma_id, data)
                DO NOTHING
                """,
                (usuario_id, turma_id, acesso_id),
            )


def listar_acessos(limit: int = 200):
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                a.id,
                a.data_hora,
                a.status,
                u.nome,
                u.matricula,
                t.nome AS turma_nome,
                t.disciplina
            FROM acessos a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            LEFT JOIN turmas t ON t.id = a.turma_id
            ORDER BY a.data_hora DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()


def obter_metricas():
    with get_connection() as conn:
        total_usuarios = conn.execute("SELECT COUNT(*) AS c FROM usuarios").fetchone()["c"]
        total_acessos = conn.execute("SELECT COUNT(*) AS c FROM acessos").fetchone()["c"]
        reconhecidos = conn.execute(
            "SELECT COUNT(*) AS c FROM acessos WHERE status = 'RECONHECIDO'"
        ).fetchone()["c"]
        desconhecidos = conn.execute(
            "SELECT COUNT(*) AS c FROM acessos WHERE status = 'DESCONHECIDO'"
        ).fetchone()["c"]

        por_dia = conn.execute(
            """
            SELECT
                DATE(data_hora) AS dia,
                SUM(CASE WHEN status = 'RECONHECIDO' THEN 1 ELSE 0 END) AS reconhecido,
                SUM(CASE WHEN status = 'DESCONHECIDO' THEN 1 ELSE 0 END) AS desconhecido
            FROM acessos
            GROUP BY DATE(data_hora)
            ORDER BY DATE(data_hora) DESC
            LIMIT 7
            """
        ).fetchall()

        top_usuarios = conn.execute(
            """
            SELECT
                u.nome,
                u.matricula,
                COUNT(*) AS qtd
            FROM acessos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.status = 'RECONHECIDO'
            GROUP BY a.usuario_id
            ORDER BY qtd DESC
            LIMIT 5
            """
        ).fetchall()

        return {
            "total_usuarios": total_usuarios,
            "total_acessos": total_acessos,
            "reconhecidos": reconhecidos,
            "desconhecidos": desconhecidos,
            "por_dia": [dict(row) for row in por_dia][::-1],
            "top_usuarios": [dict(row) for row in top_usuarios],
        }


def listar_presencas(limit: int = 300):
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                p.id,
                p.data,
                p.status,
                u.nome,
                u.matricula,
                t.nome AS turma_nome,
                t.disciplina
            FROM presencas p
            JOIN usuarios u ON u.id = p.usuario_id
            JOIN turmas t ON t.id = p.turma_id
            ORDER BY p.data DESC, p.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()
