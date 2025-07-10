# Mr.Cashondo Trading Bot

## Descripción
Mr.Cashondo es un bot de trading automatizado para FOREX, índices y metales, con gestión de riesgo avanzada y alertas por Telegram. El bot realiza escaneos periódicos de todos los símbolos disponibles y ejecuta operaciones según señales generadas por algoritmos propios.

## Flujo de Ejecución Actualizado
1. **Validación de Suscripción:**
   - Al iniciar el bot, se solicita el correo y token de suscripción SOLO UNA VEZ por ejecución.
   - La validación se realiza contra una base de datos en Supabase.
   - Si la suscripción es válida, el bot continúa; si no, se detiene.
2. **Inicialización de Componentes:**
   - Conexión a MetaTrader 5 (MT5) usando los datos de cuenta, password y servidor.
   - Inicialización de generador de señales, gestor de riesgo y alertas de Telegram.
3. **Escaneo y Ejecución:**
   - El bot escanea TODOS los símbolos de FOREX, índices y metales configurados en la cuenta MT5.
   - Procesa señales, ejecuta operaciones y gestiona posiciones activas.
4. **Alertas y Reportes:**
   - Envía alertas de señales y ejecuciones a Telegram.
   - Envía resumen diario y notificaciones de errores críticos.

## Instalación y Uso

### Requisitos
- Windows 10/11
- MetaTrader 5 instalado
- Python 3.10+ (solo para desarrollo o ejecución directa)
- Cuenta activa y suscripción válida

### Instalación Automática vía .exe
Próximamente estará disponible un instalador `.exe` que:
- Instala todas las dependencias necesarias.
- Solicita los datos de cuenta, password y servidor de MT5 al primer uso.
- Protege el código y credenciales mediante cifrado y ofuscación para evitar clonación o robo.
- Permite ejecutar el bot con doble clic, sin requerir conocimientos técnicos.

### Instalación Manual (Desarrolladores)
1. Clona el repositorio.
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura el archivo `.env` con tus credenciales y claves de API.
4. Ejecuta el bot:
   ```bash
   python main.py
   ```

## Seguridad y Protección
- El instalador .exe cifrará los archivos críticos y credenciales.
- El código fuente estará ofuscado y protegido contra ingeniería inversa.
- La validación de suscripción es obligatoria y se realiza en cada inicio.

## Soporte
Para soporte técnico o problemas con la suscripción, contacta al desarrollador.


![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)

# Mr. Cashondo - Bot de Trading Automatizado Multi-Instrumento

## � Resumen End-to-End (2025)

Mr. Cashondo es un bot profesional de trading automático, modular y multi-instrumento, enfocado en scalping y day trading en FOREX, metales e índices, con gestión de riesgo avanzada y monitoreo en tiempo real.

---

## 🏗️ Arquitectura Modular

```
MrCashondo/
├── main.py              # Ciclo principal, orquestador del bot
├── mt5_connector.py     # Conexión y ejecución de órdenes en MetaTrader 5
├── signal_generator.py  # Generación y filtrado de señales técnicas
├── risk_manager.py      # Cálculo de lotaje y control de riesgo
├── telegram_alerts.py   # Envío de alertas a Telegram
├── configure_instruments.py # Configuración dinámica de instrumentos
├── test_*.py            # Tests unitarios y de integración (pytest)
├── .env                 # Variables de entorno (credenciales y configuración)
├── *.log                # Logs detallados de cada módulo
```

---

## 🚦 Flujo End-to-End

1. **Inicialización**: Carga de variables de entorno y configuración de instrumentos. Conexión a MetaTrader 5 usando credenciales del `.env`.
2. **Rotación y Escaneo**: Rotación entre ~370 símbolos (FOREX, metales, índices). Analiza 50 símbolos por ciclo (cada 30 segundos aprox.). Filtros pre-técnicos eliminan símbolos inoperables (spread, volumen, datos insuficientes).
3. **Generación de Señales**: Filtros técnicos y scoring flexible (mínimo 1 condición técnica). Detección expandida de cruces EMA, RSI, ATR, ADX y patrones de velas. Se genera una señal por cada oportunidad válida, sin límite artificial de cantidad (el límite real es la gestión de riesgo y posiciones abiertas).
4. **Gestión de Riesgo**: Cálculo de lotaje y SL/TP usando el balance y ATR. Límites: máximo 4 posiciones abiertas globales, 1 por símbolo, máximo 1% de riesgo por operación.
5. **Ejecución y Notificación**: Si la señal pasa todos los filtros, se ejecuta la orden en MT5 y se envía alerta a Telegram con todos los detalles técnicos y de riesgo. Todo queda registrado en logs.
6. **Monitoreo y Logging**: Logs detallados por módulo. Métricas clave: señales diarias, win rate, profit factor, drawdown, ratio SL/TP.

