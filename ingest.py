import os
from config import DOCS_PATH


def load_documents():
    """Load all .txt professor profile documents from the docs folder."""
    documents = []
    for filename in sorted(os.listdir(DOCS_PATH)):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCS_PATH, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            professor_name = filename.replace(".txt", "").replace("_", " ").title()
            documents.append({
                "professor": professor_name,
                "filename": filename,
                "text": text,
            })
    print(f"Loaded {len(documents)} professor profile(s): {[d['professor'] for d in documents]}")
    return documents


def chunk_document(text, professor_name):
    """
    Split a professor profile document into chunks based on reviews.

    Deliberate Strategy:
      - Split the document by the '---' review separator.
      - The first part is the professor's overall statistics header.
      - The subsequent parts are individual student reviews.
      - Prepend "Professor: [Name]\n" to each review to ensure the semantic context
        (who the review is about) is preserved in every vector representation.
    """
    raw_chunks = text.split("---")
    chunks = []
    prefix = professor_name.lower().replace(" ", "_")
    counter = 0

    # Ingest the overall profile header as the first chunk
    header_text = raw_chunks[0].strip()
    if len(header_text) > 50:
        chunks.append({
            "text": header_text,
            "professor": professor_name,
            "chunk_id": f"{prefix}_{counter}"
        })
        counter += 1

    # Ingest each individual student review
    for raw_chunk in raw_chunks[1:]:
        review_text = raw_chunk.strip()
        if len(review_text) > 50:
            # Prepend the professor name to guarantee search grounding
            full_chunk_text = f"Professor: {professor_name}\n{review_text}"
            chunks.append({
                "text": full_chunk_text,
                "professor": professor_name,
                "chunk_id": f"{prefix}_{counter}"
            })
            counter += 1

    return chunks
