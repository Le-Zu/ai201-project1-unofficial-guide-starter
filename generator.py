from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, GEMINI_API_KEY

_groq_client = None
if GROQ_API_KEY:
    _groq_client = Groq(api_key=GROQ_API_KEY)

_gemini_client = None
if GEMINI_API_KEY:
    from google import genai
    _gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are a student assistant for the Hunter College Computer Science department.
Your task is to answer the user's question about computer science professors and courses using ONLY the provided reviews and details in the Context.

Strict Rules:
1. Grounding: Answer the question using ONLY the provided Context. Do NOT use any general training knowledge or assume anything not written in the Context.
2. If the Context does not contain enough information to answer the question, or if the question is about professors/subjects not listed in the Context, you MUST state exactly: "I don't have enough information in my document database to answer this question."
3. Formatting: Cite the professor names, course numbers (e.g. CSCI 127), and dates or tags mentioned in the Context where relevant so the user knows where the information came from.
4. Keep the response factual, concise, and direct. Do not make up any facts, ratings, or details.
"""


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved professor review chunks.

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"      : the chunk text
      - "professor" : the professor name
      - "distance"  : similarity score

    Your response will:
      1. Answer using only the retrieved context — not the model's general knowledge
      2. Programmatically cite and link to the source documents
      3. Say so clearly when the answer isn't in the loaded documents
    """
    if not GROQ_API_KEY and not GEMINI_API_KEY:
        return (
            "⚠️ Neither `GROQ_API_KEY` nor `GEMINI_API_KEY` is set in your `.env` file.\n\n"
            "Please obtain one of the following:\n"
            "1. **Groq API Key (Free):** Get it at [console.groq.com](https://console.groq.com) and add `GROQ_API_KEY=your_key` to `.env`.\n"
            "2. **Google Gemini API Key (Free):** Get it at [aistudio.google.com](https://aistudio.google.com) and add `GEMINI_API_KEY=your_key` to `.env`."
        )

    if not retrieved_chunks:
        return "I don't have enough information in my document database to answer this question."

    # Filter out extremely weak matches (distance > 0.65 in cosine space)
    valid_chunks = [c for c in retrieved_chunks if c["distance"] < 0.65]

    if not valid_chunks:
        return "I don't have enough information in my document database to answer this question."

    # Build context string
    context_parts = []
    for i, chunk in enumerate(valid_chunks):
        context_parts.append(
            f"--- Source Chunk {i+1} ({chunk['professor']}) ---\n"
            f"Text:\n{chunk['text']}"
        )
    context_text = "\n\n".join(context_parts)

    answer = None
    errors = []

    # Use Gemini if key is set
    if GEMINI_API_KEY and _gemini_client:
        try:
            from google.genai import types
            response = _gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Context:\n{context_text}\n\nQuestion: {query}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                )
            )
            answer = response.text.strip()
        except Exception as e:
            errors.append(f"Gemini API error: {str(e)}")

    # Use Groq if Gemini is not set or failed, and Groq key is set
    if not answer and GROQ_API_KEY and _groq_client:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
            ]
            response = _groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.0,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg or "Access denied" in err_msg:
                errors.append(
                    f"Groq API error: Access denied (403). Cloudflare blocked the request.\n\n"
                    f"👉 **Troubleshooting:** Try disabling your VPN or changing your network connection (e.g. to a mobile hotspot).\n\n"
                    f"👉 **Workaround:** You can bypass Groq by using Google Gemini instead! "
                    f"Get a free API key at [aistudio.google.com](https://aistudio.google.com), "
                    f"add `GEMINI_API_KEY=your_key` to your `.env` file, and restart the app."
                )
            else:
                errors.append(f"Groq API error: {err_msg}")

    if not answer:
        return "Error communicating with LLM:\n\n" + "\n\n".join(errors)

    # Determine if it's a refusal
    refusal_phrases = [
        "don't have enough information",
        "do not have enough information",
        "no information",
        "not mentioned in the context",
        "cannot be answered",
        "not listed in the context"
    ]
    is_refusal = any(phrase in answer.lower() for phrase in refusal_phrases)

    if is_refusal:
        return answer
    else:
        # Programmatically append sources
        sources = sorted(list(set(c["professor"] for c in valid_chunks)))
        if sources:
            source_links = ", ".join(f"[{s}](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/{s.lower().replace('.', '').replace(' ', '_')}.txt)" for s in sources)
            return f"{answer}\n\n**Sources:** {source_links}"
        else:
            return answer
