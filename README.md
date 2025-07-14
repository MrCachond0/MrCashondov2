## Actualización automática (Auto-Update)
El bot incluye un sistema de auto-actualización:

- Cada vez que se ejecuta, compara la versión local (`version.txt`) con la versión remota en GitHub.
- Si hay una nueva versión, descarga y reemplaza los archivos automáticamente.
- El usuario solo debe reiniciar el bot tras una actualización.

**Importante:** Si modificas el código, actualiza el número de versión en `version.txt` antes de subir a GitHub.

## Cómo crear el ejecutable (.exe) para distribución

1. Asegúrate de tener `pyinstaller` instalado:
   ```powershell
   pip install pyinstaller
   ```
2. Desde la raíz del proyecto, ejecuta:
   ```powershell
   pyinstaller --onefile --add-data ".env.enc;." --add-data ".env.key;." --add-data "EULA.txt;." --add-data "README.md;." --add-data "version.txt;." --hidden-import cryptography --name MrCashondoBot main.py
   ```
3. El ejecutable estará en la carpeta `dist/` como `MrCashondoBot.exe`.

**Nota:** Si usas dependencias adicionales, agrégalas con `--add-data` o `--hidden-import` según sea necesario.

## Flujo de actualización para el usuario final

1. El usuario ejecuta el bot normalmente.
2. Si hay una nueva versión en GitHub, el bot la descarga y reemplaza los archivos.
3. El usuario solo debe reiniciar el bot para aplicar la actualización.
## Instalación y configuración rápida
1. **Descarga y descomprime** el paquete de MrCashondoV2 en una carpeta de tu PC.
2. **Ejecuta** el archivo `setup.bat` (doble clic). Esto instalará todo lo necesario automáticamente y lanzará el instalador interactivo.
3. El instalador solo te pedirá tus datos personales: Chat ID de Telegram, credenciales de MT5, email y token de suscripción. El resto de la configuración ya está cifrada y protegida.
4. Acepta el EULA cuando se muestre en pantalla.
5. **Ejecuta** el archivo `run_bot.bat` para iniciar el bot.

## Seguridad y protección
- **Tus datos personales** se guardan en `.env.user`.
- **Tokens y claves sensibles** (TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_API_KEY) ya están cifrados y embebidos en el ejecutable, nunca se exponen ni se solicitan al usuario final.
- El código fuente del ejecutable está ofuscado y protegido con PyArmor.

## ¿Cómo funciona?
- El bot analiza automáticamente los mercados habilitados (FOREX, metales, índices) y ejecuta operaciones según su estrategia.
- Recibirás alertas y reportes automáticos por Telegram sobre las operaciones y el estado del bot.
- La gestión de riesgo es configurable y centralizada: puedes elegir arriesgar un monto fijo en USD por operación o un porcentaje de tu balance (por defecto, 2% por operación y exposición máxima de 40% para FOREX, 25% para metales, 20% para índices; puedes modificarlo en `risk_config.py`).
- El bot solo funcionará si tu suscripción está activa y los datos ingresados son correctos.

## Requisitos previos
- Windows 10/11
- MetaTrader 5 instalado
- Python 3.10+ (solo para desarrollo o ejecución directa)
- Cuenta activa y suscripción válida
- Git instalado (opcional, para clonar el repo)

## Instalación y configuración inicial (modo desarrollador)
1. Clona el repositorio:
   ```powershell
   git clone https://github.com/MrCachond0/MrCashondov2.git
   cd MrCashondov2
   ```
2. Ejecuta el script de instalación automática:
   ```powershell
   setup.bat
   ```
   Esto instalará todas las dependencias necesarias en un entorno virtual y lanzará el instalador interactivo para tus datos personales.
3. El resto de la configuración ya está cifrada y lista para usarse.

## Distribución como ejecutable (.exe)
El bot puede distribuirse como ejecutable protegido usando PyInstaller + PyArmor. El usuario solo debe descargar el `.exe`, ejecutarlo, aceptar el EULA e ingresar sus datos personales cuando se le solicite.

## Soporte
Si tienes dudas o necesitas ayuda, contacta al soporte oficial de MrCashondoV2 o crea un Issue en GitHub.

**¡Disfruta de tu trading automatizado con MrCashondoV2!**

- 🔎 Escaneo periódico de todos los símbolos configurados (FOREX, metales, índices; acciones y cripto opcional)
- 📈 Generación de señales basada en indicadores técnicos (EMA, RSI, ATR, ADX, MACD, volumen, price action, patrones de velas, etc.)
- 🤖 Ejecución automática de operaciones en MT5 con control de riesgo (monto fijo en USD o porcentaje)
- 🗃️ Registro de todas las señales y operaciones en base de datos SQLite, incluyendo:
  - 🟢 Trades ejecutados (con actualización automática de estado: TP, SL, BE, trailing, abierto, etc.)
  - 🧬 Parámetros de generación de cada señal (para futuros estudios y machine learning)
