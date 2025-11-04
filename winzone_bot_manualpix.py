import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

# --- Variáveis de configuração ---
BOT_TOKEN = "SEU_TOKEN_AQUI"  # troque pelo seu
OWNER_ID = 1722782714

# --- Funções do bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot ativo e rodando perfeitamente no Render!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos disponíveis:\n/start - Inicia o bot\n/help - Mostra ajuda")

# --- Scheduler (agendador de tarefas) ---
scheduler = AsyncIOScheduler()

def exemplo_de_tarefa():
    logging.info("⏰ Executando tarefa agendada automaticamente!")

def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(exemplo_de_tarefa, "interval", minutes=1)
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

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # Mantém o bot ativo
    await asyncio.Event().wait()

# --- Execução ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Se o Render já estiver com um loop ativo, usa esse loop
        if "already running" in str(e).lower():
            logging.warning("⚠️ Loop já em execução — ajustando para modo compatível com Render.")
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise


