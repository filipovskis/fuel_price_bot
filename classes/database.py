import sqlite3

from telegram import Chat
from telegram.constants import ChatType
from classes.fuel_station import FuelStation

class Database:
    def __init__(self):
        self.connection = sqlite3.connect("storage.db")
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        with self.connection:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER UNIQUE NOT NULL,
                    is_private BOOLEAN NOT NULL,
                    username VARCHAR(255),
                    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY,
                    company VARCHAR(255) NOT NULL,
                    fuel_type VARCHAR(255) NOT NULL,
                    price REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(company, fuel_type)
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_changes (
                    id INTEGER PRIMARY KEY,
                    company VARCHAR(255) NOT NULL,
                    fuel_type VARCHAR(255) NOT NULL,
                    old_price REAL NOT NULL,
                    new_price REAL NOT NULL,
                    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def is_subscribed(self, chat: Chat) -> bool:
        self.cursor.execute("SELECT 1 FROM subscribers WHERE chat_id = ?", (chat.id,))
        return self.cursor.fetchone() is not None

    def add_subscriber(self, chat: Chat):
        is_private = chat.type == ChatType.PRIVATE
        with self.connection:
            self.cursor.execute("""
                INSERT OR IGNORE INTO subscribers (chat_id, is_private, username)
                VALUES (?, ?, ?)
            """, (chat.id, is_private, chat.username))

    def remove_subscriber(self, chat: Chat):
        with self.connection:
            self.cursor.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat.id,))

    def get_subscribers(self):
        self.cursor.execute("SELECT chat_id FROM subscribers")
        return self.cursor.fetchall()

    def get_price(self, station: FuelStation, fuel_type: str):
        self.cursor.execute("""
            SELECT price FROM prices
            WHERE company = ? AND fuel_type = ?
        """, (station.name, fuel_type))

        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_prices(self):
        self.cursor.execute("SELECT company, fuel_type, price FROM prices")
        return self.cursor.fetchall()
    
    def update_price(self, station: FuelStation, fuel_type: str, price: float):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO prices (company, fuel_type, price)
                VALUES (?, ?, ?)
                ON CONFLICT(company, fuel_type) DO UPDATE SET
                    price = excluded.price,
                    updated_at = CURRENT_TIMESTAMP
            """, (station.name, fuel_type, price))

    def get_price_changes(self):
        self.cursor.execute("""
            SELECT 
                company, 
                fuel_type, 
                old_price, 
                new_price, 
                strftime('%d.%m.%Y',change_date) as date, 
                CAST(strftime('%s', change_date) AS INTEGER) as timestamp
            FROM price_changes
            GROUP BY company, fuel_type, DATE(change_date)
            ORDER BY change_date DESC
            LIMIT 100
        """)
        return self.cursor.fetchall()

    def insert_price_change(self, station: FuelStation, fuel_type: str, old_price: float, new_price: float):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO price_changes (company, fuel_type, old_price, new_price)
                VALUES (?, ?, ?, ?)
            """, (station.name, fuel_type, old_price, new_price))