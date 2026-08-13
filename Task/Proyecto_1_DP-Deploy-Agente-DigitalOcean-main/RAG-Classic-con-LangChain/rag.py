import os

#Paso 1: Elección de la Técnica de DocumentLoader
from langchain_community. document_loaders import PyPDFLoader

#Paso 2: Elección de Técnica de Splitting
from langchain_text_splitters import RecursiveCharacterTextSplitter #Mi técnica de Splitting

#Paso 3: Elección del Modelo de Word Embedding
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

#Importanciones para trabajar con SUPABASE
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client


if __name__ == '__main__':
    #=================================== Paso 1: Documment Loader =======================================
    path = "Base_de_Conocimientos/MANUAL DE TRÁMITES - Municipio de Girardota.pdf"
    loader = PyPDFLoader(path)
    documentos = loader.load()


    #============================= Paso 2: Document Splitting o Chunking ===========================================
    text_splitter =  RecursiveCharacterTextSplitter(
        chunk_size = 512, #1024
        chunk_overlap = 128,
    )
    chunks = text_splitter.split_documents(
        documents=documentos
    )


    #========== Paso 3: Embeddings - Cargamos el Modelo de Embeddings para convertir los Chunks ==========
    embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')


    #======================= Paso 4: VectorStore - Llevamos los Embeddings a Supabase ====================
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    client = create_client(supabase_url, supabase_key)

    vectorstore = SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        client=client,
        table_name="documents_langchain_asistente_de_informacion", #Esta es la tabla que creé
        query_name="match_documents_langchain_asistente_de_informacion",
    )