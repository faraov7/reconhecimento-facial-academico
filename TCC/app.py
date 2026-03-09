import json
import csv
from io import BytesIO, StringIO
from datetime import datetime

import cv2
from flask import Flask, Response, flash, redirect, render_template, request, send_file, url_for
from sqlite3 import IntegrityError

from cadastro import (
    criar_usuario,
    listar_usuarios,
    salvar_fotos_base64_usuario,
    salvar_fotos_usuario,
)
from camera import CameraManager
from config import ensure_directories
from database import init_db
from logs import listar_acessos, listar_presencas, obter_metricas
from presenca import (
    criar_turma,
    listar_ids_usuarios_turma,
    listar_turmas,
    listar_vinculos_turma,
    obter_turma,
    vincular_usuarios_na_turma,
)
from reconhecimento import ReconhecedorFacial
from treinamento import treinar_todos_usuarios
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


app = Flask(__name__)
app.config["SECRET_KEY"] = "tcc-reconhecimento-facial-secret"

camera_manager = CameraManager(camera_index=0)
reconhecedor = ReconhecedorFacial()


def setup() -> None:
    ensure_directories()
    init_db()


setup()


def gerar_stream_video(turma_id: int | None = None):
    allowed_ids = listar_ids_usuarios_turma(turma_id) if turma_id else None
    while True:
        ok, frame = camera_manager.read()
        if not ok or frame is None:
            continue

        frame, _ = reconhecedor.reconhecer_frame(
            frame,
            turma_id=turma_id,
            allowed_user_ids=allowed_ids,
        )
        ok_jpg, buffer = cv2.imencode(".jpg", frame)
        if not ok_jpg:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )


def gerar_stream_captura():
    while True:
        ok, frame = camera_manager.read()
        if not ok or frame is None:
            continue
        ok_jpg, buffer = cv2.imencode(".jpg", frame)
        if not ok_jpg:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )


@app.route("/")
def index():
    metricas = obter_metricas()
    return render_template("index.html", metricas=metricas)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        matricula = request.form.get("matricula", "").strip()
        fotos = request.files.getlist("fotos")
        capturas_json = request.form.get("capturas_json", "[]")
        capturas = []
        try:
            capturas = json.loads(capturas_json) if capturas_json else []
        except json.JSONDecodeError:
            capturas = []

        if not nome or not matricula:
            flash("Nome e matricula sao obrigatorios.", "warning")
            return redirect(url_for("cadastro"))

        if not fotos and not capturas:
            flash("Envie ao menos uma foto ou use a captura automatica.", "warning")
            return redirect(url_for("cadastro"))

        try:
            usuario_id = criar_usuario(nome, matricula)
            qtd_upload = salvar_fotos_usuario(usuario_id, fotos)
            qtd_capturas = salvar_fotos_base64_usuario(usuario_id, capturas)
            qtd = qtd_upload + qtd_capturas
            if qtd == 0:
                flash("Nenhuma imagem valida foi enviada (use JPG/JPEG/PNG).", "danger")
                return redirect(url_for("cadastro"))

            resumo = treinar_todos_usuarios()
            reconhecedor.load_embeddings()
            flash(
                (
                    f"Usuario cadastrado com sucesso. {qtd} foto(s) salva(s). "
                    f"Embeddings gerados: {resumo['embeddings_gerados']}."
                ),
                "success",
            )
            return redirect(url_for("cadastro"))
        except IntegrityError:
            flash("A matricula informada ja existe. Use outra matricula.", "danger")
            return redirect(url_for("cadastro"))

    usuarios = listar_usuarios()
    return render_template("cadastro.html", usuarios=usuarios)


@app.route("/treinar", methods=["POST"])
def treinar():
    resumo = treinar_todos_usuarios()
    reconhecedor.load_embeddings()
    flash(
        (
            "Treinamento concluido. "
            f"Usuarios: {resumo['usuarios']} | "
            f"Imagens lidas: {resumo['imagens_lidas']} | "
            f"Embeddings: {resumo['embeddings_gerados']}"
        ),
        "success",
    )
    return redirect(url_for("cadastro"))


@app.route("/reconhecimento")
def reconhecimento():
    turma_id_raw = request.args.get("turma_id", "").strip()
    turma = None
    turma_id = None
    if turma_id_raw.isdigit():
        turma_id = int(turma_id_raw)
        turma = obter_turma(turma_id)
    return render_template("reconhecimento.html", turma=turma, turma_id=turma_id)


