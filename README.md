# AI Customer Support Agent — Hiver SDE Intern Take-Home

An AI customer support agent that classifies intents, drafts grounded replies using historical resolutions, and decides whether to auto-handle or escalate — built for one brand from the Twitter customer support dataset.

**Focus**: Evaluation rigor, not architectural sophistication.

## Architecture

```
Customer Message
       │
       ▼
┌──────────────┐
│    Intent     │  LLM-based classifier with taxonomy
│   Classifier  │  derived from brand's actual data
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Retrieval   │  Sentence-transformer embeddings
│    Engine     │  + cosine similarity over resolved threads
└──────┬───────┘
       │  top-k historical examples
       ▼
┌──────────────┐
│     Reply     │  Grounded in retrieved evidence
│   Generator   │  Anti-hallucination prompt design
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Escalation   │  Rule-based + confidence thresholds
│    Policy     │  Conservative: prefer false-escalation
└──────────────┘   over false-auto-handle
```

## Dataset Setup

1. Download from [Kaggle](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
2. Place the CSV at:

```
data/raw/twcs.csv
```

You can also use the Kaggle CLI:

```bash
pip install kaggle
kaggle datasets download -d thoughtvector/customer-support-on-twitter
# Extract and place twcs.csv in data/raw/
```

## Environment Setup

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Copy the example and fill in your API key:

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

Required:
- `OPENAI_API_KEY` — Your OpenAI API key (or compatible API)

Optional:
- `OPENAI_MODEL` — Model to use (default: `gpt-4o-mini`)
- `OPENAI_BASE_URL` — Override for compatible APIs (Azure, local, etc.)

## Run Pipeline

### Full pipeline (recommended first run)

```bash
python -m src.run_pipeline
```

### Step by step

```bash
# 1. Profile the dataset
python -m src.profile_dataset

# 2. Select the best brand
python -m src.select_brand

# 3. Reconstruct conversation threads
python -m src.build_threads

# 4. Discover intent taxonomy
python -m src.discover_intents

# 5. Create golden evaluation set
python -m src.create_golden_set

# 6. Run trivial baseline
python -m src.baseline_majority

# 7. Run TF-IDF baseline
python -m src.baseline_tfidf

# 8. Build retrieval index
python -m src.retrieve_examples

# 9. Run full evaluation (intent + escalation + reply quality)
python -m src.evaluate

# 10. Generate human agreement template
python -m src.human_judge_agreement
```

### Use the agent directly

```bash
python -m src.agent --message "I was charged twice for my order"
python -m src.agent --message "Someone hacked my account" --json
```

## Reproduce Headline Results

After placing `data/raw/twcs.csv` and setting your `.env`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
python -m src.run_pipeline
```

This runs all phases and produces all evaluation artifacts. Expected time: ~10-15 minutes (depends on API call speed and whether sentence-transformer model needs downloading).

## Results

> Populated after running the evaluation pipeline. See `reports/evaluation.md` for full results.

Key metrics are saved to:
- `reports/results.json` — Machine-readable results
- `reports/evaluation.md` — Human-readable evaluation report
- `reports/tables/baseline_majority.json` — Trivial baseline
- `reports/tables/tfidf_results.json` — ML baseline
- `reports/figures/confusion_matrix.png` — Intent confusion matrix

## Baselines

| Baseline | What it does | Why it exists |
|----------|-------------|---------------|
| **Majority class** | Always predicts most common intent; always auto-handles | Shows the floor — if we can't beat this, nothing works |
| **TF-IDF + LR/SVC** | TF-IDF features → Logistic Regression or LinearSVC | Shows what simple ML achieves — the LLM must beat this |

## Tests

```bash
.venv\Scripts\python -m pytest tests/ -q
```

## Failure Analysis

See `REPORT.md` § 9 for top 5 failure modes with real examples from evaluation.

## Limitations

1. **Auto-labeled golden set**: Labels from clustering need human review. Some "errors" may be label noise.
2. **Single brand**: Findings may not generalize to other brands/industries.
3. **Tweet-length messages**: Real support interactions may be longer and more complex.
4. **No production safeguards**: No rate limiting, no PII detection, no content filtering.
5. **LLM judge not yet human-validated**: Judge reliability is pending human review completion.

## How I'd Explain This Project in an Interview

**Architecture**: "I built a retrieval-augmented support agent: classify the customer's intent, retrieve similar resolved conversations as evidence, generate a grounded reply, and decide whether to auto-handle or escalate. The key architectural choice was making escalation rule-based rather than LLM-based — it's the safety-critical decision, so it needs to be transparent and auditable."

**Key design decision**: "I derived intents from the brand's actual data via clustering rather than using an off-the-shelf taxonomy. This means the intents reflect what customers actually ask about, not what we assume they ask about. The trade-off is noisier cluster boundaries, but that's honest — customer intents genuinely overlap."

**Evaluation strategy**: "Three baselines (trivial, ML, AI) compared on a stratified golden set. Reply quality measured by an LLM judge with 6 dimensions, validated against human scores. I report false-auto rate as the primary escalation metric because a missed escalation has higher cost than an unnecessary one."

**Biggest failure**: "The retrieval sometimes returns superficially similar but semantically wrong examples — same keywords, different problem. This poisons the reply generator's evidence. The fix is intent-filtered reranking, which I'd implement in a second iteration."

**Next improvement**: "Human-review all 200 golden labels. It's the single highest-impact improvement to evaluation credibility, and it's boring but important."

## Project Structure

```
├── README.md               ← You are here
├── DECISION_LOG.md          ← 15 engineering decisions
├── REPORT.md                ← Full report (max 6 pages)
├── requirements.txt
├── .env.example
│
├── data/
│   ├── raw/twcs.csv         ← Place dataset here
│   ├── processed/           ← Pipeline outputs
│   └── golden/              ← Evaluation set
│
├── src/
│   ├── config.py            ← Centralized configuration
│   ├── profile_dataset.py   ← Phase 1: Dataset profiling
│   ├── select_brand.py      ← Phase 2: Brand selection
│   ├── build_threads.py     ← Phase 3: Thread reconstruction
│   ├── discover_intents.py  ← Phase 4: Intent taxonomy
│   ├── create_golden_set.py ← Phase 5: Golden set
│   ├── baseline_majority.py ← Phase 6: Trivial baseline
│   ├── baseline_tfidf.py    ← Phase 7: ML baseline
│   ├── train_classifier.py  ← Phase 8: LLM classifier
│   ├── retrieve_examples.py ← Phase 9: Historical retrieval
│   ├── generate_reply.py    ← Phase 10: Reply generation
│   ├── escalation.py        ← Phase 11: Escalation policy
│   ├── agent.py             ← Phase 12: End-to-end agent
│   ├── evaluate.py          ← Phase 13: Evaluation harness
│   ├── judge_replies.py     ← Phase 14: LLM judge
│   ├── human_judge_agreement.py ← Phase 15: Human agreement
│   └── run_pipeline.py      ← Master pipeline runner
│
├── prompts/                 ← LLM prompt files
├── tests/                   ← pytest test suite
└── reports/                 ← Generated reports and figures
```
