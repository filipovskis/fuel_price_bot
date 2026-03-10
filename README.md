# fuel_price_bot ⛽

Simple Telegram bot to track fuel prices across Latvia. It scrapes data from the 4 main suppliers: Neste, Circle K, Viada, and Virši.
I built this to keep an eye on things when fuel prices started to increase due to global events.

**What it does:**
- Tracks prices - constant monitoring of the fuel station websites.
- Notifications - subscribe and get a message the moment prices change.
- History - saves all price changes so you can see them afterwards.
- Comparison - quickly shows all prices and what station has the cheapest fuel right now.

### Extensibility
You can easily modify the scrapers or add new ones to support other fuel chains or different countries entirely.

## Demo
The bot is live and running here: [@fuelwatchlv_bot](https://t.me/fuelwatchlv_bot)

<img width="457" height="219" alt="image" src="https://github.com/user-attachments/assets/d8d7ead2-a7a1-4b38-89e6-528977b7e998" />
<img width="456" height="766" alt="image" src="https://github.com/user-attachments/assets/c4d8e1c1-7cdf-458c-8b33-b81058013b0d" />


## Quick Start
1. Install dependencies
2. Paste your bot's token into `config/telegram_token.txt`
3. Run main.py
