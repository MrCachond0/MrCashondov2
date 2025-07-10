"""
trade_database.py
Módulo para registrar señales y operaciones en una base de datos SQLite, consultar y exportar a CSV.
"""
import sqlite3
from typing import Optional, Dict, Any, List
import pandas as pd
import os
from datetime import datetime

DB_PATH = os.getenv("TRADE_DB_PATH", "trades.db")

class TradeDatabase:
    """
    Clase para gestionar el registro y consulta de señales y operaciones en SQLite.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Inicializa la base de datos y las tablas si no existen."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    signal_type TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL,
                    timestamp TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    order_id TEXT,
                    symbol TEXT,
                    action TEXT,
                    volume REAL,
                    price REAL,
                    sl REAL,
                    tp REAL,
                    comment TEXT,
                    open_time TEXT,
                    close_time TEXT,
                    close_price REAL,
                    profit REAL,
                    status TEXT,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
                )
            ''')
            conn.commit()

    def log_signal(self, signal: Dict[str, Any]) -> int:
        """
        Registra una señal en la base de datos.
        Args:
            signal: Diccionario con los datos de la señal.
        Returns:
            id de la señal registrada.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO signals (symbol, timeframe, signal_type, entry_price, stop_loss, take_profit, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal['symbol'],
                signal['timeframe'],
                signal['signal_type'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit'],
                signal['confidence'],
                signal.get('timestamp', datetime.utcnow().isoformat())
            ))
            conn.commit()
            return c.lastrowid

    def update_signal_status(self, signal_id: int, status: str) -> None:
        """Actualiza el estado de una señal."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('UPDATE signals SET status = ? WHERE id = ?', (status, signal_id))
            conn.commit()

    def log_trade(self, trade: Dict[str, Any]) -> int:
        """
        Registra una operación en la base de datos.
        Args:
            trade: Diccionario con los datos de la operación.
        Returns:
            id de la operación registrada.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO trades (signal_id, order_id, symbol, action, volume, price, sl, tp, comment, open_time, close_time, close_price, profit, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.get('signal_id'),
                trade.get('order_id'),
                trade.get('symbol'),
                trade.get('action'),
                trade.get('volume'),
                trade.get('price'),
                trade.get('sl'),
                trade.get('tp'),
                trade.get('comment'),
                trade.get('open_time'),
                trade.get('close_time'),
                trade.get('close_price'),
                trade.get('profit'),
                trade.get('status', 'open')
            ))
            conn.commit()
            return c.lastrowid

    def update_trade(self, trade_id: int, updates: Dict[str, Any]) -> None:
        """
        Actualiza los campos de una operación.
        Args:
            trade_id: id de la operación.
            updates: diccionario con los campos a actualizar.
        """
        if not updates:
            return
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [trade_id]
            c.execute(f'UPDATE trades SET {set_clause} WHERE id = ?', values)
            conn.commit()

    def get_signals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Consulta señales por estado."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if status:
                c.execute('SELECT * FROM signals WHERE status = ?', (status,))
            else:
                c.execute('SELECT * FROM signals')
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_trades(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Consulta operaciones por estado."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if status:
                c.execute('SELECT * FROM trades WHERE status = ?', (status,))
            else:
                c.execute('SELECT * FROM trades')
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in c.fetchall()]

    def export_signals_to_csv(self, csv_path: str) -> None:
        """Exporta todas las señales a un archivo CSV."""
        df = pd.read_sql('SELECT * FROM signals', sqlite3.connect(self.db_path))
        df.to_csv(csv_path, index=False)

    def export_trades_to_csv(self, csv_path: str) -> None:
        """Exporta todas las operaciones a un archivo CSV."""
        df = pd.read_sql('SELECT * FROM trades', sqlite3.connect(self.db_path))
        df.to_csv(csv_path, index=False)

# Ejemplo de uso:
# db = TradeDatabase()
# signal_id = db.log_signal({...})
# trade_id = db.log_trade({...})
# db.update_trade(trade_id, {"close_time": ..., "profit": ...})
# db.export_trades_to_csv("trades_export.csv")
