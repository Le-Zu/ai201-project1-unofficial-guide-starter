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


def retrieve(query, n_results=None):
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

    # Preprocess query to handle CS/CSCI course codes (e.g. CS 150 -> CSCI150 CSCI 150)
    import re
    normalized_query = re.sub(
        r'\b(cs|csci)\s*[-]?\s*(\d{3})\b',
        lambda m: f"CSCI{m.group(2)} CSCI {m.group(2)}",
        query,
        flags=re.IGNORECASE
    )

    # Determine n_results dynamically to handle course-wide queries
    if n_results is None:
        is_course_query = (
            re.search(r'CSCI\d{3}', normalized_query, re.IGNORECASE) or
            any(w in normalized_query.lower() for w in ["who teaches", "which professors", "what professors", "who teach", "list professors"])
        )
        n_results = 15 if is_course_query else N_RESULTS

    results = _collection.query(
        query_texts=[normalized_query],
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

    # Detect comparison/statistical/overall rating queries and load all professor stats headers
    comparison_keywords = [
        "would take again", "would-take-again", "retake", "lowest score", "highest score",
        "lowest rating", "highest rating", "overall quality", "easiest", "hardest",
        "most difficult", "least difficult", "compare ratings", "lowest would take again",
        "highest would take again", "best professor", "worst professor", "overall ratings",
        "take again"
    ]
    is_comparison = any(kw in normalized_query.lower() for kw in comparison_keywords)
    if is_comparison:
        # Load overall profile headers (the _0 chunks) for all 10 professors
        professors = [
            'Katherine St John', 'Eric Schweitzer', 'Susan Epstein', 'Ioannis Stamos',
            'Mike Zamansky', 'Saad Mneimneh', 'Pavel Shostak', 'Stewart Weiss',
            'Tiziana Ligorio', 'Melissa Lynch'
        ]
        header_ids = [f"{p.lower().replace(' ', '_')}_0" for p in professors]
        try:
            headers = _collection.get(ids=header_ids, include=["documents", "metadatas"])
            if headers and "documents" in headers and headers["documents"]:
                existing_texts = {c["text"].strip() for c in retrieved_chunks}
                for doc, meta in zip(headers["documents"], headers["metadatas"]):
                    cleaned_doc = doc.strip()
                    if cleaned_doc not in existing_texts:
                        retrieved_chunks.append({
                            "text": doc,
                            "professor": meta.get("professor", "Unknown"),
                            "distance": 0.0 # Force similarity to be perfect to bypass filters
                        })
        except Exception as e:
            print(f"Error fetching comparison headers: {e}")

    return retrieved_chunks
