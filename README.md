# ZentroMart VoiceOps Agent

A grounded, voice-enabled customer support agent for the fictional Indian online store **ZentroMart**, built for the **VoiceOps 2026** capstone (LLM & Generative AI Course, Consulting & Analytics Club, IIT Guwahati × Gnani.ai).

A customer speaks a question. The agent listens (Gnani STT), answers from ZentroMart's policy documents and order data (LLM + RAG + tools), and replies out loud (Gnani TTS).

```
Customer audio → Gnani STT → [ Agent: LLM + RAG + tools ] → Gnani TTS → Spoken reply
```

Repository: https://github.com/mithilg25/VoiceOps

---

## Results on the practice set

| Evaluation | Score | Notes |
|---|---|---|
| Baseline (ungrounded, estimated) | 23.1% (12/52) | Retrieval bug meant the model received irrelevant context, so it effectively guessed |
| Step 2: RAG, text questions | 69.2% (36/52) | Answers grounded in retrieved `[SECTION-ID]` chunks |
| Step 3: conversations | 60.9% (14/23) | Multi-turn, tools, verification, handover |
| Step 4: ASR text | 57.7% (30/52) | Simulated speech-to-text transcripts (`asr_text` column), not Gnani STT output |

The grader is a string-matching check (`must_include` / `must_not_include`). See `report.pdf` for the full analysis.

---

## Quick start

```bash
git clone https://github.com/mithilg25/VoiceOps.git
cd VoiceOps
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                  # Windows: copy .env.example .env
# edit .env: add your API keys and set DATASET_DIR (see below)
python run.py --audio_dir path/to/audio_files --out_dir sample_outputs
```

The first run builds the retrieval index automatically (this downloads the embedding model, so it takes a minute or two). Later runs reuse it.

---

## Setup

### 1. Requirements

- Python 3.10 or newer
- A Groq API key (or any OpenAI-compatible LLM endpoint)
- A Gnani API key from https://app.gnani.ai/voice (one key covers both STT and TTS)
- The capstone dataset (see step 4)

### 2. Install

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### 3. Configure `.env`

Open `.env` and fill in your keys. Never commit this file.

```env
# Dataset path (optional: leave blank if data/, kb/, practice/ and tools/ are in the project root)
DATASET_DIR=

# LLM
OPENAI_API_KEY=your-groq-or-openai-key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Voice
GNANI_API_KEY=your-gnani-key
```

| Variable | Purpose |
|---|---|
| `DATASET_DIR` | Folder containing the extracted dataset (`data/`, `kb/`, `practice/`, `tools/`). Blank means the project root |
| `OPENAI_API_KEY` | Key for the LLM provider (the variable name is OpenAI-style, but the value can be a Groq key) |
| `OPENAI_BASE_URL` | Provider endpoint. Leave empty for OpenAI itself |
| `LLM_MODEL` | Model used for answers and tool calling |
| `EMBED_MODEL` | Sentence-transformers model used for retrieval |
| `GNANI_API_KEY` | Used by Gnani STT and TTS |

### 4. Point the agent at the dataset

The capstone dataset is **not** part of this repository (the submission rules forbid including a copy). Download `Capstone_Project_Dataset_FTTT_2026.zip` from the organizers and extract it. Then do either of these:

**Option A: use `DATASET_DIR` (recommended).** Set it to the extracted folder, which must contain `data/`, `kb/`, `practice/` and `tools/`:

```env
DATASET_DIR=/path/to/Capstone_Project_Dataset_FTTT_2026
```

On Windows, use forward slashes or a raw path, for example `DATASET_DIR=C:/Users/you/Downloads/Capstone_Project_Dataset_FTTT_2026`.

**Option B: copy the folders into the project root.** Copy `data/`, `kb/`, `practice/` and `tools/` next to `run.py` and leave `DATASET_DIR` blank. They are git-ignored.

Optional: check the dataset is intact with the validator that ships inside the dataset folder:

```bash
python /path/to/Capstone_Project_Dataset_FTTT_2026/validate_dataset.py
```

### 5. Retrieval index

The index is built **automatically the first time the agent starts**, from `kb/*.md` in your dataset folder, and saved to `src/rag_index/` (git-ignored). To rebuild it by hand, for example after changing `EMBED_MODEL`:

