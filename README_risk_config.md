# Configuración de riesgo en USD para Mr. Cashondo

Este archivo documenta cómo modificar el monto fijo en USD a arriesgar por operación.

## ¿Cómo funciona?
- El bot puede operar en dos modos de gestión de riesgo:
  - `percent_margin`: arriesga un porcentaje del balance o margen libre (modo clásico)
  - `fixed_usd`: arriesga SIEMPRE el mismo monto en USD por operación (recomendado para cuentas pequeñas o control absoluto)

## ¿Dónde se configura?
Edita el archivo `risk_config.py` en la raíz del proyecto:

```
RISK_MODE = "fixed_usd"   # o "percent_margin"
FIXED_RISK_USD = 1.0       # Cambia este valor al monto deseado en USD
```

- Si usas `fixed_usd`, el bot calculará el volumen para que la pérdida máxima (si se ejecuta el SL) sea exactamente ese monto.
- Si el volumen calculado es menor al mínimo permitido por el broker, el bot ajustará al mínimo y lo notificará en el log.

## Ejemplo de uso

1. Para arriesgar siempre 2 USD por operación:
   - Abre `risk_config.py`
   - Cambia:
     ```
     RISK_MODE = "fixed_usd"
     FIXED_RISK_USD = 2.0
     ```
2. Para volver al modo clásico (1% del balance):
   - Cambia:
     ```
     RISK_MODE = "percent_margin"
     ```

## Notas
- El cambio es inmediato, no requiere reiniciar el bot.
- El archivo `risk_config.py` es seguro de editar y no afecta otros módulos.
- Si tienes dudas, revisa los logs para ver qué modo está activo y cuánto se arriesga por operación.
