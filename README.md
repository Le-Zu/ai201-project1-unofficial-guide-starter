# The Unofficial Guide — Project 1

An AI-powered RAG (Retrieval-Augmented Generation) assistant that makes student-generated knowledge about computer science professors and courses at Hunter College easily searchable and answerable, grounded in actual Rate My Professors ratings and reviews.

---

## Getting Started

### 1. Create a virtual environment
```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment
```bash
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Configure your `GROQ_API_KEY` in a `.env` file:
```bash
cp .env.example .env
```

### 5. Run the application
```bash
python3 app.py
```

---

## Domain

The domain is **Computer Science undergraduate professors and course reviews at Hunter College (CUNY)**. 

Official college resources (like the department faculty directory) only provide email addresses, office locations, and research publications. They offer zero insight into what classes are actually like. Real student survival knowledge—such as course workload (e.g., 20+ hours a week for Operating Systems), whether coding projects are auto-graded with strict style checkers, whether exams are curved, and whether quizzes are pop quizzes—is only found in informal student networks (like Reddit or Rate My Professors). 

This system aggregates this unofficial student knowledge to help students make informed scheduling decisions.

---

## Document Sources

We scraped actual student reviews for 10 undergraduate CS instructors at Hunter College using the Rate My Professors GraphQL API, saved as plain text files in the [documents/](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/) directory:

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Eric Schweitzer | RMP Profile | [eric_schweitzer.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/eric_schweitzer.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/257192) |
| 2 | Tiziana Ligorio | RMP Profile | [tiziana_ligorio.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/tiziana_ligorio.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/815879) |
| 3 | Melissa Lynch | RMP Profile | [melissa_lynch.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/melissa_lynch.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/2505090) |
| 4 | Saad Mneimneh | RMP Profile | [saad_mneimneh.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/saad_mneimneh.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/926045) |
| 5 | Susan Epstein | RMP Profile | [susan_epstein.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/susan_epstein.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/192300) |
| 6 | Pavel Shostak | RMP Profile | [pavel_shostak.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/pavel_shostak.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/1823870) |
| 7 | Mike Zamansky | RMP Profile | [mike_zamansky.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/mike_zamansky.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/2212256) |
| 8 | Katherine St. John | RMP Profile | [katherine_st_john.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/katherine_st_john.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/2324096) |
| 9 | Stewart Weiss | RMP Profile | [stewart_weiss.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/stewart_weiss.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/192304) |
| 10 | Ioannis Stamos | RMP Profile | [ioannis_stamos.txt](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/documents/ioannis_stamos.txt) / [RMP Link](https://www.ratemyprofessors.com/professor/64427) |

---

## Chunking Strategy

### Strategy Description
Rather than using a mechanical character-based sliding window, we implemented a **custom, review-based chunking strategy**:
1. Split each document using the review separator `---`.
2. Parse and store the first chunk as the professor's overall profile header (containing overall quality score, department info, etc.).
3. Parse each subsequent part as an individual student review chunk.
4. Programmatically prepend `"Professor: [Professor Name]\n"` to the top of every review chunk.

**Chunk size:** Review-based dynamic splitting (typically 100–350 characters per review block)  
**Overlap:** None  

**Why these choices fit the documents:**
* **Why character-based chunking fails:** A sliding window of 400 characters frequently cuts a student's review comment in half. This separates the professor's name (located at the top of the file) from the review comment (located at the bottom), causing the embedding model to lose the semantic connection.
* **Why review-based chunking is better:** Each student review represents a complete, self-contained thought. By splitting on `---` and prepending the professor's name to each chunk, we guarantee that the professor's identity is mathematically bound to every single review comment. This dramatically increases retrieval accuracy when querying specific professors.

**Final chunk count:** 244 chunks across 10 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via the `sentence-transformers` library (384-dimensional dense vectors).

**Production tradeoff reflection:**
If deploying this system to a production environment with thousands of users and documents, we would consider the following tradeoffs:
1. **Cost:** `all-MiniLM-L6-v2` runs locally and is 100% free with zero API call costs. However, it consumes server memory and CPU/GPU. In contrast, cloud APIs (like OpenAI's `text-embedding-3-small`) cost money per token but shift the computational scaling burden off our servers.
2. **Context Length:** `all-MiniLM-L6-v2` has a sequence limit of 256 tokens. While perfect for short student reviews, it would fail to embed entire course syllabi or long academic guides. A production deployment would benefit from models with larger context lengths (e.g., `text-embedding-3-small` with 8191 tokens).
3. **Multilingual Support:** The local model has poor multilingual alignment. If students write reviews in multiple languages (e.g., Japanese, Chinese, English), a multilingual model like `multilingual-e5-base` would be required to perform semantic search across languages.
4. **Latency vs. Throughput:** Local inference has zero network latency, making it extremely fast. However, scaling to handle thousands of concurrent search requests requires deploying and managing a cluster of inference containers, whereas cloud APIs scale automatically.

---

## Retrieval and Query Normalization

To make search highly resilient to variations in student behavior, we implemented two key enhancements in [retriever.py](file:///home/lezu/Projects/codepath/ai201/ai201-project1-unofficial-guide-starter/retriever.py):

1. **Course Code Preprocessing & Normalization:** 
   Students frequently search using shorthand course codes such as `CS 150`, `cs150`, or `CS-150` instead of the formal prefix `CSCI 150` used in official records. We added a regular expression preprocessor that intercepts queries matching these patterns and normalizes them to a search expansion format (e.g., `CSCI150 CSCI 150`), matching both spaced and spaceless course code formats.
2. **Dynamic Retrieval Expansion:**
   Standard queries retrieve a default top-k (`N_RESULTS = 4`). However, course-wide queries (e.g., *"Which professors teach CSCI 150?"*) or comparison queries require scanning across reviews of multiple distinct professors. When a course-wide query is detected, the system dynamically scales the retrieval limit (`n_results`) to `15` to capture reviews across all matching documents.
3. **Statistical & Comparison Query Injection:**
   Comparison queries (e.g., *"Which professor has the lowest 'Would take again' score?"* or *"Who is the easiest professor?"*) require data from all professors' profiles to draw accurate conclusions. When a comparison keyword is identified, the retriever automatically loads the overall statistics header chunks for all 10 professors and appends them to the context. This allows the LLM to perform complete, accurate comparisons.

---

## Grounded Generation

**System prompt grounding instruction:**
```
You are a student assistant for the Hunter College Computer Science department.
Your task is to answer the user's question about computer science professors and courses using ONLY the provided reviews and details in the Context.

Strict Rules:
1. Grounding: Answer the question using ONLY the provided Context. Do NOT use any general training knowledge or assume anything not written in the Context.
2. If the Context does not contain enough information to answer the question, or if the question is about professors/subjects not listed in the Context, you MUST state exactly: "I don't have enough information in my document database to answer this question."
3. Formatting: Cite the professor names, course numbers (e.g. CSCI 127), and dates or tags mentioned in the Context where relevant so the user knows where the information came from.
4. Keep the response factual, concise, and direct. Do not make up any facts, ratings, or details.
```

**How source attribution is surfaced in the response:**
To programmatically guarantee source attribution, we set the LLM temperature to `0.0` to prevent hallucination, and we write a Python metadata parser. The parser extracts the unique professor names from the verified retrieved chunks and appends actual clickable local markdown file links (pointing to their text documents under `documents/`) at the bottom of the response message.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Why do students recommend to "take the test out" for Katherine St. John's CSCI 127 class? | Because they feel her class is outdated, lectures are a mess, she cannot communicate properly, and she flags/reports majority of the class for cheating or AI use. | A student recommends to "take the test out" because they think Katherine St. John's material is outdated, the lectures are a mess, and she can't communicate properly. | Relevant | Accurate |
| 2 | What are the rules regarding the final exam in Katherine St. John's courses? | In her elective course CS39542, if you fail the final exam, you fail the course. | Comments suggest that in her elective CS39542, failing the final exam results in failing the course. | Relevant | Accurate |
| 3 | How does Saad Mneimneh curve grades in his classes? | For STAT 319, grades are curved using the square root ($\sqrt{x}$) method. For CSCI 705, he applies a generous curve and allows students below a B to do extra work for a B+. For CSCI 150, he offers curves and extra credit in recitation. | In CSCI 705, he curves generously and allows extra work. In STAT 319, he uses the "√ method". In CSCI 150, he offers generous curves and extra credit in recitation. | Relevant | Accurate |
| 4 | Why was a student flagged for cheating by Katherine St. John on a homework they missed? | The student missed the homework because they were trying to beat the "Demon of Hatred" in the game Sekiro all day, and St. John flagged them for cheating anyway. | A student was flagged for cheating on a missed homework because they missed the deadline due to trying to beat the "Demon of Hatred" in Sekiro all day, and she flagged them anyway. | Relevant | Accurate |
| 5 | What kind of questions make up a large portion of Stewart Weiss's exams and quizzes? | Tricky true or false questions make up 30% of exams and 90% of quizzes in CSCI 340. | True or false questions make up a large portion of his exams (30 percent) and quizzes (90 percent) in CSCI 340. | Relevant | Accurate |
| 6 | Which professors teach CSCI 150 according to the reviews? | Based on the loaded reviews, CSCI 150 has been taught by Ioannis Stamos, Saad Mneimneh, Eric Schweitzer, and Susan Epstein. | The reviews indicate that CSCI 150 is taught by Ioannis Stamos, Saad Mneimneh, Eric Schweitzer, and Susan Epstein. | Relevant | Accurate |
| 7 | Which professor has the lowest "Would take again" score? | Susan Epstein has the lowest "Would Take Again" score at 15.1%. | Susan Epstein has the lowest "Would Take Again" score at 15.1%. | Relevant | Accurate |

---

## Failure Case Analysis

### Question that failed
`Who is recommended to take for CSCI 127 according to students?`

### What the system returned
`I don't have enough information in my document database to answer this question.`

### Root cause (tied to a specific pipeline stage)
This is an **information bottleneck / data coverage failure** in our database stage. The actual scraped reviews for CSCI 127 across our database are highly critical (e.g. complaining about St. John's strict AI policies, Tiziana Ligorio's slide-heavy lectures, or Melissa Lynch's poor communication). Because there are no positive recommendations in the data for CSCI 127, the retriever returned the closest semantic matches (which were all critical reviews). The generator, adhering to the strict grounding instructions, correctly refused to provide a recommendation since the retrieved context did not mention one.

### What you would change to fix it
We could add positive student comments to the text database if they exist. Alternatively, we could modify the prompt instructions to allow the system to synthesize a balanced summary indicating that *no* professor is highly recommended and explain that students suggest "taking the test out" instead. Additionally, layout a pros/cons list for each professor if the student were to take each professor that also highlights the percentage that student review say would retake the class.

---

## Spec Reflection

**One way the spec helped during implementation:**
Writing `planning.md` forced us to define a clear, testable set of 5 evaluation questions with expected answers, which allowed us to identify that our initial sliding-window chunker was completely failing to retrieve specific review data because names and reviews were split.

**One way the implementation diverged from the spec, and why:**
We originally planned a standard character-based sliding window (400 characters, 80 overlap). We diverged during implementation to a custom review-based splitter using the `---` delimiter because the character-based sliding window split reviews in a way that cut off the professor's name from their review comment, leaving the embedding model unable to associate reviews with the correct professor.

---

## AI Usage

### Instance 1

*   *What I gave the AI:* We gave the AI our 10 professor names, and asked it to write a python script `scrape_rmp.py` that queries the Rate My Professors GraphQL endpoint using requests.
*   *What it produced:* A baseline Python script that queries the GraphQL endpoint but would fail if a professor's full name had slight formatting variations or if the school ID was not resolved.
*   *What I changed or overrode:* We added a robust search fallback mechanism that queries the school ID `U2Nob29sLTIyNg==` (Hunter College), parses last name matching to resolve first-name variations, and formats the output into clean, structured text documents with `---` separators, which enabled our review-based chunking.

### Instance 2

*   *What I gave the AI:* We gave the AI our citation layout requirements and asked it to format citations inside the LLM prompt.
*   *What it produced:* A prompt format asking the LLM to write out source files.
*   *What I changed or overrode:* We realized this could lead to hallucinated links. We overrode the AI's approach by writing a Python metadata parser inside `generator.py` that programmatically extracts unique professor names from the verified retrieved chunks, sanitizes their filenames (e.g. handling dots in names like St. John), and appends actual markdown links pointing directly to the files on disk.
