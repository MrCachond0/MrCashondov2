"""
Gestor centralizado de instrumentos para Mr. Cashondo
Obtiene y actualiza la lista de símbolos en tiempo real desde MT5
"""

import MetaTrader5 as mt5
import logging

class InstrumentsManager:
    def __init__(self):
        self.symbols = []
        self.logger = logging.getLogger("InstrumentsManager")

    def update_symbols(self):
        """Obtiene todos los símbolos disponibles en MT5 en tiempo real, sin hardcodear."""
        if not mt5.initialize():
            self.logger.error("No se pudo inicializar MetaTrader 5 para obtener símbolos.")
            return []
        all_symbols = mt5.symbols_get()
        self.symbols = [s.name for s in all_symbols]
        self.logger.info(f"Símbolos actualizados: {len(self.symbols)} disponibles.")
        return self.symbols

    def get_symbols_by_type(self, symbol_type: str):
        """Filtra símbolos por tipo: FOREX, METALS, INDICES, etc. (dinámico, no hardcodeado)"""
        # Ejemplo simple: filtrar por nombre, se puede mejorar con info de mt5.symbol_info
        if not self.symbols:
            self.update_symbols()
        if symbol_type.lower() == "forex":
            return [s for s in self.symbols if any(c in s for c in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]) and len(s) <= 7]
        elif symbol_type.lower() == "metals":
            return [s for s in self.symbols if any(m in s for m in ["XAU", "XAG", "GOLD", "SILVER", "PLATINUM", "PALLADIUM"])]
        elif symbol_type.lower() == "indices":
            return [s for s in self.symbols if any(i in s for i in ["US30", "US500", "NAS100", "GER30", "UK100", "AUS200"])]
        else:
            return self.symbols
