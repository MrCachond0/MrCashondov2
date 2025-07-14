# trade_database.py
# Módulo moderno y depurado para registrar, actualizar y consultar señales, operaciones y métricas en una base de datos SQLite.
# Autor: MrCashondo Team
# Última actualización: julio 2025

import os
import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

DB_PATH = os.getenv("TRADE_DB_PATH", "trades.db")

class TradeDatabase:
    def find_duplicate_signal(self, symbol: str, timeframe: str, signal_type: str, window_minutes: int = 60) -> Optional[Dict[str, Any]]:
        """
        Busca una señal abierta (pending/executed) para el mismo símbolo, timeframe y tipo en los últimos X minutos.
        """
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT * FROM signals WHERE symbol=? AND timeframe=? AND signal_type=?
                AND status IN ('pending', 'executed')
                AND timestamp >= ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (symbol, timeframe, signal_type, window_start.isoformat())
            )
            row = c.fetchone()
            if row:
                columns = [desc[0] for desc in c.description]
                return dict(zip(columns, row))
            return None
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Inicializa la base de datos y las tablas si no existen."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Tabla de señales
            c.execute("""
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
                    status TEXT DEFAULT 'pending',
                    probabilidad TEXT,
                    emocional INTEGER DEFAULT 0,
                    generation_params TEXT
                );
            """)

            # Tabla de operaciones reales
            c.execute("""
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
                    probabilidad TEXT,
                    emocional INTEGER DEFAULT 0,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
                );
            """)

            # Tabla de operaciones virtuales
            c.execute("""
                CREATE TABLE IF NOT EXISTS virtual_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    symbol TEXT,
                    timeframe TEXT,
                    signal_type TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    open_time TEXT,
                    close_time TEXT,
                    close_price REAL,
                    result TEXT,
                    history TEXT,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
                );
            """)

            # Tabla de métricas
            c.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    win_rate REAL,
                    profit_factor REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    total_trades INTEGER,
                    total_wins INTEGER,
                    total_losses INTEGER,
                    symbol TEXT,
                    timeframe TEXT
                );
            """)

            # Migración de columna extra
            c.execute("PRAGMA table_info(signals)")
            columns = [row[1] for row in c.fetchall()]
            if 'generation_params' not in columns:
                try:
                    c.execute("ALTER TABLE signals ADD COLUMN generation_params TEXT")
                except Exception as e:
                    print(f"[DB MIGRATION] Error: {e}")
            conn.commit()

    # ---------------------- MÉTODOS DE SEÑALES ----------------------

    def log_signal(self, signal: Dict[str, Any], generation_params: Optional[Dict[str, Any]] = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            data = signal.copy()
            data['generation_params'] = json.dumps(generation_params) if generation_params else None
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            values = tuple(data.values())
            c.execute(f"INSERT INTO signals ({columns}) VALUES ({placeholders})", values)
            conn.commit()
            return c.lastrowid

    def update_signal_status(self, signal_id: int, status: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE signals SET status = ? WHERE id = ?", (status, signal_id))
            conn.commit()

    def get_signals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if status:
                c.execute('SELECT * FROM signals WHERE status = ?', (status,))
            else:
                c.execute('SELECT * FROM signals')
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in c.fetchall()]

    def export_signals_to_csv(self, csv_path: str) -> None:
        df = pd.read_sql('SELECT * FROM signals', sqlite3.connect(self.db_path))
        df.to_csv(csv_path, index=False)

    # ---------------------- MÉTODOS DE TRADES ----------------------

    def log_trade(self, trade: Dict[str, Any]) -> int:
        trade.setdefault('probabilidad', None)
        trade.setdefault('emocional', 0)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            columns = ', '.join(trade.keys())
            placeholders = ', '.join(['?'] * len(trade))
            c.execute(f"INSERT INTO trades ({columns}) VALUES ({placeholders})", tuple(trade.values()))
            conn.commit()
            return c.lastrowid

    def update_trade(self, trade_id: int, updates: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [trade_id]
            c.execute(f"UPDATE trades SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def update_trade_by_order_id(self, order_id: str, updates: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [order_id]
            c.execute(f"UPDATE trades SET {set_clause} WHERE order_id = ?", values)
            conn.commit()

    def update_trade_status_by_order_id(self, order_id: str, status: str, close_price: Optional[float] = None, close_time: Optional[str] = None, profit: Optional[float] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            final_status = 'trailing' if status.lower() == 'sl' and profit and profit > 0 else status
            updates = ["status = ?"]
            values = [final_status]
            if close_price is not None:
                updates.append("close_price = ?")
                values.append(close_price)
            if close_time is not None:
                updates.append("close_time = ?")
                values.append(close_time)
            if profit is not None:
                updates.append("profit = ?")
                values.append(profit)
            values.append(order_id)
            set_clause = ", ".join(updates)
            c.execute(f"UPDATE trades SET {set_clause} WHERE order_id = ?", values)
            conn.commit()

    def get_trades(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if status:
                c.execute('SELECT * FROM trades WHERE status = ?', (status,))
            else:
                c.execute('SELECT * FROM trades')
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in c.fetchall()]

    def export_trades_to_csv(self, csv_path: str) -> None:
        df = pd.read_sql('SELECT * FROM trades', sqlite3.connect(self.db_path))
        df.to_csv(csv_path, index=False)

    # ---------------------- MÉTODOS DE TRADES VIRTUALES ----------------------

    def log_virtual_trade(self, virtual_trade: Dict[str, Any]) -> int:
        data = virtual_trade.copy()
        if 'history' in data and isinstance(data['history'], (list, dict)):
            data['history'] = json.dumps(data['history'])
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            c.execute(f"INSERT INTO virtual_trades ({columns}) VALUES ({placeholders})", tuple(data.values()))
            conn.commit()
            return c.lastrowid

    def update_virtual_trade(self, vt_id: int, updates: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [vt_id]
            c.execute(f"UPDATE virtual_trades SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def get_virtual_trades(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if symbol:
                c.execute("SELECT * FROM virtual_trades WHERE symbol = ?", (symbol,))
            else:
                c.execute("SELECT * FROM virtual_trades")
            rows = c.fetchall()
            columns = [desc[0] for desc in c.description]
            result = []
            for row in rows:
                d = dict(zip(columns, row))
                if d.get('history'):
                    try:
                        d['history'] = json.loads(d['history'])
                    except Exception:
                        pass
                result.append(d)
            return result

    # ---------------------- MÉTODOS DE MÉTRICAS ----------------------

    def log_metrics(self, metrics: dict, symbol: str = None, timeframe: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            data = metrics.copy()
            data['timestamp'] = data.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data['symbol'] = symbol
            data['timeframe'] = timeframe
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            values = tuple(data.values())
            c.execute(f"INSERT INTO metrics ({columns}) VALUES ({placeholders})", values)
            conn.commit()
            return c.lastrowid

    def get_metrics(self, symbol: str = None, timeframe: str = None) -> list:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            query = "SELECT * FROM metrics"
            params = []
            if symbol and timeframe:
                query += " WHERE symbol=? AND timeframe=?"
                params = [symbol, timeframe]
            elif symbol:
                query += " WHERE symbol=?"
                params = [symbol]
            elif timeframe:
                query += " WHERE timeframe=?"
                params = [timeframe]
            c.execute(query, params)
            columns = [desc[0] for desc in c.description]
            return [dict(zip(columns, row)) for row in c.fetchall()]

    def export_metrics_to_csv(self, csv_path: str) -> None:
        df = pd.read_sql('SELECT * FROM metrics', sqlite3.connect(self.db_path))
        df.to_csv(csv_path, index=False)
