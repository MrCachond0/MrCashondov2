"""
calendar_blackout.py
Sistema de blackout temporal por calendario económico para Mr.Cashondo
Lee eventos de alto impacto desde un CSV local y expone una función para saber si hay blackout activo para un símbolo y timestamp.
"""
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

CALENDAR_CSV = os.getenv("CALENDAR_CSV", "economic_calendar.csv")

class EconomicEvent:
    def __init__(self, timestamp: datetime, symbol: str, impact: str, description: str):
        self.timestamp = timestamp
        self.symbol = symbol
        self.impact = impact
        self.description = description

    def is_high_impact(self) -> bool:
        return self.impact.lower() in ("high", "alto", "alta")

class CalendarBlackout:
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or CALENDAR_CSV
        self.events: List[EconomicEvent] = []
        self._load_events()

    def _load_events(self):
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(row['timestamp'])
                    symbol = row.get('symbol', '')
                    impact = row.get('impact', '')
                    desc = row.get('description', '')
                    self.events.append(EconomicEvent(ts, symbol, impact, desc))
                except Exception:
                    continue

    def is_blackout(self, symbol: str, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        for event in self.events:
            if not event.is_high_impact():
                continue
            # Blackout: 30 min antes y 30 min después del evento
            if event.symbol.upper() in symbol.upper() or event.symbol == "ALL":
                if abs((event.timestamp - now).total_seconds()) <= 1800:
                    return True
        return False

    def get_next_event(self, symbol: str, now: Optional[datetime] = None) -> Optional[EconomicEvent]:
        now = now or datetime.utcnow()
        future_events = [e for e in self.events if e.timestamp > now and (e.symbol.upper() in symbol.upper() or e.symbol == "ALL")]
        if not future_events:
            return None
        return min(future_events, key=lambda e: e.timestamp)