---

# Mr. Cashondo - Bot de Trading Automatizado Multi-Instrumento

🧠 **Bot de Trading Profesional** diseñado ## 📊 Instrumentos Monitoreados

### 🎛️ Configuración de Instrumentos (NUEVA FUNCIONALIDAD)
- **Sistema configurable**: Habilitar/deshabilitar tipos de instrumentos dinámicamente
- **Configuración actual**: ✅ FOREX, ✅ Índices, ✅ Metales | ❌ Acciones, ❌ Crypto, ❌ ETFs (temporal)
- **Cambio en tiempo real**: Sin necesidad de reiniciar el bot
- **Configurador incluido**: Script `configure_instruments.py` para gestión fácil

### Configuración Actual (Predeterminada)
- ✅ **FOREX**: Todos los pares de divisas habilitados
- ✅ **Metales Preciosos**: Oro, plata, platino, paladio habilitados
- ✅ **Índices Bursátiles**: US30, US500, NAS100, GER30, UK100, etc. habilitados
- ❌ **Acciones**: DESHABILITADO permanentemente
- ❌ **Criptomonedas**: DESHABILITADO permanentemente
- ❌ **ETFs**: DESHABILITADO permanentemente

### Sistema de Rotación Multi-Instrumento
- **Sistema dinámico**: Analiza instrumentos según configuración activa
- **Rotación inteligente**: Procesa 50 símbolos por ciclo para optimizar memoria
- **Cobertura completa**: Incluye solo instrumentos habilitados
- **Símbolos preferidos**: Prioriza instrumentos de alta liquidez en cada rotación

### Categorías de Instrumentos Disponibles
- **FOREX (~37 pares)**: Majors, minors, crosses y exóticos
- **Metales Preciosos (~4)**: Oro, plata, platino, paladio
- **Índices Internacionales**: US30, US500, NAS100, GER30, UK100, AUS200
- **Acciones Principales**: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META (deshabilitadas)
- **Criptomonedas**: BTC, ETH, LTC, XRP, ADA (deshabilitadas) **TODOS los mercados disponibles en MetaTrader 5** con estrategias de scalping y day trading completamente automatizadas.

## 🚀 Características Principales

- **Conexión MetaTrader 5**: Integración completa con MT5 para ejecución automática
- **Análisis Multi-Instrumento Configurable**: FOREX, metales, índices, acciones y ETFs
- **Sistema de Rotación**: Gestiona miles de símbolos mediante rotación inteligente
- **Configuración de Instrumentos**: Habilitar/deshabilitar tipos de instrumentos dinámicamente
- **Análisis Técnico Avanzado**: Utiliza EMA, RSI, ATR, ADX y patrones de velas
- **Filtros Adaptativos**: Sistema de filtros dinámicos por volatilidad y tendencia
- **Gestión de Riesgo**: Control automático de riesgo con máximo 1% por operación
- **Alertas Telegram**: Notificaciones en tiempo real de señales y ejecuciones
- **Logging Detallado**: Seguimiento completo de decisiones y análisis
- **Arquitectura Modular**: Código limpio y mantenible siguiendo mejores prácticas
- **Compatibilidad Windows**: Optimizado para sistemas Windows con encoding UTF-8


## 📋 Requisitos

- Python 3.10+
- MetaTrader 5 instalado en Windows
- Cuenta de trading (demo o real)
- Bot de Telegram configurado
- Git instalado (para clonar y subir el proyecto)


## � Subida inicial a GitHub

1. **Inicializa el repositorio y sube el código**
```powershell
cd "ruta/del/proyecto/MrCashondo"
git init
git add .
git commit -m "Add initial Mr. Cashondo trading bot project"
git branch -M main
git remote add origin https://github.com/MrCachond0/MrCashondov2.git
git push -u origin main
```

## �🔧 Instalación y configuración

1. **Clona el repositorio**
```powershell
git clone https://github.com/MrCachond0/MrCashondov2.git
cd MrCashondov2
```

2. **Crea el entorno virtual**
```powershell
python -m venv venv
venv\Scripts\activate
```

3. **Instala dependencias**
```powershell
pip install -r requirements.txt
```


