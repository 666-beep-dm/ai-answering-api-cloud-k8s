#!/usr/bin/env python3
"""
Ingest documents into the FAISS vector store.
Usage:
  python scripts/ingest.py --source docs/
  python scripts/ingest.py --source my_file.pdf
"""
import argparse
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from src.config import get_settings


def ingest(source: str) -> None:
    s = get_settings()
    print(f"Loading documents from: {source}")

    loader = DirectoryLoader(source, loader_cls=TextLoader, glob="**/*.txt")
    raw_docs = loader.load()
    print(f"Loaded {len(raw_docs)} raw documents")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"Split into {len(chunks)} chunks")

    embeddings = OpenAIEmbeddings(
        model=s.embedding_model, openai_api_key=s.openai_api_key
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("data/faiss_index")
    print(f"✅ Index saved to data/faiss_index  ({len(chunks)} vectors)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="docs/", help="Source dir/file")
    args = parser.parse_args()
    ingest(args.source)
