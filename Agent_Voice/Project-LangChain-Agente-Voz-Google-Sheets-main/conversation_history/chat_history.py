"""Histórico de conversación del agente de voz (PostgreSQL).

Son DOS piezas con funciones distintas, no una:

1. CHECKPOINTER — `get_checkpointer()`
   Es lo que hace que el agente RECUERDE. LangGraph guarda el estado de la
   conversación por `thread_id` y lo relee al inicio de cada turno, así que
   "¿y en Pinheiros?" entiende de qué venías hablando. Guarda las tablas
   `checkpoints*` en formato binario: NO está pensado para leerse con SQL.

2. LOG PLANO — `registrar_turno()` / `listar_conversacion()`
   Una fila por mensaje en la tabla `voice_chat_log`, legible con un SELECT.
   Para auditar en clase qué preguntó el usuario y qué respondió el agente.

Variables de entorno (.env): DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

Si faltan o la conexión falla, el módulo cae a memoria RAM (InMemorySaver) con
un aviso visible: el agente sigue recordando dentro de la sesión, pero nada se
persiste al reiniciar. Consulta `historial_persistente()` para saber en qué modo
estás corriendo.
"""

import atexit
import os
import uuid
from contextlib import ExitStack
from urllib.parse import quote_plus

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ==========================================================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS
# ==========================================================================
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

#quote_plus escapa caracteres especiales de la contraseña (@, /, :, #...)
#que si no romperían la URL de conexión.
#
#OJO con Supabase: usa el puerto 5432 (pooler en modo "session"). El 6543 es el
#modo "transaction", que no soporta prepared statements y hace fallar al
#checkpointer de LangGraph con errores de tipo DuplicatePreparedStatement.
DATABASE_URL = (
    f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if all([DB_USER, DB_PASSWORD, DB_HOST])
    else None
)

TABLA_LOG = "voice_chat_log"

_stack = ExitStack()
_checkpointer = None
_persistente = False


# ==========================================================================
# 2. SESIONES
# ==========================================================================
def nueva_sesion() -> str:
    """Genera un ID de sesión. Se usa como `thread_id` del agente."""
    return str(uuid.uuid4())


def validar_sesion(session_id: str) -> str:
    """Devuelve el session_id si es un UUID válido; si no, genera uno nuevo."""
    try:
        uuid.UUID(session_id)
        return session_id
    except (ValueError, AttributeError, TypeError):
        print(f"⚠️  Session ID inválido ({session_id!r}). Creando una sesión nueva...")
        return nueva_sesion()


# ==========================================================================
# 3. CHECKPOINTER (la memoria del agente)
# ==========================================================================
def get_checkpointer():
    """Devuelve el checkpointer que se le pasa a `create_agent(checkpointer=...)`.

    Singleton: la conexión se abre una sola vez y vive lo que dure el proceso.
    """
    global _checkpointer, _persistente
    if _checkpointer is not None:
        return _checkpointer

    if DATABASE_URL is None:
        _avisar_sin_persistencia(
            "Faltan variables en .env (requeridas: DB_USER, DB_PASSWORD, DB_HOST)."
        )
        return _checkpointer

    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        print(f"🔌 Conectando el histórico a {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        #from_conn_string es un context manager; lo mantenemos abierto durante
        #toda la vida del proceso y lo cerramos en cerrar()
        _checkpointer = _stack.enter_context(PostgresSaver.from_conn_string(DATABASE_URL))
        _checkpointer.setup()  #crea las tablas de checkpoints si no existen
        _crear_tabla_log()
        _persistente = True
        print("💾 Histórico persistente activo (PostgreSQL)")
    except Exception as e:
        _avisar_sin_persistencia(f"{type(e).__name__}: {e}")

    return _checkpointer


def _avisar_sin_persistencia(motivo: str) -> None:
    """Cae a memoria RAM, pero que se note."""
    global _checkpointer, _persistente
    from langgraph.checkpoint.memory import InMemorySaver

    print("=" * 70)
    print("⚠️  HISTÓRICO NO PERSISTENTE — usando memoria RAM")
    print(f"    Motivo: {motivo}")
    print("    El agente recuerda dentro de esta sesión, pero se pierde al salir.")
    print("=" * 70)
    _checkpointer = InMemorySaver()
    _persistente = False


def historial_persistente() -> bool:
    """True si el histórico se está guardando en PostgreSQL."""
    return _persistente


def cerrar() -> None:
    """Cierra la conexión del checkpointer. Llamar al terminar el programa."""
    global _checkpointer, _persistente
    _stack.close()
    _checkpointer = None
    _persistente = False


atexit.register(cerrar)


# ==========================================================================
# 4. LOG PLANO (legible con SQL)
# ==========================================================================
def _conexion():
    import psycopg

    return psycopg.connect(DATABASE_URL)


def _crear_tabla_log() -> None:
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA_LOG} (
                id          BIGSERIAL PRIMARY KEY,
                session_id  UUID        NOT NULL,
                rol         TEXT        NOT NULL,
                contenido   TEXT        NOT NULL,
                creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{TABLA_LOG}_sesion "
            f"ON {TABLA_LOG} (session_id, creado_en);"
        )
        conn.commit()


def registrar_turno(session_id: str, pregunta: str, respuesta: str) -> None:
    """Guarda un turno completo (lo que dijo el usuario + lo que respondió el agente).

    Es solo para auditoría: el agente NO lee de esta tabla, lee del checkpointer.
    Si falla, se avisa pero no se interrumpe la conversación.
    """
    if not _persistente:
        return
    try:
        with _conexion() as conn, conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO {TABLA_LOG} (session_id, rol, contenido) VALUES (%s, %s, %s)",
                [(session_id, "usuario", pregunta), (session_id, "agente", respuesta)],
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️  No se pudo guardar el turno en {TABLA_LOG}: {e}")


def listar_conversacion(session_id: str) -> list[tuple]:
    """Devuelve [(rol, contenido, creado_en), ...] de una sesión, en orden."""
    if not _persistente:
        return []
    with _conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT rol, contenido, creado_en FROM {TABLA_LOG} "
            f"WHERE session_id = %s ORDER BY creado_en, id",
            (session_id,),
        )
        return cur.fetchall()


# ==========================================================================
# 5. INSPECCIÓN MANUAL:  python conversation_history/chat_history.py <session_id>
# ==========================================================================
if __name__ == "__main__":
    import sys

    get_checkpointer()
    if len(sys.argv) > 1:
        for rol, contenido, creado_en in listar_conversacion(sys.argv[1]):
            print(f"[{creado_en:%Y-%m-%d %H:%M:%S}] {rol:>7}: {contenido}")
    else:
        print("Uso: python conversation_history/chat_history.py <session_id>")
    cerrar()
