# A 11 de Mayo del 2026, el comando para instalar el MCP de la Documentación de LangChain es:
claude mcp add --transport http docs-langchain https://docs.langchain.com/mcp --scope user

Scope: local (default)
Alcance: Solo el proyecto actual, solo tu usuario
Dónde se guarda: ~/.claude.json → bajo la ruta del proyecto

Scope: project
Alcance: Compartido con el equipo vía repo
Dónde se guarda: .mcp.json en la raíz del proyecto (commiteado a git)

Scope: user
Alcance: Todos tus proyectos, solo tu usuario
Dónde se guarda: ~/.claude.json → sección user