4. **Configura las variables de entorno**
   - Copia `.env.example` a `.env`
   - Completa con tus credenciales reales:
     ```env
     TELEGRAM_BOT_TOKEN=tu_token_aqui
     TELEGRAM_CHAT_ID=tu_chat_id_aqui
     MT5_LOGIN=tu_login_mt5
     MT5_PASSWORD=tu_password_mt5
     MT5_SERVER=tu_servidor_mt5
     # --- Suscripciones (Supabase + Stripe) ---
     SUPABASE_URL=https://<tu-proyecto>.supabase.co
     SUPABASE_API_KEY=tu_api_key_publica
     SUBSCRIPTION_API_URL=https://<tu-backend>.vercel.app/validate
     # USER_EMAIL=usuario@dominio.com  # (opcional)
     ```
   - **¡No subas nunca tu archivo `.env` real a GitHub!**

## 🔑 Control de suscripciones (Supabase + Stripe)

El bot valida tu suscripción antes de operar. Debes tener un email registrado y activo en la base de datos de Supabase (se activa automáticamente al pagar por Stripe).

Al iniciar el bot, se te pedirá tu email de suscripción (o lo puedes dejar en `.env`).
Si la suscripción está activa, el bot funcionará normalmente. Si no, se bloqueará y mostrará un mensaje de error.

**¿Cómo funciona?**
- El backend recibe los pagos de Stripe y actualiza la tabla de suscripciones en Supabase.
- El bot consulta la API `/validate?email=...` antes de operar.
- Si la suscripción está activa, permite el uso; si no, lo bloquea.

5. **Configuración rápida en Windows**
   - Ejecuta `setup.bat` para instalar todo automáticamente.
   - Para limpiar y reinstalar, usa `clean_setup.bat`.

6. **Scripts útiles**
   - `run_bot.bat`: Ejecuta el bot con entorno virtual y chequeos previos.
   - `run_tests.bat`: Ejecuta los tests con pytest.
## 📂 Estructura de archivos principal

| Archivo/Carpeta              | Descripción                                      |
|------------------------------|--------------------------------------------------|
| main.py                      | Ciclo principal y orquestador del bot            |
| mt5_connector.py             | Conexión y ejecución de órdenes en MetaTrader 5  |
| signal_generator.py          | Generación y filtrado de señales técnicas        |
| risk_manager.py              | Cálculo de lotaje y control de riesgo            |
| telegram_alerts.py           | Envío de alertas a Telegram                      |
| configure_instruments.py     | Configuración dinámica de instrumentos           |
| trade_database.py            | Registro y consulta de señales/operaciones       |
| export_tocsv.py              | Exporta base de datos a CSV                      |
| test_*.py                    | Tests unitarios e integración (pytest)           |
| .env.example                 | Plantilla de variables de entorno                |
| requirements.txt             | Dependencias del proyecto                        |
| *.log                        | Logs detallados de cada módulo                   |
| exports/                     | Exportaciones de señales y trades                |
## ⚠️ Configuración de riesgo

El bot soporta dos modos de gestión de riesgo:

- `percent_margin`: Arriesga un % del balance/margen libre (modo clásico)
- `fixed_usd`: Arriesga SIEMPRE el mismo monto en USD por operación (recomendado para cuentas pequeñas)

Configura esto en `risk_config.py`:
```python
RISK_MODE = "fixed_usd"   # o "percent_margin"
FIXED_RISK_USD = 1.0      # Cambia este valor al monto deseado en USD
```
El cambio es inmediato y no requiere reiniciar el bot.
## 📤 Exportar base de datos a CSV

Puedes exportar todas las señales y operaciones a CSV con:
```powershell
python export_tocsv.py
```
Los archivos se guardan en la carpeta `exports/` con timestamp.
## ❓ Preguntas frecuentes (FAQ)

**¿Por qué no se generan señales?**
- Es normal si los filtros técnicos no se cumplen. Revisa los logs para ver el motivo exacto.
- El mercado puede estar en baja volatilidad o fuera de horario óptimo.

**¿Cómo cambio el riesgo por operación?**
- Edita `risk_config.py` y ajusta `FIXED_RISK_USD` o cambia el modo a `percent_margin`.

**¿Puedo usarlo en cuenta real?**
- Sí, pero siempre prueba primero en demo. El trading conlleva riesgos.

**¿Cómo restauro la configuración de instrumentos?**
- Ejecuta `python configure_instruments.py` o edita el script para personalizar.

