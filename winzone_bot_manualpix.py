#!/usr/bin/env python3
# WinZoneVipBot3 — versão estável e compatível com Render (sem Flask)

import os
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configurações
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1722782714"))
PIX_KEY = os.getenv("PIX_KEY", "e016b584-d2c3-4852-a752-eab63add11a7")
DB_PATH = "database.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Banco de Dados
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assinantes (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            nome TEXT,
            data_ativacao TEXT,
            data_expiracao TEXT
        )
    """)
    conn.commit()
    return conn

# Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💹 *Bem-vindo à WinZone | Sala de Sinais VIP 🚀*\n\n"
        "Para acessar nossas listas exclusivas, realize a assinatura mensal de *R$30,00*.\n\n"
        f"💰 *Chave Pix:* `{PIX_KEY}`\n\n"
        "Após o pagamento, envie o comprovante (imagem ou PDF) aqui mesmo.\n"
        "Assim que confirmado, seu acesso será liberado por 30 dias."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.message.photo or update.message.document):
        await update.message.reply_text("Envie o comprovante em imagem ou PDF.")
        return

    user = update.effective_user
    conn = context.bot_data["db"]
    cur = conn.cursor()

    ativacao = datetime.now()
    expiracao = ativacao + timedelta(days=30)

    cur.execute("""
        INSERT OR REPLACE INTO assinantes (user_id, nome, data_ativacao, data_expiracao)
        VALUES (?, ?, ?, ?)
    """, (user.id, user.full_name, ativacao.isoformat(), expiracao.isoformat()))
    conn.commit()

    await update.message.reply_text(
        f"✅ Pagamento confirmado!\nSeu acesso expira em *{expiracao.strftime('%d/%m/%Y')}*.",
        parse_mode="Markdown"
    )

async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Acesso negado.")
        return

    conn = context.bot_data["db"]
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM assinantes")
    total = cur.fetchone()[0]
    receita = total * 30

    msg = (
        "📊 *Painel WinZone*\n\n"
        f"👥 Assinantes ativos: {total}\n"
        f"💸 Receita estimada: R${receita},00"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Execução
async def main():
    print("🚀 Iniciando WinZoneVipBot3...")
    conn = init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data["db"] = conn

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("painel", painel))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_comprovante))

    scheduler = AsyncIOScheduler()
    scheduler.start()

    print("✅ Bot rodando e aguardando comandos...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
