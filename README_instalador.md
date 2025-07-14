# INSTRUCCIONES PARA CREAR EL INSTALADOR PROTEGIDO DE MrCashondoV2

1. Instala los requisitos para el instalador:
   ```bash
   pip install -r requirements_installer.txt
   ```

2. Ejecuta el script de construcción:
   ```bash
   build_installer.bat
   ```

3. El instalador te pedirá los datos de MT5, Telegram y Supabase, y mostrará el EULA para aceptar.

4. El ejecutable final protegido estará en la carpeta `dist\MrCashondoV2.exe`.

---

## Notas de seguridad
- El código fuente se ofusca automáticamente con PyArmor.
- El instalador incluye el EULA y el archivo `.env.enc` generado (cifrado).
- **No compartas el ejecutable ni el archivo de entorno (.env, .env.enc, .env.key): son personales e intransferibles.**
- El EULA debe ser aceptado por el usuario final antes de usar el bot.

---

## Para desarrolladores
- Si modificas el código, repite el proceso para generar un nuevo instalador.
- El EULA se puede editar en `EULA.txt` antes de empaquetar.
- Elimina archivos temporales y credenciales antes de distribuir cualquier build.
