# Cambios recientes (julio 2025)

## Mejoras automáticas implementadas
1. **Endurecimiento de score/confianza y filtros de señales:**
   - El score mínimo y la confianza requerida para ejecutar señales se han incrementado (confianza >= 0.85, R:R >= 2.2).
   - El cálculo de score ahora penaliza más el spread y premia señales de mayor calidad.
   - Solo se consideran señales con ADX >= 28 (tendencia clara) y volumen actual > 1.5x la media de 20 velas.
   - Se exige un ATR mínimo absoluto de 0.0015 y confirmación de breakout (ruptura de máximos/mínimos previos).
   - Solo se permite operar en zonas institucionales validadas por el módulo context_analyzer.
   - Solo se opera en la sesión de Londres y Nueva York (07:00-17:00 UTC), bloqueando 30 minutos antes y después de noticias económicas relevantes.
   - Se exigen al menos 4 confluencias técnicas (patrón de vela, EMA, RSI, volumen, nivel clave, etc.).
   - El trailing stop y break-even solo se activan tras movimientos >1.2x ATR a favor.

# 🚀 MrCashondoV2 - ¡Tu Trading Automatizado, Inteligente y Sin Límites! 💸🤖
¡Bienvenido a la revolución del trading automático! MrCashondoV2 es el bot que te permite operar en FOREX, metales e índices de manera profesional, sin que tengas que mover un dedo. Recibe señales, ejecuta operaciones y gestiona tu riesgo como un verdadero pro, ¡todo mientras disfrutas de tu tiempo libre! 🏖️📈

---
## Sistema de señales de trading (actualizado julio 2025)

El sistema genera señales solo si se cumplen criterios estrictos de momentum, contexto institucional, horario y volatilidad:
- **ADX**: Solo se consideran señales con ADX >= 28 (tendencia clara).
- **Volumen**: Se requiere impulso, validado por tick_volume > 1.5x la media de 20 velas.
- **Breakout**: Confirmación de ruptura de máximos/mínimos previos.
- **ATR**: El ATR mínimo absoluto es 0.0015 (mercados sin volatilidad quedan descartados).
- **Contexto institucional**: Solo se permite operar en zonas validadas por el módulo context_analyzer (soporte/resistencia institucional, liquidez reciente).
- **Horario**: Solo se opera en la sesión de Londres y Nueva York (07:00-17:00 UTC). Se bloquean operaciones 30 minutos antes y después de noticias económicas relevantes.
- **Confluencias**: Se exigen al menos 4 confluencias técnicas (patrón de vela, EMA, RSI, volumen, nivel clave, etc.).
- **Scoring/confianza**: Solo se aceptan señales con confianza >= 0.85 y R:R >= 2.2.
- **Gestión activa**: El trailing stop y break-even solo se activan tras movimientos >1.2x ATR a favor.

Estas reglas buscan evitar entradas débiles, operar solo en condiciones óptimas y reducir drawdown.
# Cambios recientes (julio 2025)

## Mejoras automáticas implementadas

1. **Endurecimiento de score/confianza:**
   - El score mínimo y la confianza requerida para ejecutar señales se han incrementado.
   - El cálculo de score ahora penaliza más el spread y premia señales de mayor calidad.
2. **ATR mínimo y filtro de spread:**
   - Se exige un ATR mínimo absoluto y un ratio ATR/spread más alto para filtrar mercados de baja volatilidad o con spread alto.
   - El filtro de spread es más estricto.

3. **Gestión activa de posiciones:**
   - Ahora el bot ejecuta gestión activa (trailing stop y cierre parcial) en tiempo real desde el ciclo principal.
4. **Icono personalizado en el instalador:**
   - El archivo ejecutable `.exe` generado incluye el icono personalizado `capturabot.ico` para una experiencia visual profesional.


# 🚀 MrCashondoV2 - ¡Tu Trading Automatizado, Inteligente y Sin Límites! 💸🤖

¡Bienvenido a la revolución del trading automático! MrCashondoV2 es el bot que te permite operar en FOREX, metales e índices de manera profesional, sin que tengas que mover un dedo. Recibe señales, ejecuta operaciones y gestiona tu riesgo como un verdadero pro, ¡todo mientras disfrutas de tu tiempo libre! 🏖️📈

---

## ✨ ¿Por qué elegir MrCashondoV2?

- 🔥 **Resultados 24/7**: Opera los mercados más grandes del mundo, incluso mientras duermes.
- 🤖 **Estrategia Avanzada**: Algoritmo SFO con validación multiframe, filtros técnicos y gestión de riesgo profesional.
- 🛡️ **Seguridad Total**: Tus credenciales están cifradas y protegidas. Solo tú tienes acceso a tus datos personales.
- 📲 **Alertas en Telegram**: Recibe notificaciones en tiempo real de cada operación y señal relevante.
- 🔄 **Auto-Update**: ¡Siempre tendrás la última versión, mejoras y nuevas funciones sin mover un dedo!
- 🏆 **Membresía Exclusiva**: Acceso solo para miembros, con soporte dedicado y comunidad privada.

---


## 🚀 Instalación para Usuarios Finales
1. **Recibe el instalador** (`MrCashondoV2.exe`) directamente del equipo de soporte al adquirir tu suscripción. Este archivo es personal e intransferible.
2. **Ejecuta** el archivo `.exe` (doble clic). El instalador te guiará paso a paso e incluirá el EULA que deberás aceptar.
3. Ingresa solo tus datos personales:
   - 📲 Chat ID de Telegram
   - 🔑 Credenciales de MetaTrader 5 (login, password, servidor)
   - 📧 Email y token de suscripción
   *(¡El resto ya está cifrado y protegido!)*
4. Una vez instalado, simplemente ejecuta el acceso directo creado en tu escritorio para comenzar a operar.

> **Nota:** No es necesario descargar nada desde GitHub ni ejecutar archivos `.bat`. Todo lo necesario está incluido en el instalador `.exe` que recibirás tras tu suscripción.

---

## 🔄 ¿Cómo funciona el Auto-Update?

- Cada vez que inicies el bot, este buscará automáticamente la última versión en el repositorio oficial de GitHub.
- Si hay una actualización, ¡la descarga y la aplica solo! Siempre tendrás las mejores estrategias, parches y seguridad sin preocuparte por nada.

---

## 🖥️ Requisitos
- Windows 10/11
- MetaTrader 5 instalado
- Python 3.10+ (solo para desarrollo o ejecución directa)
- Cuenta activa y membresía válida

---

## 💬 Soporte y Comunidad
¿Tienes dudas o necesitas ayuda? ¡No estás solo! Contacta al soporte oficial de MrCashondoV2 o únete a nuestra comunidad exclusiva para miembros.

---

## ⚠️ Disclaimer Legal

**El uso de MrCashondoV2 es bajo tu absoluta y exclusiva responsabilidad.**

- Ni el desarrollador, ni los colaboradores, ni ningún tercero relacionado con este software se hacen responsables, bajo ninguna circunstancia, de las decisiones de inversión, ganancias, pérdidas, resultados financieros, ni de las obligaciones fiscales o tributarias derivadas del uso de este bot.
- El trading en mercados financieros conlleva riesgos significativos. Antes de operar con dinero real, asegúrate de comprender los riesgos y, si es necesario, consulta con un asesor financiero profesional.
- Al instalar y usar MrCashondoV2, aceptas que TODO el riesgo y la responsabilidad recaen únicamente sobre ti como usuario final.

---

**¡Únete a la nueva era del trading automatizado y lleva tu operativa al siguiente nivel con MrCashondoV2! 🚀💰**
