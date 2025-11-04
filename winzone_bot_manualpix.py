import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuração de logs ---
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Lendo variáveis do ambiente ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
PIX_KEY = os.getenv("PIX_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN não encontrado nas variáveis de ambiente!")
if not OWNER_ID:
    raise ValueError("❌ OWNER_ID não encontrado nas variáveis de ambiente!")

# --- Comandos básicos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 WinZoneVipBot3 está ativo e rodando no Render!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos disponíveis:\n/start - Inicia o bot\n/help - Mostra esta mensagem")

# --- Agendador de tarefas ---
scheduler = BackgroundScheduler()

def tarefa_periodica():
    logging.info("⏰ Executando tarefa periódica de teste...")

def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(tarefa_periodica, "interval", minutes=1)
        scheduler.start()
        logging.info("✅ Scheduler iniciado com sucesso.")

# --- Função principal ---
async def main():
    logging.info("🚀 Iniciando WinZoneVipBot3...")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    iniciar_scheduler()
    logging.info("✅ Bot rodando e aguardando comandos...")

    # Mantém o bot ativo continuamente
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(60)

# --- Execução ---
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.warning("🛑 Bot encerrado manualmente.")
    finally:
        loop.close()
