# ZentroMart VoiceOps Agent

Grounded customer-support agent for the fictional Indian retailer ZentroMart.
Built for the VoiceOps 2026 capstone (IIT Guwahati C&A × Gnani.ai).

## Setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` (Fill in your OpenAI and Gnani API keys)
4. Extract the capstone dataset (`data/`, `kb/`, `practice/`, `tools/`) into the root directory.
5. `python scripts/build_index.py` (Builds the RAG vector index)

## Run
**Single Query:**
`python run.py --text "How long does a card refund take?"`

**Batch Evaluation (Text):**
`python scripts/evaluate.py --mode all`

**Batch Evaluation (Audio):**
`python run.py --audio_dir path/to/audio_files --out_dir sample_outputs`

## Architecture
- **Step 1/2:** RAG pipeline chunks `kb/*.md` by `[SECTION-ID]`, embeds with `sentence-transformers`, and retrieves based on precedence.
- **Step 3:** Tool-calling agent (`src/agent.py`). Dynamic verification (max 1 retry), tool calls for business-day math (`add_business_days`), and human escalation.
- **Step 4:** Gnani STT/TTS wrapped in `src/voice.py`.
- **No hardcoded policies:** The LLM extracts timelines from retrieved docs and uses Python tools strictly for date math and database lookups.