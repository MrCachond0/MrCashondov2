# build_installer.bat
REM Script para automatizar la creación del instalador protegido (.exe) de MrCashondoV2
REM 1. Ejecuta el script de configuración interactiva para crear el .env
REM 2. Ofusca el código fuente con PyArmor
REM 3. Empaqueta el bot con PyInstaller
REM 4. Incluye el EULA y el .env en el dist
REM 5. Limpia archivos temporales

@echo off
setlocal

REM Paso 1: Configuración interactiva
python setup_installer.py
if errorlevel 1 exit /b %errorlevel%

REM Paso 2: Ofuscar código fuente
if not exist dist (mkdir dist)
if exist dist\obf (rmdir /s /q dist\obf)
pyarmor obfuscate --output dist\obf main.py mt5_connector.py signal_generator.py risk_manager.py telegram_alerts.py trade_database.py subscription_api.py
if errorlevel 1 exit /b %errorlevel%

REM Paso 3: Empaquetar con PyInstaller
pyinstaller --onefile --name MrCashondoV2 --add-data ".env;." --add-data "EULA.txt;." --add-data "dist\obf;obf" dist\obf\main.py
if errorlevel 1 exit /b %errorlevel%

REM Paso 4: Copiar EULA y .env al dist final
copy /Y .env dist\
copy /Y EULA.txt dist\

REM Paso 5: Limpieza
rmdir /s /q dist\obf
rd /s /q build
if exist MrCashondoV2.spec del MrCashondoV2.spec

echo Instalador .exe generado en la carpeta dist\
endlocal
