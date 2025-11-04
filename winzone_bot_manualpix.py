import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- LOGS ---
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- CONFIG ---
BOT_TOKEN = "COLE_SEU_TOKEN_AQUI"
OWNER_ID = 1722782714

# --- COMANDOS BÁSICOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 WinZoneVipBot3 está ativo e rodando no Render!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos disponíveis:\n/start - Inicia o bot\n/help - Mostra esta mensagem")

# --- AGENDADOR ---
scheduler = BackgroundScheduler()

def tarefa_periodica():
    logging.info("⏰ Executando tarefa periódica de teste...")

def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(tarefa_periodica, "interval", minutes=1)
        scheduler.start()
        logging.info("✅ Scheduler iniciado com sucesso.")

# --- LOOP PRINCIPAL ---
async def main():
    logging.info("🚀 Iniciando WinZoneVipBot3...")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    iniciar_scheduler()
    logging.info("✅ Bot rodando e aguardando comandos...")

    # Mantém o bot vivo para sempre no Render
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(60)

# --- EXECUÇÃO ---
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.warning("🛑 Bot encerrado manualmente.")
    finally:
        loop.close()