**¿Qué hago si tengo errores de conexión MT5?**
- Verifica credenciales y que MetaTrader 5 esté abierto y conectado.

**¿Cómo contribuyo?**
- Haz fork, crea una rama, realiza tus cambios y abre un Pull Request.
## 📝 Notas importantes

- **Nunca subas tu archivo `.env` real ni credenciales a GitHub.**
- El bot está optimizado para Windows, pero puede adaptarse a Linux/Mac con cambios menores.
- Usa siempre entorno virtual para evitar conflictos de dependencias.

## 🏃‍♂️ Uso

### Ejecutar el bot
```bash
python main.py
```

### Ejecutar tests
```bash
pytest test_bot.py -v
```

### Formatear código
```bash
black .
```

## 📈 Estrategias Implementadas


### Estrategia "Signal Flow Optimized" (SFO)
- **Validación progresiva**: Solo se requiere 1 condición técnica para generar señal.
- **Scoring flexible**: Señales con score ≥ 40/100.
- **Umbrales técnicos**:
  - ATR mínimo: 0.0003
  - ADX mínimo: 6.0
  - RSI compra: 35-52, venta: 48-65
- **Gestión de riesgo**:
  - SL: 1.0 × ATR
  - TP: 1.6 × ATR
  - Breakeven: 0.6 × ATR
  - Máximo 1% de balance por operación
  - Máximo 4 posiciones abiertas, 1 por símbolo


### Condiciones de Entrada BUY
- Precio por encima de EMA 200 (filtro de tendencia)
- EMA 20 cruza hacia arriba a EMA 50 (detección expandida, ventana de 3 barras)
- RSI > 35 o divergencia alcista
- Patrón de vela alcista (engulfing/pin bar)
- ADX > 6.0 (mercado con fuerza)

### Condiciones de Entrada SELL
- Precio por debajo de EMA 200 (filtro de tendencia)
- EMA 20 cruza hacia abajo a EMA 50 (detección expandida, ventana de 3 barras)
- RSI < 65 o divergencia bajista
- Patrón de vela bajista (engulfing/pin bar)
- ADX > 6.0 (mercado con fuerza)


### Métricas de Éxito Proyectadas
- **Señales diarias**: 10-20 (según condiciones de mercado)
- **Win rate objetivo**: 60-65%
- **Profit factor**: 1.4-1.8
- **Máximo drawdown**: 12%
- **Ratio riesgo/recompensa**: 1:1.4


### Monitoreo Diario
- **Generación de señales**: Mínimo esperado: 8, óptimo: 12-18, máximo: 25
- **Calidad de ejecución**: Slippage <0.0003, ejecución <2s, tasa de llenado >95%
- **Riesgo**: VAR diario <2%, correlación <0.3, exposición máxima <2.4%

## 🏗️ Arquitectura

```
MrCashondo/
├── main.py              # Módulo principal del bot
├── mt5_connector.py     # Conexión y órdenes MT5
├── signal_generator.py  # Generación de señales
├── risk_manager.py      # Gestión de riesgo
├── telegram_alerts.py   # Alertas Telegram
├── test_bot.py         # Tests unitarios
├── requirements.txt    # Dependencias
└── .env               # Variables de entorno
```

## ⚙️ Configuración de Instrumentos

### 🎛️ Configurar Tipos de Instrumentos
```bash
# Configurador interactivo
python configure_instruments.py

# Test de configuración actual
python test_config.py
```

### 📋 Opciones de Configuración Disponibles
1. **Configuración Actual**: FOREX + Índices + Metales (recomendada)
2. **Solo FOREX**: Únicamente pares de divisas
3. **FOREX + Metales**: Divisas y metales preciosos
4. **FOREX + Índices**: Divisas e índices bursátiles
5. **Todo Habilitado**: Todos los instrumentos disponibles
6. **Configuración Personalizada**: Selección manual por tipo

### 🔧 Configuración Programática
```python
from signal_generator import SignalGenerator

# Crear instancia
signal_generator = SignalGenerator()

# Habilitar solo FOREX
signal_generator.configure_instrument_types(
    forex=True, indices=False, metals=False, stocks=False, crypto=False
)

# Habilitar FOREX + Metales + Índices (configuración actual)
signal_generator.configure_instrument_types(
    forex=True, indices=True, metals=True, stocks=False, crypto=False
)

# Habilitar temporalmente acciones
signal_generator.configure_instrument_types(stocks=True)

# Verificar configuración
config = signal_generator.get_instrument_types_status()
print(config)
```

