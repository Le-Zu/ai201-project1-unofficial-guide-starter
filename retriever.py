import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL, N_RESULTS

# Embedding function and ChromaDB client are initialized once at module load.
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def get_collection():
    """Return the ChromaDB collection. Used by app.py during ingestion."""
    return _collection


def embed_and_store(chunks):
    """
    Embed a list of chunks and store them in the vector database with professor metadata.
    """
    _collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[{"professor": c["professor"]} for c in chunks],
        ids=[c["chunk_id"] for c in chunks],
    )
    print(f"Stored {_collection.count()} total chunks in the vector database.")


def retrieve(query, n_results=N_RESULTS):
    """
    Find the most relevant professor review chunks for a user's question.

    Use _collection.query() to run a semantic search. It takes:
      - query_texts : a list containing your query string
      - n_results   : how many results to return
      - include     : what to return — use ["documents", "metadatas", "distances"]

    Return a list of dicts, each with:
      - "text"      : the chunk text
      - "professor" : the professor name (pull this from metadatas)
      - "distance"  : the similarity score (lower = more similar for cosine)
    """
    if _collection.count() == 0:
        return []

    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    retrieved_chunks = []
    if results and "documents" in results and results["documents"]:
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for text, meta, dist in zip(documents, metadatas, distances):
            retrieved_chunks.append({
                "text": text,
                "professor": meta.get("professor", "Unknown"),
                "distance": dist
            })

    return retrieved_chunks
