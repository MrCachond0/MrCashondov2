# Configuración de riesgo para Mr. Cashondo
# Este archivo controla el modo de gestión de riesgo y el monto fijo en USD a arriesgar por operación.
# Puedes modificar estos valores en caliente, el cambio es inmediato.

# Opciones de modo de riesgo:
# RISK_MODE = "percent_margin"  # Arriesga un % del balance/margen
# RISK_MODE = "fixed_usd"       # Arriesga un monto fijo en USD por operación

RISK_MODE = "percent_margin"  # o "fixed_usd"
FIXED_RISK_USD = 1.0     # Cambia este valor al monto deseado en USD
# Porcentaje de riesgo por operación (para percent_margin)
MAX_RISK_PER_TRADE = 0.02  # 2% por operación (ajustado para scalping/day trading)