- 📤 Exportación de toda la base de datos a CSV para análisis externo
- 📲 Alertas y reportes automáticos por Telegram
- 📝 Logs detallados por módulo para trazabilidad y debugging
- 🔒 Seguridad: credenciales cifradas y validadas, EULA obligatorio, código protegido en el instalador

## 🏗️ Arquitectura Modular y Estructura de Carpetas

```text
MrCashondo/
├── main.py                # Orquestador principal del bot
├── mt5_connector.py       # Conexión y ejecución de órdenes en MetaTrader 5
├── signal_generator.py    # Generación y filtrado de señales técnicas
├── risk_manager.py        # Cálculo de lotaje y control de riesgo
├── telegram_alerts.py     # Envío de alertas a Telegram
├── trade_database.py      # Registro y consulta de señales, trades y trades virtuales
├── configure_instruments.py # Configuración dinámica de instrumentos
├── export_tocsv.py        # Exporta todas las tablas de la base de datos a CSV
├── core/                  # Lógica modular (config, logger, instrument_manager)
├── alerts/                # Módulos de alertas
├── filters/               # Filtros técnicos
├── indicators/            # Indicadores técnicos (ej: macd.py)
├── scripts/               # Scripts auxiliares
├── tests/                 # Tests unitarios y de integración (pytest)
├── .env.enc / .env.key    # Credenciales cifradas (solo desarrollo: .env)
├── *.log                  # Logs detallados de cada módulo
├── requirements.txt       # Dependencias principales
├── requirements_installer.txt # Dependencias para el instalador protegido
```

## 🔄 Flujo End-to-End

1. 🛡️ **Validación de Suscripción y Seguridad:**
   - Al iniciar el bot, se solicita el correo y token de suscripción SOLO UNA VEZ por ejecución.
   - Se valida la suscripción vía Supabase (Stripe) y se verifica la integridad de los archivos críticos.
   - Si la suscripción es válida, el bot continúa; si no, se detiene y lo notifica.

2. ⚙️ **Inicialización de Componentes:**
   - Conexión a MetaTrader 5 (MT5) usando credenciales cifradas.
   - Inicialización de:
     - Generador de señales con análisis multitemporal (H4/H1 para contexto, M5 para entradas)
     - Filtros de volatilidad (ATR bajo en M5, spread máximo por activo) y de sesión (solo mercados activos, evita exposición overnight)
     - Sistema de blackout económico (evita operar durante noticias de alto impacto, configurable por CSV/API)
     - Gestor de riesgo avanzado (cálculo de lotaje, cooldown tras pérdidas, trailing stop, break even, parcialidades, RR dinámico, límites diarios)
     - Base de datos y sistema de post-trade review automático
     - Alertas de Telegram con contexto completo

3. 🔍 **Escaneo, Análisis y Ejecución:**
   - El bot escanea periódicamente todos los símbolos configurados (FOREX, metales, índices, acciones, ETFs).
   - Para cada símbolo:
     - Realiza análisis multitemporal y calcula mínimo 3 confluencias técnicas (tendencia macro, EMA, RSI, MACD, price action, volumen)
     - Aplica filtros de volatilidad y sesión; si hay blackout económico, descarta operar ese símbolo
     - Si la señal cumple criterios, ejecuta la operación en MT5 con control de riesgo y registra el trade
   - El estado de cada trade (real y virtual) se actualiza automáticamente según la evolución del precio (TP, SL, BE, trailing, abierto, etc.)
   - TODAS las señales (ejecutadas o no) se registran como "trades virtuales" para análisis de performance y machine learning.

4. 📢 **Alertas y Reportes:**
   - Envía alertas detalladas a Telegram con:
     - Confluencias activas, tendencia macro, hora y sesión, contexto del trade
     - Estado de ejecución, errores críticos y resumen diario

5. 🧪 **Post-Trade Review y Clasificación:**
   - Cada operación queda registrada con:
     - Hora, sesión, tendencia macro, confluencias activas, razón de entrada, clasificación (`alta_probabilidad`, `media`, `baja`, `emocional`)
     - Screenshot (si MT5 API lo permite) o string descriptivo
   - El sistema etiqueta automáticamente operaciones fuera de sesión o sin criterios completos como `emocional`.

6. 📊 **Exportación y Análisis:**
   - Exporta todas las tablas de la base de datos a CSV para análisis externo, backtesting o machine learning.
   - Permite análisis de performance, scoring de señales, optimización futura y auditoría de todas las señales generadas.

---

