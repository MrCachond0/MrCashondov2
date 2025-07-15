# build_installer.bat
REM Script para automatizar la creación del instalador protegido (.exe) de MrCashondoV2
REM 1. Ejecuta el script de configuración interactiva para crear el .env
REM 2. Ofusca el código fuente con PyArmor
REM 3. Empaqueta el bot con PyInstaller
REM 4. Incluye el EULA y el .env en el dist
REM 5. Limpia archivos temporales

@echo off
setlocal

REM Paso 1: Configuración interactiva (el usuario final ingresará sus datos en la primera ejecución)
REM python setup_installer.py
REM if errorlevel 1 exit /b %errorlevel%



REM Paso 2: Empaquetar con PyInstaller (sin ofuscación)
pyinstaller --onefile --name MrCashondoV2 --add-data ".env;." --add-data "EULA.txt;." --add-data "first_run_setup.py;." main.py
if errorlevel 1 exit /b %errorlevel%





echo Instalador .exe generado en la carpeta dist\
endlocal
