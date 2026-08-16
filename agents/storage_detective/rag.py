"""
RAG pipeline for Storage Detective.

Same pattern as CommandCheck's RAG: real chunking + embedding + vector
retrieval, over the storage-locations knowledge base, so the agent's
"safe to clean?" judgment is grounded in retrieved reference text
rather than an LLM guessing from parametric memory alone.
"""

from pathlib import Path
from functools import lru_cache

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

from utils.llm import get_embeddings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = BASE_DIR / "knowledge_base" / "storage_detective"
PERSIST_DIR = BASE_DIR / "vectorstore" / "storage_chroma"


def _load_documents():
    docs = []
    for md_file in sorted(KB_DIR.glob("*.md")):
        loader = TextLoader(str(md_file), encoding="utf-8")
        docs.extend(loader.load())
    return docs


def _build_vectorstore():
    docs = _load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)

    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=str(PERSIST_DIR),
        collection_name="storage_docs",
    )
    return vs


@lru_cache(maxsize=1)
def get_vectorstore():
    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        return Chroma(
            persist_directory=str(PERSIST_DIR),
            embedding_function=get_embeddings(),
            collection_name="storage_docs",
        )
    return _build_vectorstore()


def retrieve_docs(query: str, k: int = 3):
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    return [
        {
            "source": Path(doc.metadata.get("source", "unknown")).name,
            "content": doc.page_content,
        }
        for doc in results
    ]