## 🛡️ Seguridad y Protección
- 🔑 El instalador .exe cifra los archivos críticos y credenciales.
- 🛡️ El código fuente está ofuscado y protegido contra ingeniería inversa (PyArmor).
- 🧩 **Diversificación**: FOREX + Metales + Índices + Acciones
- **Variables de entorno**: Nunca subas tu archivo `.env`, `.env.enc` ni `.env.key` a ningún repositorio ni los compartas.
- **EULA**: Debes aceptar el Acuerdo de Licencia antes de usar el bot.
- **Logs seguros**: No se registra información sensible.
- **Validación de entrada**: Todos los inputs son validados.
- **Límites de riesgo**: Múltiples capas de protección.

---

## 📋 Dependencias principales

- Python 3.10+
- MetaTrader5
- pyTelegramBotAPI
- python-dotenv
- pandas
- numpy
- schedule
- pytest
- black
- cryptography (solo si usas `.env.enc`)

## Instalación manual avanzada

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

**Scripts útiles**
- `run_bot.bat`: Ejecuta el bot con entorno virtual y chequeos previos.
- `run_tests.bat`: Ejecuta los tests con pytest.

## 📂 Estructura de archivos principal

Ver sección "Arquitectura Modular y Estructura de Carpetas" arriba para el detalle completo.

## ⚠️ Configuración de riesgo

El bot soporta dos modos de gestión de riesgo:

- `percent_margin`: Arriesga un % del balance/margen libre (modo clásico, por defecto)
- `fixed_usd`: Arriesga SIEMPRE el mismo monto en USD por operación (recomendado para cuentas pequeñas)

Configura esto en `risk_config.py`:
```python
RISK_MODE = "percent_margin"   # o "fixed_usd"
FIXED_RISK_USD = 1.0      # Cambia este valor al monto deseado en USD
MAX_RISK_PER_TRADE = 0.02 # 2% por operación (solo para percent_margin)
```
El cambio es inmediato y no requiere reiniciar el bot.
Para más detalles, consulta `README_risk_config.md`.

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
- Verifica que los símbolos pasen los filtros ATR, ADX, volumen y scoring.

**¿Cómo cambio el riesgo por operación?**
- Edita `risk_config.py` y ajusta `FIXED_RISK_USD` o cambia el modo a `percent_margin`.

**¿Puedo usarlo en cuenta real?**
- Sí, pero siempre prueba primero en demo. El trading conlleva riesgos.

**¿Cómo restauro la configuración de instrumentos?**
- Ejecuta `python configure_instruments.py` o edita el script para personalizar.

**¿Qué hago si tengo errores de conexión MT5?**
- Verifica credenciales y que MetaTrader 5 esté abierto y conectado.

**¿Por qué el bot entra en cooldown y no opera?**
- Si hay 2 pérdidas consecutivas, el sistema activa un cooldown temporal para proteger el capital.

**¿Cómo contribuyo?**
- Haz fork, crea una rama, realiza tus cambios y abre un Pull Request.

## 📝 Notas importantes

- **Nunca subas tu archivo `.env`, `.env.enc` ni credenciales a GitHub.**
- El bot está optimizado para Windows, pero puede adaptarse a Linux/Mac con cambios menores.
- Usa siempre entorno virtual para evitar conflictos de dependencias.

## 📈 Estrategias Implementadas

### Estrategia "Signal Flow Optimized" (SFO)
- **Validación progresiva**: Solo se requiere 1 condición técnica para generar señal.
- **Scoring flexible**: Señales con score ≥ 0.8 (score normalizado 0-1).
- **Validación multiframe**: Confirmación de tendencia en M15, entrada en M5.
- **Umbrales técnicos actualizados**:
  - ADX mínimo: 8
  - Spread máximo: 12
  - ATR mínimo: 0.001
  - SL: 1.25 × ATR
  - TP: 1.7 × ATR
  - Score de confianza mínimo: 0.8
  - Máximo 4 posiciones abiertas, 1 por símbolo
  - Riesgo por operación: 0.6% (ajustable)

#### Condiciones de Entrada BUY (actualizadas)
- Precio por encima de EMA 200 (M15)
- EMA 20 cruza hacia arriba la EMA 50 (M5)
- RSI (14) entre 50 y 70 con pendiente positiva
- MACD línea rápida cruzando sobre línea lenta por debajo de 0
- Volumen actual > promedio móvil de volumen (últimas 10 velas)
- Patrón de vela alcista (Engulfing, Marubozu o Pin Bar con mecha larga inferior)
- Vela de entrada debe cerrar por encima de EMA 20

