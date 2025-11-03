#!/usr/bin/env python3
# winzone_bot_manualpix.py
# WinZoneVipBot3 — versão final e estável para Render

import os
import logging
import sqlite3
import threading
import asyncio
from datetime import datetime, timedelta, date
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler
import holidays

# ----------------------------
# CONFIGURAÇÕES
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003260125225"))
OWNER_ID = int(os.getenv("OWNER_ID", "1722782714"))
PIX_KEY = os.getenv("PIX_KEY", "e016b584-d2c3-4852-a752-eab63add11a7")
DB_PATH = "database.db"
BR_HOLIDAYS = holidays.Brazil(years=datetime.now().year)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ----------------------------
# BANCO DE DADOS
# ----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assinantes (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            username TEXT,
            nome TEXT,
            data_ativacao TEXT,
            data_expiracao TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            valor REAL,
            data TEXT,
            comprovante TEXT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            conteudo TEXT
        )
    """)
    conn.commit()
    return conn

# ----------------------------
# FUNÇÕES DE APOIO
# ----------------------------
def registrar_assinante(conn, user_id, username, nome):
    hoje = datetime.now()
    expiracao = hoje + timedelta(days=30)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO assinantes (user_id, username, nome, data_ativacao, data_expiracao)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, nome, hoje.isoformat(), expiracao.isoformat()))
    conn.commit()

# ----------------------------
# AGENDADOR
# ----------------------------
scheduler = BackgroundScheduler()

def iniciar_scheduler():
    """Evita erro 'SchedulerAlreadyRunningError'."""
    if not scheduler.running:
        scheduler.start()
        logging.info("✅ Scheduler iniciado com sucesso.")
    else:
        logging.info("⚙️ Scheduler já estava em execução, ignorando novo start().")

# ----------------------------
# HANDLERS DO BOT
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "💹 *Bem-vindo à WinZone | Sala de Sinais VIP 🚀*\n\n"
        "Para acessar nossas listas exclusivas, realize a assinatura mensal de *R$30,00*.\n\n"
        "💰 *Pagamento via Pix*\n"
        f"Chave aleatória:\n`{PIX_KEY}`\n\n"
        "Após o pagamento, envie o comprovante aqui (imagem ou PDF).\n"
        "Assim que confirmado, você receberá o link da Sala VIP.\n\n"
        "⚠️ O acesso é válido por 30 dias.\n"
        "Disciplina e consistência constroem resultados 💪"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Acesso negado.")
        return
    conn = context.bot_data["db"]
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM assinantes")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM assinantes WHERE DATE(data_expiracao) <= DATE('now', '+3 day')")
    vencendo = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM assinantes WHERE DATE(data_expiracao) < DATE('now')")
    expirados = cur.fetchone()[0]
    receita = total * 30
    msg = (
        "📋 *Painel WinZone*\n\n"
        f"👥 Assinantes ativos: {total}\n"
        f"⏳ Vencendo em até 3 dias: {vencendo}\n"
        f"🚫 Expirados: {expirados}\n"
        f"💸 Receita mensal estimada: R${receita},00\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.message.photo or update.message.document):
        await update.message.reply_text("Envie uma foto ou PDF do comprovante.")
        return
    user = update.effective_user
    conn = context.bot_data["db"]
    cur = conn.cursor()
    cur.execute("INSERT INTO pagamentos (user_id, valor, data, comprovante, status) VALUES (?, ?, ?, ?, ?)",
                (user.id, 30.0, datetime.now().isoformat(), "comprovante_enviado", "PENDENTE"))
    conn.commit()
    await update.message.reply_text("✅ Comprovante recebido. Aguarde confirmação do administrador.")

async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Acesso negado.")
        return
    if not context.args:
        await update.message.reply_text("Use: /confirm <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except:
        await update.message.reply_text("ID inválido.")
        return
    conn = context.bot_data["db"]
    cur = conn.cursor()
    cur.execute("SELECT * FROM pagamentos WHERE user_id = ? AND status = 'PENDENTE'", (user_id,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text("Nenhum pagamento pendente para esse usuário.")
        return
    cur.execute("UPDATE pagamentos SET status = 'CONFIRMADO' WHERE user_id = ?", (user_id,))
    conn.commit()
    registrar_assinante(conn, user_id, "", "")
    await update.message.reply_text(f"✅ Pagamento confirmado e acesso liberado para {user_id}.")

# ----------------------------
# BOT PRINCIPAL
# ----------------------------
async def iniciar_bot():
    print("🚀 Iniciando WinZoneVipBot3...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conn = init_db()
    app.bot_data["db"] = conn

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("painel", painel))
    app.add_handler(CommandHandler("confirm", confirmar_pagamento))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_comprovante))

    iniciar_scheduler()  # garante que só será iniciado 1 vez

    print("✅ Bot rodando e aguardando comandos...")
    await app.run_polling(stop_signals=None, close_loop=False)

# ----------------------------
# FLASK KEEP-ALIVE (Render)
# ----------------------------
def iniciar_flask():
    app_web = Flask(__name__)

    @app_web.route('/')
    def home():
        return "✅ WinZoneVipBot3 ativo e rodando!"

    port = int(os.getenv("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# ----------------------------
# EXECUÇÃO FINAL
# ----------------------------
if __name__ == "__main__":
    threading.Thread(target=iniciar_flask, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(iniciar_bot())
