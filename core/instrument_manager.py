"""
Módulo para la gestión dinámica de instrumentos y rotación inteligente.
"""
import MetaTrader5 as mt5

class InstrumentManager:
    def __init__(self):
        self.symbols = []

    def load_symbols(self):
        all_symbols = mt5.symbols_get()
        self.symbols = [s.name for s in all_symbols if s.visible]
        return self.symbols

    def get_symbols_by_type(self, forex=True, indices=True, metals=True, stocks=False, crypto=False):
        # Filtrado dinámico según tipo, implementable según necesidades
        return self.symbols

    def rotate_symbols(self, batch_size=50):
        for i in range(0, len(self.symbols), batch_size):
            yield self.symbols[i:i+batch_size]
