# DP-LangChain-Introduccion

Notebooks de introducción a **LangChain v1** del programa AI Engineer de DataPath.

Autor: Ing. Kevin Inofuente Colque — DataPath

## Contenido

| Notebook | Tema |
|---|---|
| `01_aula_Models_Accesando_a_Modelos_de_Lenguaje.ipynb` | Acceso a modelos de lenguaje (OpenAI, Gemini) |
| `02_aula_Models_Conceptos_avanzados_de_Models.ipynb` | Conceptos avanzados de Models |
| `03_aula_Prompt_Templates.ipynb` | Prompt Templates |
| `04_aula_Output Parsers.ipynb` | Output Parsers |
| `05_aula_Agentes.ipynb` | Agentes con `create_agent` |

`Comandos.md` incluye cómo añadir el MCP de la documentación de LangChain a Claude Code.

## Instalación

**1. Crear y activar el entorno virtual:**

```bash
conda create -n LangChain-Introduccion python=3.11
conda activate LangChain-Introduccion
```

**2. Instalar dependencias:**

```bash
pip install -r requirements.txt
```

**3. Configurar las claves de API:**

```bash
cp .env.example .env
```

Rellena `OPENAI_API_KEY` y `GOOGLE_API_KEY`. El `.env` está en `.gitignore`
y no debe subirse nunca al repositorio.