```bash
python scripts/build_index.py
```

If the first run says the index is missing or empty, check that `DATASET_DIR` points at a folder that contains `kb/`.

---

## How to run

### Ask one question (text)

```bash
python run.py --text "How long does a card refund take?"
```

Prints the reply and the section IDs the answer used.

### Interactive demo (used for the video)

A continuous chat loop that keeps conversation state across turns:

```bash
python demo_chat.py
```

Type `quit` to exit.

### Batch run on a folder of audio (the organizers' command)

```bash
python run.py --audio_dir path/to/audio_files --out_dir sample_outputs
```

Optional: `--lang en-IN` (default) sets the language code for STT and TTS, for example `hi-IN` for Hindi.

Supported input formats: `.wav`, `.mp3`, `.m4a`, `.flac`. Keep each clip under **60 seconds** (the Gnani STT limit).

For each audio file the run saves:

```
sample_outputs/
├── results.json              # per file: transcript, reply, reply audio path, retrieved sections
└── audio/
    ├── <name>.reply.wav      # spoken reply
    └── <name>.reply.txt      # reply text
```

Each file is handled by a fresh agent, so clips are independent. Tool calls are logged to `sample_outputs/tool_log.jsonl`.

### Evaluate on the practice set

```bash
python scripts/evaluate.py --mode question   # 52 text questions
python scripts/evaluate.py --mode asr        # 52 ASR-noise variants
python scripts/evaluate.py --mode conv       # 23 conversations (96 turns)
python scripts/evaluate.py --mode all        # everything
```

The practice files are read from `DATASET_DIR/practice/`. Per-item results are written to `sample_outputs/` (`eval_questions.csv`, `eval_asr.csv`, `eval_conversations.json`), including the retrieved section IDs. A conversation counts as correct only when **every** turn passes. Free API tiers rate-limit, so a full run takes several minutes.

---

## How it works: the four steps

### Step 1: Answer a question with an LLM

`src/llm.py` wraps the chat-completions API (OpenAI-compatible, so Groq works with only a base-URL change). `src/agent.py` gives the model a system prompt that makes it ZentroMart's support assistant: its role, its limits, and a first reply that says it is an AI assistant. With no documents, the model guesses at policies, which is why this step gives the weakest score.

### Step 2: Ground it in the documents (RAG)

- **Chunking** (`scripts/build_index.py`): each Markdown file in `kb/` is split on its `## [SECTION-ID]` headings into 84 chunks. Every chunk keeps its section ID, document type, status and `effective_from` date.
- **Embeddings**: chunks are embedded with `paraphrase-multilingual-MiniLM-L12-v2`, chosen so Hindi and Hinglish queries still match English policies.
- **Retrieval** (`src/rag.py`): cosine similarity, then a precedence adjustment so current policy outranks agent guides, help pages, FAQs and marketing, and superseded documents (such as `pol_returns_v3_superseded.md`) are penalized. The top 6 chunks go to the model.
- **Grounded answering**: the prompt tells the model to answer only from the retrieved text or tool results, and to say it does not know and offer a human when the documents do not cover the question.
- **Source tracking**: the section IDs used are returned with every reply and saved in the outputs.

### Step 3: Hold a conversation

- **Memory**: the message history is sent each turn, so follow-ups like "how long will that take?" refer to the same order.
- **Tools** (`src/agent.py`, `src/tools_wrapper.py`, `src/data.py`):
  - `lookup_order`: fetches an order, only after the caller is verified
  - `create_ticket`: records a handover with a short summary
  - `add_business_days` / `business_days_between`: date maths (Monday to Saturday, skipping dates in `holidays.csv`; today is fixed at 20 October 2026)
  - product, catalogue and pincode lookups from the CSVs
- **Identity verification**: before order details are shown, the caller must give the order ID and either the last four digits of the phone number or the delivery pincode. The dispatcher allows at most one retry, then refuses to share order details.
- **Handover**: the system prompt instructs the agent to create a ticket and hand over to a human when the customer asks for one, mentions legal action, has 2 or more contacts in 7 days, or reports a damage claim above ₹10,000. It must not say a ticket exists unless the tool returned `created=True`.
- **Refusals**: requests that break policy, such as instant compensation, are declined politely and routed to a human.

