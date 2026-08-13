-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- 1. Crear la tabla para almacenar tus documentos
-- Esta tabla usa los nombres de tu script de Python.
create table documents_langchain_asistente_de_informacion (
  -- ⚠️ El `default gen_random_uuid()` es OBLIGATORIO:
  -- SupabaseVectorStore.from_documents() NO envía la columna `id`, así que la base
  -- de datos tiene que generarla. Sin el default falla con:
  --   null value in column "id" ... violates not-null constraint  (código 23502)
  id uuid primary key default gen_random_uuid(),
  content text,
  metadata jsonb,
  -- El embedding es de 1536 dimensiones porque usas el modelo 'text-embedding-ada-002' de OpenAI
  embedding vector (1536) 
);

-- 2. Crear la función para buscar documentos por similitud
-- Esta función también usa el nombre personalizado de tu script.
create or replace function match_documents_langchain_asistente_de_informacion (
  query_embedding vector(1536),
  match_count int,
  filter jsonb
) returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents_langchain_asistente_de_informacion.embedding <=> query_embedding) as similarity
  from documents_langchain_asistente_de_informacion
  where metadata @> filter
  order by documents_langchain_asistente_de_informacion.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- ============================================================================
-- 3. ¿YA CREASTE LA TABLA SIN EL DEFAULT?
-- ============================================================================
-- Si la tabla ya existe y rag.py falla con el error 23502 ("null value in
-- column id"), no hace falta borrarla ni perder datos. Basta con agregarle
-- el default y volver a ejecutar rag.py:

alter table documents_langchain_asistente_de_informacion
  alter column id set default gen_random_uuid();