@app.route("/video_feed")
def video_feed():
    camera_manager.start()
    turma_id_raw = request.args.get("turma_id", "").strip()
    turma_id = int(turma_id_raw) if turma_id_raw.isdigit() else None
    return Response(
        gerar_stream_video(turma_id=turma_id),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/video_feed_cadastro")
def video_feed_cadastro():
    camera_manager.start()
    return Response(
        gerar_stream_captura(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/presencas", methods=["GET", "POST"])
def presencas():
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "criar_turma":
            nome = request.form.get("nome_turma", "").strip()
            disciplina = request.form.get("disciplina", "").strip()
            periodo = request.form.get("periodo", "").strip()
            if not nome or not disciplina:
                flash("Informe nome da turma e disciplina.", "warning")
                return redirect(url_for("presencas"))
            turma_id = criar_turma(nome, disciplina, periodo)
            flash("Turma criada com sucesso.", "success")
            return redirect(url_for("presencas", turma_id=turma_id))

        if action == "vincular_turma":
            turma_id_raw = request.form.get("turma_id", "").strip()
            if not turma_id_raw.isdigit():
                flash("Turma invalida para vinculo.", "danger")
                return redirect(url_for("presencas"))
            turma_id = int(turma_id_raw)
            usuarios_ids = [int(x) for x in request.form.getlist("usuarios_ids") if x.isdigit()]
            vincular_usuarios_na_turma(turma_id, usuarios_ids)
            flash("Vinculos atualizados com sucesso.", "success")
            return redirect(url_for("presencas", turma_id=turma_id))

    turma_id_raw = request.args.get("turma_id", "").strip()
    turma_id = int(turma_id_raw) if turma_id_raw.isdigit() else None
    turma_selecionada = obter_turma(turma_id) if turma_id else None
    vinculados = listar_vinculos_turma(turma_id) if turma_id else []
    vinculados_ids = {int(u["id"]) for u in vinculados}

    return render_template(
        "presencas.html",
        turmas=listar_turmas(),
        usuarios=listar_usuarios(),
        turma_selecionada=turma_selecionada,
        vinculados=vinculados,
        vinculados_ids=vinculados_ids,
    )


@app.route("/historico")
def historico():
    acessos = listar_acessos(limit=300)
    return render_template("historico.html", acessos=acessos)


@app.route("/relatorios")
def relatorios():
    metricas = obter_metricas()
    presencas = listar_presencas(limit=500)
    labels = [item["dia"] for item in metricas["por_dia"]]
    dados_reconhecido = [item["reconhecido"] for item in metricas["por_dia"]]
    dados_desconhecido = [item["desconhecido"] for item in metricas["por_dia"]]
    return render_template(
        "relatorios.html",
        metricas=metricas,
        presencas=presencas,
        labels_json=json.dumps(labels),
        reconhecido_json=json.dumps(dados_reconhecido),
        desconhecido_json=json.dumps(dados_desconhecido),
        agora=datetime.now(),
    )


@app.route("/export/csv")
def exportar_csv():
    presencas = listar_presencas(limit=5000)
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["ID", "Data", "Status", "Nome", "Matricula", "Turma", "Disciplina"])
    for item in presencas:
        writer.writerow(
            [
                item["id"],
                item["data"],
                item["status"],
                item["nome"],
                item["matricula"],
                item["turma_nome"],
                item["disciplina"],
            ]
        )

    payload = BytesIO(buffer.getvalue().encode("utf-8-sig"))
    payload.seek(0)
    data_tag = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"relatorio_presencas_{data_tag}.csv",
    )


@app.route("/export/pdf")
def exportar_pdf():
    presencas = listar_presencas(limit=2500)
    data_tag = datetime.now().strftime("%Y%m%d_%H%M")
    payload = BytesIO()
    c = canvas.Canvas(payload, pagesize=A4)
    largura, altura = A4
    margem = 15 * mm
    y = altura - margem

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margem, y, "Relatorio de Presencas - FaceID Academico")
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(margem, y, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.setFillColor(colors.black)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margem, y, "Data")
    c.drawString(margem + 24 * mm, y, "Nome")
    c.drawString(margem + 90 * mm, y, "Matricula")
    c.drawString(margem + 120 * mm, y, "Turma")
    c.drawString(margem + 165 * mm, y, "Status")
    y -= 4 * mm
    c.line(margem, y, largura - margem, y)
    y -= 5 * mm
    c.setFont("Helvetica", 8)

    for item in presencas:
        if y < margem + 10 * mm:
            c.showPage()
            y = altura - margem
            c.setFont("Helvetica", 8)
        c.drawString(margem, y, str(item["data"])[:10])
        c.drawString(margem + 24 * mm, y, str(item["nome"])[:30])
        c.drawString(margem + 90 * mm, y, str(item["matricula"])[:14])
        c.drawString(margem + 120 * mm, y, str(item["turma_nome"])[:20])
        c.drawString(margem + 165 * mm, y, str(item["status"])[:12])
        y -= 5 * mm

    c.save()
    payload.seek(0)
    return send_file(
        payload,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"relatorio_presencas_{data_tag}.pdf",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