#### Condiciones de Entrada SELL (actualizadas)
- Precio por debajo de EMA 200 (M15)
- EMA 20 cruza hacia abajo la EMA 50 (M5)
- RSI (14) entre 30 y 50 con pendiente negativa
- MACD línea rápida cruzando debajo de la lenta por encima de 0
- Volumen actual > promedio móvil de volumen (últimas 10 velas)
- Patrón de vela bajista (Engulfing, Marubozu o Pin Bar con mecha larga superior)
- Vela de entrada debe cerrar por debajo de EMA 20

#### Métricas de Éxito Proyectadas
- **Señales diarias**: 10-20 (según condiciones de mercado)
- **Win rate objetivo**: 65-70%
- **Profit factor**: 1.4-1.8
- **Máximo drawdown**: 12%
- **Ratio riesgo/recompensa**: 1:1.4

#### Monitoreo Diario
- **Generación de señales**: Mínimo esperado: 8, óptimo: 12-18, máximo: 25
- **Calidad de ejecución**: Slippage <0.0003, ejecución <2s, tasa de llenado >95%
- **Riesgo**: VAR diario <2%, correlación <0.3, exposición máxima <2.4%

## 🏗️ Arquitectura

Ver sección "Arquitectura Modular y Estructura de Carpetas" arriba para el detalle completo.

## ⚙️ Configuración de Instrumentos

Puedes configurar los tipos de instrumentos a analizar con el script interactivo:
```bash
python configure_instruments.py
```
Opciones disponibles:
1. FOREX + Índices + Metales (recomendada)
2. Solo FOREX
3. FOREX + Metales
4. FOREX + Índices
5. Todo habilitado
6. Configuración personalizada

**Nota:** Acciones individuales y ETFs están deshabilitados por defecto para reducir ruido. Criptomonedas requieren lógica aparte.

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
- **Indicadores técnicos**: Valores en tiempo real de EMA, RSI, ATR, ADX, MACD, volumen
- **Sin emojis**: Compatible con sistemas Windows
- **Timestamps precisos**: Seguimiento temporal de todas las decisiones

### Métricas Clave
- Win Rate (Tasa de éxito)
- Profit Factor
- Drawdown máximo
- Ratio SL vs TP alcanzado

## 🚨 Alertas Telegram

Ver sección "Alertas por Telegram" arriba para el formato y detalles.

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
3. **Filtros activos**: Revisa que los símbolos pasen los filtros ATR, ADX, volumen y scoring
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


## 📄 Licencia y EULA

Este proyecto está licenciado bajo la Licencia MIT.
El uso del bot requiere aceptar el Acuerdo de Licencia de Usuario Final (EULA), incluido en `EULA.txt`.
**Resumen EULA:**
- Uso estrictamente personal y no comercial
- Prohibida la distribución, ingeniería inversa, descompilación o modificación sin permiso expreso
- El software se provee "tal cual", sin garantías de ningún tipo
- El usuario es responsable de los resultados, riesgos y cumplimiento legal

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-feature`)
3. Commit tus cambios (`git commit -m 'Add nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

## 🛠️ Troubleshooting y FAQ ampliado

**¿Por qué el bot entra en cooldown y no opera?**
- Si hay 2 pérdidas consecutivas, el sistema activa un cooldown temporal para proteger el capital. Revisa los logs para ver cuándo se reactiva.

**¿Por qué no se generan señales?**
- Es normal si los filtros técnicos (EMA, RSI, MACD, volumen, price action) no se cumplen. El mercado puede estar en baja volatilidad o fuera de horario óptimo. Verifica que los símbolos pasen los filtros ATR, ADX, volumen y scoring.

**¿Cómo cambio el riesgo por operación?**
- Edita `risk_config.py` y ajusta `FIXED_RISK_USD` o cambia el modo a `percent_margin`. El cambio es inmediato y no requiere reiniciar el bot.

**¿Cómo restauro la configuración de instrumentos?**
- Ejecuta `python configure_instruments.py` o edita el script para personalizar. Por defecto, acciones individuales y ETFs están deshabilitados para reducir ruido. Criptomonedas requieren lógica aparte.

**¿Qué hago si tengo errores de conexión MT5?**
- Verifica credenciales y que MetaTrader 5 esté abierto y conectado. Consulta `mt5_connector.log` para detalles.

**¿Cómo contribuyo?**
- Haz fork, crea una rama, realiza tus cambios y abre un Pull Request.

**¿Cómo interpreto los logs?**
- Los logs detallan el estado de cada filtro, valores de indicadores y motivos de rechazo de señales. Úsalos para depurar y optimizar tu operativa.

**¿Cómo ejecuto los tests y valido el bot?**
- Usa `pytest test_bot.py -v` para validar la lógica y la integración. Se recomienda backtest mínimo de 3 meses en EURUSD, GBPUSD, XAUUSD, NAS100.

---

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