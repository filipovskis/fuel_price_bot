from telegram_bot import init_bot
from data_collector import run_collector

DATA_FETCH_INTERVAL = 5

if __name__ == "__main__":
    application = init_bot()

    job_queue = application.job_queue
    job_queue.run_repeating(run_collector, interval=DATA_FETCH_INTERVAL, first=1)

    application.run_polling()   