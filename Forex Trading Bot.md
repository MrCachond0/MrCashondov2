# 🧠 BOT DE TRADING FOREX EN PYTHON (SCALPING Y DAY TRADING) — 100% AUTOMATIZADO Llamado Mr Cashondo

Desarrolla un bot de trading profesional y totalmente automatizado en Python, diseñado para operar en el mercado **FOREX** con enfoque exclusivo en **scalping** (1min–5min) y **day trading** (5min–15min). El bot debe conectarse a **MetaTrader 5** y operar de forma automática, utilizando un conjunto probado de estrategias combinadas para generar **señales de alta probabilidad de éxito**, con objetivo de **cerrar consistentemente en Take Profit (TP)**.

---

## 🔧 FUNCIONALIDADES OBLIGATORIAS

1. **Conexión con MetaTrader 5**, leyendo credenciales desde un archivo `.env`: login, password, servidor.
2. **Envío de señales a Telegram** en tiempo real, incluyendo:
   - Tipo de operación (BUY/SELL)
   - Par de divisas
   - Timeframe
   - Precio de entrada, TP y SL
   - Motivo técnico que generó la señal
3. **Ejecución automática de operaciones** en MetaTrader 5 con apertura de orden, asignación de SL y TP, y monitoreo.
4. **Gestión de riesgo integrada**: por operación se arriesga el 1% del balance de la cuenta como máximo, con tamaño de lote calculado automáticamente.
5. **Registro detallado en logs** (archivo `.log`), incluyendo decisiones del bot, errores y resultados de operaciones.

---

## 📈 ESTRATEGIAS Y CONDICIONES PARA ENTRADAS

El bot analizará pares mayores (EURUSD, GBPUSD, USDJPY, XAUUSD, USDCAD) y generará señales únicamente cuando se cumplan las siguientes condiciones combinadas:

### 🔹 Indicadores Técnicos Utilizados

- **EMA 200** → Filtro de tendencia principal
- **EMA 20 y EMA 50** → Señal de impulso
- **RSI (14)** → Entrada cuando hay divergencia o cruce por sobrecompra/sobreventa
- **ATR (14)** → Para cálculo de SL dinámico
- **ADX (14)** → Entrada solo si ADX > 25 (mercado con fuerza)
- **Soporte/Resistencia recientes** → Zonas validadas por al menos 2 rebotes
- **Patrones de vela** → Confirmación con engulfing, pin bar o doji en zonas clave

### 🔹 Condición de Entrada para COMPRA (BUY)

- Precio por encima de EMA 200
- EMA 20 cruza hacia arriba a EMA 50
- RSI cruza hacia arriba de 30 o muestra divergencia alcista
- Confirmación con patrón de vela alcista reciente (ej: bullish engulfing)
- ADX > 25
- Entrada lo más cercana posible a zona de soporte

### 🔹 Condición de Entrada para VENTA (SELL)

- Precio por debajo de EMA 200
- EMA 20 cruza hacia abajo a EMA 50
- RSI cruza hacia abajo de 70 o muestra divergencia bajista
- Confirmación con patrón de vela bajista (ej: bearish engulfing)
- ADX > 25
- Entrada cerca de zona de resistencia

---

## 🎯 TAKE PROFIT, STOP LOSS Y RIESGO

- **SL**: dinámico, definido por 1.5 × ATR(14) desde el precio de entrada
- **TP**: 2.5 × ATR(14) (relación riesgo-beneficio mínima de 1:1.5 o 1:2)
- **Gestión de lote**: tamaño ajustado para que el riesgo no supere el **1% del capital disponible**
- **Break-even** automático si el precio avanza un 1.2×ATR a favor
- **Trailing Stop** opcional configurable (ej: trailing a 1×ATR)

---

## 💬 TELEGRAM ALERTA (EJEMPLO DE MENSAJE)

```
💹 NUEVA OPERACIÓN FOREX
Par: EURUSD  
Timeframe: 5M  
📈 Tipo: COMPRA  
🎯 Entrada: 1.08320  
🚫 SL: 1.08170  
✅ TP: 1.08650  
📊 Estrategia: EMA 20/50 Bullish Cross + RSI Divergencia + Engulfing  
⏰ Hora: 10:43 UTC  
```

---

## 🧠 ARQUITECTURA DEL BOT (MODULAR)

- `mt5_connector.py` → Conexión y ejecución de órdenes en MT5
- `signal_generator.py` → Lógica para escaneo del mercado y generación de señales
- `telegram_alerts.py` → Envío de mensajes vía Telegram Bot API
- `risk_manager.py` → Cálculo de lotaje y control de SL/TP
- `main.py` → Ciclo principal, escaneo en tiempo real (cada X segundos)
- `.env` → Variables de entorno para credenciales

---

## ✅ DETALLES ADICIONALES

- Trabajar con **timezone sincronizado** al de MT5 para evitar errores de horario
- Escaneo cada 30 segundos o al cierre de cada vela nueva (dependiendo del timeframe)
- Backtesting manual sugerido en EURUSD M5, XAUUSD M15, y USDJPY M1
- Logging detallado en JSON o CSV para análisis posterior de estadísticas:
  - Porcentaje de aciertos
  - Profit Factor
  - Drawdown máximo
  - Ratio TP alcanzado vs SL

---

Este bot debe estar enfocado en **consistencia, control de riesgo y sostenibilidad a largo plazo**, evitando el sobretrading y priorizando señales de alta probabilidad.