### 🚫 Instrumentos Temporalmente Deshabilitados
- **Acciones individuales**: Para reducir ruido y enfocarse en mercados más líquidos
- **Criptomonedas**: Volatilidad extrema, se analizarán por separado
- **ETFs complejos**: Filtrados automáticamente por liquidez

### ✅ Beneficios de la Configuración Actual
- **Rendimiento optimizado**: Menos símbolos = análisis más rápido
- **Mejor calidad de señales**: Enfoque en instrumentos líquidos
- **Gestión de riesgo**: Mercados más predecibles
- **Flexibilidad**: Cambios sin reiniciar el sistema

### Sistema de Rotación Multi-Instrumento
- **Sistema dinámico**: Analiza TODOS los instrumentos disponibles en MT5
- **Rotación inteligente**: Procesa 50 símbolos por ciclo para optimizar memoria
- **Cobertura completa**: Incluye FOREX, metales, índices, acciones y ETFs
- **Símbolos preferidos**: Prioriza instrumentos de alta liquidez en cada rotación

### Categorías de Instrumentos
- **FOREX (37 pares)**: Majors, minors, crosses y exóticos
- **Metales Preciosos (4)**: Oro, plata, platino, paladio
- **Índices Internacionales**: US30, US500, NAS100, GER30, UK100, AUS200
- **Acciones Principales**: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META
- **ETFs y Otros**: Miles de instrumentos adicionales disponibles

### Estados de Análisis
- ✅ **Filtros pasados**: Símbolos que cumplen ATR, ADX y spread adaptativos
- 🔄 **En rotación**: Sistema rota entre ~370 símbolos operables
- 📊 **Diversificación**: Análisis automático de múltiples clases de activos
- ❌ **Filtrados**: No cumplen criterios mínimos de volatilidad y liquidez

## ⚙️ Configuración Avanzada

### Parámetros de Riesgo
```python
risk_params = RiskParameters(
    max_risk_per_trade=0.01,      # 1% por operación
    max_daily_loss=0.05,          # 5% pérdida diaria máxima
    max_open_positions=3,         # Máximo 3 posiciones abiertas
    min_risk_reward_ratio=1.5     # Ratio mínimo 1:1.5
)
```

### Filtros Adaptativos por Tipo de Instrumento
- **FOREX**: ATR dinámico, spread < 3-15 pips según par
- **Metales**: Spread < 50 pips, alta volatilidad
- **Índices**: Spread < 100 puntos, ADX > 20
- **Acciones**: Spread < 0.50 USD, volumen mínimo
- **ETFs**: Criterios adaptativos por liquidez
- **Sesión Trading**: Filtro de horarios óptimos (configurable)
- **Rotación**: 50 símbolos por ciclo, rotación automática cada 3 scans

### Timeframes
- M5: Scalping principal (filtros estrictos)
- M15: Day trading (análisis confirmatorio)

## 🔍 Monitoreo

### Estado Actual del Bot ✅
- **~370 símbolos** monitoreados mediante rotación inteligente
- **50 símbolos por ciclo** analizados cada 30 segundos
- **Rotación automática** cada 3 scans para cobertura completa
- **Multi-instrumento**: FOREX, metales, índices, acciones, ETFs
- **Filtros funcionando**: ATR, ADX, spread adaptativos por tipo
- **Sistema estable**: Sin errores Unicode, logging optimizado
- **Análisis detallado**: Logs claros muestran decisiones en tiempo real

### Logs
- `mr_cashondo_bot.log`: Log principal del bot
- `mt5_connector.log`: Logs de conexión MT5  
- `signal_generator.log`: Logs de generación de señales
- `risk_manager.log`: Logs de gestión de riesgo
- `telegram_alerts.log`: Logs de alertas Telegram

### Logging Mejorado
- **Filtros detallados**: Estado de cada filtro por símbolo
- **Indicadores técnicos**: Valores en tiempo real de EMA, RSI, ATR, ADX
- **Sin emojis**: Compatible con sistemas Windows
- **Timestamps precisos**: Seguimiento temporal de todas las decisiones

### Métricas Clave
- Win Rate (Tasa de éxito)
- Profit Factor
- Drawdown máximo
- Ratio SL vs TP alcanzado


## 🚨 Alertas Telegram

Las alertas incluyen: instrumento, timeframe, tipo (BUY/SELL), entrada, SL, TP, motivo técnico, hora UTC.

