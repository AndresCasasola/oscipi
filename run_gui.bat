@echo off
setlocal
echo [1/3] Checking for Python environment...

:: 1. Crea un entorno virtual si no existe para no ensuciar el Python global
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: 2. Activa el entorno e instala/actualiza dependencias
echo [2/3] Syncing dependencies...
call venv\Scripts\activate
pip install -q -r requirements.txt

:: 3. Ejecuta la aplicación
echo [3/3] Launching Oscilloscope...
python gui/main_ui.py

pause