# INSTRUCCIONES PARA CREAR EL INSTALADOR PROTEGIDO DE MrCashondoV2

1. Instala los requisitos para el instalador:
   
   pip install -r requirements_installer.txt

2. Ejecuta el script de construcción:
   
   build_installer.bat

3. El instalador te pedirá los datos de MT5, Telegram y Supabase, y mostrará el EULA para aceptar.

4. El ejecutable final protegido estará en la carpeta dist\MrCashondoV2.exe

---

## Notas de seguridad
- El código fuente se ofusca con PyArmor.
- El instalador incluye el EULA y el archivo .env generado.
- No compartas el .exe ni el .env, es personal e intransferible.

---

## Para desarrolladores
- Si modificas el código, repite el proceso para generar un nuevo instalador.
- El EULA se puede editar en EULA.txt antes de empaquetar.