Ejemplo:
```
💹 NUEVA OPERACIÓN
Instrumento: XAUUSD (Oro)
Timeframe: 5M
📈 Tipo: COMPRA
🎯 Entrada: 2045.50
🚫 SL: 2038.25
✅ TP: 2056.85
📊 Estrategia: EMA 20/50 Bullish Cross + RSI Divergencia
⚖️ Tipo: Metal Precioso
⏰ Hora: 10:43 UTC
```


## 🧪 Testing

El bot incluye tests exhaustivos con `pytest` para:
- Cálculo de indicadores técnicos
- Generación de señales
- Gestión de riesgo
- Conectividad MT5 y Telegram
- Flujos end-to-end

```bash
# Ejecutar todos los tests
pytest test_bot.py -v

# Ejecutar tests específicos
pytest test_bot.py::TestTechnicalIndicators -v
```


## 🛡️ Seguridad

- **Variables de entorno**: Nunca hardcodear credenciales
- **Logs seguros**: No registrar información sensible
- **Validación de entrada**: Todos los inputs son validados
- **Límites de riesgo**: Múltiples capas de protección


## 🔧 Troubleshooting

### Problemas Comunes Resueltos
- ✅ **UnicodeEncodeError**: Eliminados emojis del código
- ✅ **Logging en Windows**: Configurado encoding UTF-8
- ✅ **Filtros adaptativos**: Sistema de umbrales dinámicos funcionando
- ✅ **Conectividad MT5**: Manejo robusto de errores de conexión

### Si no aparecen señales
1. **Normal**: Las señales solo aparecen cuando se cumplen los filtros técnicos y de riesgo
2. **Verificar logs**: Los logs muestran qué símbolos están siendo analizados y por qué se filtran
3. **Filtros activos**: Revisa que los símbolos pasen los filtros ATR, ADX y scoring
4. **Mercado**: Durante sesiones de baja volatilidad es normal no tener señales
5. **No hay límite artificial de señales**: El límite real es la gestión de riesgo y posiciones abiertas


## 📊 Rendimiento Actual

### Símbolos que Frecuentemente Pasan Filtros
- **FOREX**: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
- **Metales**: XAUUSD, XAGUSD, GOLD, SILVER
- **Índices**: US30, US500, NAS100, GER30, UK100
- **Acciones**: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META
- **ETFs**: Instrumentos de alta liquidez según disponibilidad del broker

### Estadísticas de Filtrado por Rotación
- **~75% de símbolos** pasan filtros pre-técnicos (spread, volumen)
- **~50% de símbolos** cumplen filtros adaptativos por tipo de instrumento
- **~10-15%** generan señales de entrada en condiciones normales de mercado
- **Rotación completa**: ~7-8 ciclos para cubrir todos los símbolos disponibles


## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-feature`)
3. Commit tus cambios (`git commit -m 'Add nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

## ⚠️ Disclaimer

Este bot está diseñado para fines educativos y de demostración. El trading de FOREX conlleva riesgos significativos y puede resultar en pérdidas. Siempre prueba en cuentas demo antes de usar dinero real.

## 📞 Soporte

Para soporte técnico o consultas:
- Crear un Issue en GitHub
- Revisar la documentación
- Ejecutar tests para verificar funcionalidad

---

**Mr. Cashondo** - Trading inteligente, automatizado y multi-instrumento 🚀

---


## 🎯 NUEVA CARACTERÍSTICA: ANÁLISIS MULTI-INSTRUMENTO

### 🔄 Sistema de Rotación Completo
- **373 símbolos operables** detectados automáticamente
- **50 símbolos por ciclo** para optimizar memoria y rendimiento
- **8 ciclos de rotación** para cobertura completa
- **Rotación automática** cada 3 scans del mercado

### 🌍 Diversidad de Instrumentos
- **FOREX**: Todos los pares de divisas disponibles
- **Metales Preciosos**: Oro, plata, platino, paladio
- **Índices**: US30, US500, NAS100, GER30, UK100, AUS200
- **Acciones**: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META
- **ETFs y Otros**: Miles de instrumentos adicionales

### ⚙️ Filtros Adaptativos por Tipo
- **FOREX**: Spread 3-15 pips según clasificación
- **Metales**: Spread hasta 50 pips
- **Índices**: Spread hasta 100 puntos
- **Acciones**: Spread hasta 0.50 USD
- **Otros**: Criterios dinámicos según liquidez

### 🎯 Símbolos Preferidos Priorizados
- **24 símbolos** de alta prioridad incluidos en cada rotación
- **11 activos** promedio por ciclo
- **Diversificación**: FOREX + Metales + Índices + Acciones