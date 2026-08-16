"""
RAG pipeline for CommandCheck.

Builds a Chroma vector store from the markdown knowledge base in
knowledge_base/commandcheck/ on first run, then reuses it on
subsequent runs. This is genuine retrieval: documents are chunked,
embedded with a real sentence-transformer model, stored in a vector
index, and queried by cosine similarity at request time.
"""

import os
from pathlib import Path
from functools import lru_cache

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

from utils.llm import get_embeddings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = BASE_DIR / "knowledge_base" / "commandcheck"
PERSIST_DIR = BASE_DIR / "vectorstore" / "commandcheck_chroma"


def _load_documents():
    docs = []
    for md_file in sorted(KB_DIR.glob("*.md")):
        loader = TextLoader(str(md_file), encoding="utf-8")
        docs.extend(loader.load())
    return docs


def _build_vectorstore():
    docs = _load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        separators=["\n## ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)

    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=str(PERSIST_DIR),
        collection_name="commandcheck_docs",
    )
    return vs


@lru_cache(maxsize=1)
def get_vectorstore():
    """Load existing Chroma index if present, otherwise build it once."""
    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        return Chroma(
            persist_directory=str(PERSIST_DIR),
            embedding_function=get_embeddings(),
            collection_name="commandcheck_docs",
        )
    return _build_vectorstore()


def retrieve_docs(query: str, k: int = 4):
    """
    Returns top-k relevant documentation chunks for a given command/query,
    each with its source file so the agent can cite where guidance came from.
    """
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    return [
        {
            "source": Path(doc.metadata.get("source", "unknown")).name,
            "content": doc.page_content,
        }
        for doc in results
    ]