### Step 4: Give it a voice

`src/voice.py` wraps Gnani's official SDK (`gnani-vachana`):

- **STT**: transcribes the customer audio (`en-IN` accepts English mixed with Hindi).
- **Unclear audio**: an empty transcript produces "Sorry, I didn't catch that. Could you say it again?" instead of calling the agent.
- **TTS**: replies are spoken with the `timbre-v2.5` model and the `Kaveri` voice. The model is always named because the SDK's older default is no longer served.
- **Written for the ear**: the voice-mode prompt asks for short replies with spoken dates, and `speechify()` groups 8-digit order IDs into blocks of four (for example "6952 0867") so they are read clearly.

Only Gnani is used for speech. No other STT or TTS service is called, even as a fallback.

---

## Project structure

```
.
├── README.md
├── .env.example            # variable names only, no keys
├── .gitignore
├── requirements.txt
├── run.py                  # text query, or batch run on a folder of audio
├── demo_chat.py            # interactive text CLI for the demo video
├── report.pdf              # short report
├── demo.mp4                # demo video (max 2 minutes)
├── src/
│   ├── config.py           # environment variables, DATASET_DIR, TODAY = 2026-10-20
│   ├── llm.py              # LLM client, retries on rate limits
│   ├── rag.py              # retrieval with precedence handling, builds the index if missing
│   ├── agent.py            # conversation loop, tools, verification, handover
│   ├── tools_wrapper.py    # adapter for the dataset's lookup_order / create_ticket
│   ├── data.py             # CSV lookups and business-day maths
│   ├── voice.py            # Gnani STT / TTS, speechify()
│   └── rag_index/          # generated on first run (git-ignored)
├── scripts/
│   ├── build_index.py      # chunk + embed the knowledge base
│   └── evaluate.py         # scores questions, ASR variants, conversations
└── sample_outputs/         # example evaluation and batch-run outputs

# Not in the repository (they come from the dataset ZIP via DATASET_DIR):
data/  kb/  practice/  tools/  validate_dataset.py
```

---

## Known limitations

- The grader is string-matching, so correct answers worded differently can fail. Dates should always include the full year (for example "27 October 2026").
- In conversations, `create_ticket` was sometimes called without the `order_id` from earlier turns. The planned fix is to fill it from verified conversation state in the dispatcher.
- Spelled-out SKUs in noisy transcripts (for example "ele zero zero one") are not always mapped to the right product. A fuzzy-matching layer is planned.
- The 23.1% baseline came from a run with a retrieval bug and is only an approximation of a prompt-only run.
- Verification, escalation and the "I don't know" rule are mostly enforced through the system prompt. Only the one-retry limit is enforced in code.
- The dataset's `create_ticket` tool writes to `tools/tickets_created.csv` inside the dataset folder, so test runs add rows there.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `KeyError: 'OPENAI_API_KEY'` | `.env` is missing or not in the project root |
| `FileNotFoundError` for `data/`, `kb/` or `practice/` | Set `DATASET_DIR` in `.env` to the extracted dataset folder, or copy the folders into the project root |
| `ModuleNotFoundError: tools` | `DATASET_DIR` must contain the dataset's `tools/` folder |
| "Vector index not found" on every run | The automatic build failed, usually because `kb/` was not found. Fix `DATASET_DIR`, then run `python scripts/build_index.py` |
| Retrieval returns nothing or old results | Delete `src/rag_index/` and run again, or run `python scripts/build_index.py` |
| HTTP 429 from the LLM | Free-tier rate limit. The wrapper waits 15 seconds and retries. Run one mode at a time |
| Gnani TTS returns a model error | Make sure the model is named explicitly (`timbre-v2.5` or `timbre-v3.0`) |
| STT returns an empty transcript | Check the clip is under 60 seconds and not silent; the agent will ask the caller to repeat |

---

## Rules followed

- Gnani APIs are used for all speech-to-text and text-to-speech.
- Only the synthetic ZentroMart data is used; no real customer data or recordings.
- Answers come from the agent reading the documents. No policy answers are hardcoded.
- API keys live in `.env`, which is git-ignored. `.env.example` contains no secrets.