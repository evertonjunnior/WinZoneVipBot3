#!/usr/bin/env python3
# winzone_bot_manualpix.py
# WinZoneVipBot3 - versão para Render (com servidor Flask embutido)

import os
import logging
import sqlite3
from datetime import datetime, timedelta, date
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from utils.messages import MOTIVATIONAL_MESSAGES, CLOSING_MESSAGE, NIGHT_PRELIST_MESSAGE
from apscheduler.schedulers.background import BackgroundScheduler
import holidays

# ----------------------------
# CONFIG
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
# DB
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
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
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
# Helpers de meta
# ----------------------------
def marcar_lista_postada(conn):
    hoje = datetime.now().date().isoformat()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (f"lista_{hoje}", "1"))
    conn.commit()

def lista_postada_hoje(conn):
    hoje = datetime.now().date().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key = ?", (f"lista_{hoje}",))
    row = cur.fetchone()
    return bool(row and row[0] == "1")

# ----------------------------
# Assinantes
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

def is_assinante_ativo(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT data_expiracao FROM assinantes WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        return False
    data_exp = datetime.fromisoformat(row[0])
    return data_exp > datetime.now()

# ----------------------------
# Scheduler (mensagens automáticas)
# ----------------------------
scheduler = BackgroundScheduler()

def is_business_day(d: date):
    if d.weekday() >= 5:
        return False
    return d not in BR_HOLIDAYS

async def send_channel_text(app, text):
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        logging.error("Erro ao enviar mensagem ao canal: %s", e)

def job_end_of_list(app_context):
    app = app_context['app']
    conn = app_context['db']
    if not lista_postada_hoje(conn):
        return
    app.create_task(send_channel_text(app, CLOSING_MESSAGE))

def job_night_prelist(app_context):
    app = app_context['app']
    today = datetime.now().date()
    if not is_business_day(today):
        return
    app.create_task(send_channel_text(app, NIGHT_PRELIST_MESSAGE))

def start_scheduler(app, conn):
    ctx = {'app': app, 'db': conn}
    scheduler.add_job(job_end_of_list, 'cron', hour=16, minute=5, args=[ctx])
    scheduler.add_job(job_night_prelist, 'cron', hour=22, minute=45, args=[ctx])
    motivational_times = [(6,0), (8,0), (12,0), (16,0), (18,0), (21,0), (22,0)]
    for h,m in motivational_times:
        def make_job(msg):
            def job(app_context):
                app = app_context['app']
                today = datetime.now().date()
                if not is_business_day(today):
                    return
                app.create_task(send_channel_text(app, msg))
            return job
        for idx, msg in enumerate(MOTIVATIONAL_MESSAGES):
            scheduler.add_job(make_job(MOTIVATIONAL_MESSAGES[idx % len(MOTIVATIONAL_MESSAGES)]),
                              'cron', hour=h, minute=m, args=[{'app': app, 'db': conn}])
    scheduler.start()

# ----------------------------
# Handlers do bot
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    texto = (
        f"💹 *Bem-vindo à WinZone | Sala de Sinais VIP 🚀*\n\n"
        f"Para acessar nossas listas exclusivas, realize a assinatura mensal de *R$30,00*.\n\n"
        f"💰 *Pagamento via Pix*\n"
        f"Chave aleatória:\n`{PIX_KEY}`\n\n"
        f"Após o pagamento, envie aqui o *comprovante Pix (imagem ou PDF)*.\n"
        f"Assim que for confirmado, você receberá o link da Sala VIP.\n\n"
        f"⚠️ O acesso é válido por 30 dias.\n"
        f"Disciplina e consistência constroem resultados 💪"
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
    cur.execute("""
        SELECT COUNT(*) FROM assinantes
        WHERE DATE(data_expiracao) <= DATE('now', '+3 day')
    """)
    vencendo = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM assinantes
        WHERE DATE(data_expiracao) < DATE('now')
    """)
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

async def lista_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("Apenas o administrador pode enviar listas.")
        return
    if not update.message.text:
        await update.message.reply_text("Cole a lista no corpo da mensagem (uma linha por sinal).")
        return
    raw = update.message.text.strip()
    linhas = [l.strip() for l in raw.splitlines() if l.strip()]
    tf = "M15"
    if linhas and ";" in linhas[0]:
        try:
            tf = linhas[0].split(";")[0].strip()
        except:
            tf = "M15"
    header = f"━━━━━━━━━━━━━━━\n💹 *Lista de Sinais WinZone - {tf}*\n\n"
    body = ""
    for linha in linhas:
        if ";" in linha:
            parts = linha.split(";")
            if len(parts) >= 4:
                _, par, hora, direcao = parts[:4]
                body += f"📊 {par} - {hora} - {direcao}\n"
    rodape = (
        "\n━━━━━━━━━━━━━━━\n"
        "⚠️ *Orientação WinZone:*\n"
        "Os sinais são válidos até *Gale 2 (G2)*.\n"
        "🎯 Siga um gerenciamento firme — *2x0 e fora do mercado!*\n"
        "Nada de ganância. Consistência vence impulso.\n\n"
        "📅 As listas são postadas até as 23:00 e devem ser usadas no dia seguinte.\n"
        "📈 Operamos somente em mercado aberto — nada de OTC.\n"
        "🕒 As listas contêm sinais entre 00:00 e 16:00 (somente os horários mais assertivos).\n"
        "━━━━━━━━━━━━━━━\n"
        "💹 *WinZone | Sala de Sinais VIP 🚀*"
    )
    mensagem_preview = header + body + rodape
    context.user_data["preview"] = mensagem_preview
    await update.message.reply_text("🔎 Prévia da lista gerada. Responda com 'sim' para publicar ou 'não' para cancelar.")
    await update.message.reply_text(mensagem_preview, parse_mode="Markdown")

async def resposta_publicacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if "preview" not in context.user_data:
        return
    texto = update.message.text.lower().strip()
    conn = context.bot_data["db"]
    if texto == "sim":
        msg_final = context.user_data["preview"]
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg_final, parse_mode="Markdown")
        marcar_lista_postada(conn)
        cur = conn.cursor()
        cur.execute("INSERT INTO listas (data, conteudo) VALUES (?, ?)", (datetime.now().isoformat(), msg_final))
        conn.commit()
        await update.message.reply_text("✅ Lista publicada no canal com sucesso!")
        context.user_data.pop("preview")
    elif texto == "não":
        await update.message.reply_text("❌ Publicação cancelada.")
        context.user_data.pop("preview")

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

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot online. WinZoneVipBot ativo.")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "/start - Instruções de assinatura\n"
        "/lista - Enviar lista (admin)\n"
        "/painel - Painel administrativo (admin)\n"
        "/status - Verificar status do bot\n"
        "/ajuda - Esta ajuda\n"
        "/confirm <user_id> - Confirmar pagamento (admin)\n"
    )
    await update.message.reply_text(texto)

# ----------------------------
# MAIN
# ----------------------------
async def main():
    print("🚀 Iniciando WinZoneVipBot3...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conn = init_db()
    app.bot_data["db"] = conn

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("painel", painel))
    app.add_handler(CommandHandler("lista", lista_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("confirm", confirmar_pagamento))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_comprovante))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, resposta_publicacao))

    start_scheduler(app, conn)
    print("✅ Bot rodando. Aguardando comandos...")
    await app.run_polling()

# ----------------------------
# FLASK KEEP-ALIVE (versão corrigida e estável)
# ----------------------------
if __name__ == "__main__":
    import asyncio
    import threading
    from flask import Flask

    app_web = Flask(__name__)

    @app_web.route('/')
    def home():
        return "✅ WinZoneVipBot3 ativo e rodando!"

    def run_flask():
        port = int(os.getenv("PORT", 10000))
        app_web.run(host="0.0.0.0", port=port)

    # Executa o Flask em paralelo
    threading.Thread(target=run_flask, daemon=True).start()

    print("🚀 Iniciando WinZoneVipBot3...")

    # Executa o bot em um loop isolado
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("⚠️ Loop já em execução. Criando novo event loop...")
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(main())
        else:
            loop.run_until_complete(main())
    except RuntimeError:
        print("⚙️ Criando loop assíncrono manualmente...")
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(main())
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
