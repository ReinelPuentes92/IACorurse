## Opción A: Con Conda

### Crea un Entorno Virtual con Python 3.11
conda create --name LangChain python=3.11

### Activa el Entorno Virtual
conda activate LangChain

### Instalación de dependencias
pip install -r requirements.txt


## Opción B: Con venv (Windows / PowerShell, sin Conda)

### Crea el Entorno Virtual
python -m venv venv

### Activa el Entorno Virtual
.\venv\Scripts\Activate.ps1

Si PowerShell bloquea el script por política de ejecución, corre esto una vez (solo para la sesión actual):
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

### Instalación de dependencias
pip install -r requirements.txt

### Desactivar el Entorno Virtual
deactivate


## Configurar variables de entorno

### Copia el archivo de ejemplo
Copy-Item .env.example .env

Luego edita `.env` y rellena las variables necesarias según el agente que vayas a ejecutar (ver comentarios dentro de `.env.example`).


## Ejecutar un agente

python Agente-Basico-A\agente_basico.py