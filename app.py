import gradio as gr
from ingest import load_documents, chunk_document
from retriever import embed_and_store, retrieve, get_collection
from generator import generate_response


# ---------------------------------------------------------------------------
# Ingestion — runs once on startup
# ---------------------------------------------------------------------------

def run_ingestion():
    """
    Load professor review documents, chunk them, and store in ChromaDB.

    If the vector store is already populated, ingestion is skipped.
    To re-ingest (e.g. after changing your chunking strategy), delete the
    ./chroma_db folder and restart the app.
    """
    collection = get_collection()

    if collection.count() > 0:
        print(f"Vector store already populated ({collection.count()} chunks). Skipping ingestion.")
        print("To re-ingest, delete the ./chroma_db folder and restart.")
        return

    print("Ingesting Hunter CS professor documents...")
    documents = load_documents()
    all_chunks = []

    for doc in documents:
        chunks = chunk_document(doc["text"], doc["professor"])
        all_chunks.extend(chunks)

    if all_chunks:
        embed_and_store(all_chunks)
        print(f"Ingestion complete. {len(all_chunks)} chunks stored.")
    else:
        print(
            "\n⚠️  No chunks produced. Make sure chunk_document() is implemented in ingest.py.\n"
            "    The Guide will start, but won't be able to answer questions yet.\n"
        )


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------

def chat(message, history):
    if not message.strip():
        return ""
    retrieved = retrieve(message)
    return generate_response(message, retrieved)


# ---------------------------------------------------------------------------
# Gradio UI & Theme Styling
# ---------------------------------------------------------------------------

CSS_STYLE = """
.header-container {
    background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%);
    padding: 2.2rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(109, 40, 217, 0.15);
    margin-bottom: 1.5rem;
    text-align: center;
}
.header-title {
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    margin: 0 !important;
}
.header-subtitle {
    color: #ddd6fe !important;
    font-size: 1rem !important;
    margin: 0.5rem 0 0 !important;
    font-weight: 400 !important;
}
.sidebar-panel {
    background: #fdfdfd !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 1.2rem !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
}
.sidebar-title {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #5b21b6 !important;
    margin: 0 0 0.75rem 0 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    border-bottom: 2px solid #ddd6fe;
    padding-bottom: 0.35rem;
}
.prof-item {
    font-size: 0.9rem !important;
    color: #1f2937 !important;
    line-height: 1.8 !important;
    font-weight: 500 !important;
}
"""

is_gradio_6 = gr.__version__.startswith("6")

blocks_kwargs = {
    "title": "Hunter CS Unofficial Guide"
}
launch_kwargs = {}

if is_gradio_6:
    launch_kwargs["theme"] = gr.themes.Soft(primary_hue="violet", secondary_hue="indigo")
    launch_kwargs["css"] = CSS_STYLE
else:
    blocks_kwargs["theme"] = gr.themes.Soft(primary_hue="violet", secondary_hue="indigo")
    blocks_kwargs["css"] = CSS_STYLE

with gr.Blocks(**blocks_kwargs) as demo:

    gr.HTML("""
        <div class="header-container">
            <h1 class="header-title">🎓 The Unofficial Guide</h1>
            <p class="header-subtitle">
                Hunter College Computer Science Professor Assistant — Grounded in Real Student Reviews & Data
            </p>
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=chat,
                chatbot=gr.Chatbot(
                    height=440,
                    placeholder=(
                        "<div style='text-align:center; color:#9ca3af; margin-top:3rem;'>"
                        "<h3>Ask a question about a Hunter CS professor or course workload!</h3>"
                        "<p style='font-size:0.9rem; color:#9ca3af;'>e.g., 'What is CSCI 235 like with Stewart Weiss?'</p>"
                        "</div>"
                    ),
                ),
                textbox=gr.Textbox(
                    placeholder='e.g., "Who is the best professor for Algorithms (CSCI 250)?"',
                    container=False,
                    scale=7,
                ),
                examples=[
                    "Who is recommended to take for CSCI 127?",
                    "What is the workload like for CSCI 235 with Stewart Weiss?",
                    "Are Eric Schweitzer's quizzes in CSCI 150 open book?",
                    "Who teaches Algorithms (CSCI 250) and how are the exams?",
                    "Tell me about Mike Zamansky's teaching style.",
                    "Is Operating Systems with Stewart Weiss hard?",
                    "What do students say about Melissa Lynch?",
                    "What classes does Ioannis Stamos teach?",
                ],
                cache_examples=False,
            )

        with gr.Column(scale=1, min_width=220):
            gr.HTML("""
                <div class="sidebar-panel">
                    <p class="sidebar-title">📚 Loaded CS Professors</p>
                    <div style="max-height: 350px; overflow-y: auto;">
                        <ul style="list-style:none; padding:0; margin:0;">
                            <li class="prof-item">Eric Schweitzer</li>
                            <li class="prof-item">Tiziana Ligorio</li>
                            <li class="prof-item">Melissa Lynch</li>
                            <li class="prof-item">Saad Mneimneh</li>
                            <li class="prof-item">Susan Epstein</li>
                            <li class="prof-item">Pavel Shostak</li>
                            <li class="prof-item">Mike Zamansky</li>
                            <li class="prof-item">Katherine St. John</li>
                            <li class="prof-item">Stewart Weiss</li>
                            <li class="prof-item">Ioannis Stamos</li>
                        </ul>
                    </div>
                    <hr style="border:none; border-top:1px solid #e5e7eb; margin:1rem 0;">
                    <p style="font-size:0.75rem; color:#6b7280; margin:0; line-height:1.5;">
                        All answers are grounded in student reviews, including grading rigor, class difficulty, and exam expectations.
                    </p>
                </div>
            """)


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  The Unofficial Guide (Hunter CS) — starting up")
    print("="*50 + "\n")
    run_ingestion()
    demo.launch(**launch_kwargs)
