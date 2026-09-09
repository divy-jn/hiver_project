# Decision Log

Engineering decisions made during the design and implementation of the AI customer support agent. Each entry documents a non-obvious choice, the alternatives considered, and the trade-off.

---

## 1. Single Brand Focus

**Decision**: Build the agent for ONE brand rather than a multi-brand system.

**Alternatives**:
- Multi-brand agent with brand-specific adapters
- Brand-agnostic general support agent

**Why selected**: A single-brand focus gives us deeper, more honest evaluation. We can measure intent coverage, retrieval quality, and escalation accuracy against that brand's actual historical behavior. A multi-brand system would spread our evaluation thin and make it harder to identify real failure modes.

**Trade-off**: Less general, but much stronger evaluation story.

---

## 2. Data-Driven Brand Selection (Weighted Scoring)

**Decision**: Select the brand using a weighted composite score across 6 factors (conversation volume, multi-turn depth, resolution rate, vocabulary diversity, response quality, customer volume).

**Alternatives**:
- Pick the brand with the most tweets
- Manually choose a recognizable brand
- Random selection

**Why selected**: Raw volume doesn't guarantee evaluation quality. A brand with 50k tweets but only "we're sorry" responses gives worse evaluation data than a brand with 10k tweets and diverse, substantive resolutions. The scoring prioritizes brands that give us the strongest evaluation story.

**Trade-off**: Scoring weights are heuristic — different weights might select a different brand. We document the weights for reproducibility.

---

## 3. TF-IDF Clustering for Intent Discovery (Not Banking77 or Manual)

**Decision**: Derive intents from the brand's actual data using TF-IDF + KMeans clustering, then label clusters with LLM assistance.

**Alternatives**:
- Use an off-the-shelf taxonomy like Banking77
- Manually define intents by reading sample messages
- Use LLM to generate taxonomy from scratch

**Why selected**: Banking77 doesn't match Twitter support workflows. Manual labeling doesn't scale and introduces prior bias. TF-IDF clustering reflects the actual distribution of customer issues for this specific brand. LLM labeling of clusters is a practical middle ground — data-driven structure with human-readable labels.

**Trade-off**: Cluster boundaries are imperfect. Some intents may overlap. This is honest — we document the ambiguity rather than pretending clean categories exist.

---

## 4. Target 6–12 Intents (Not Fewer, Not More)

**Decision**: Aim for 6–12 intent categories.

**Alternatives**:
- 3–5 very broad categories
- 20+ fine-grained categories

**Why selected**: Fewer than 6 loses the ability to distinguish meaningfully different support needs. More than 12 creates sparse categories where evaluation becomes unreliable (too few golden examples per class). The range balances granularity with statistical validity.

**Trade-off**: Some genuinely distinct issues get merged. We document common confusions in the taxonomy.

---

## 5. Stratified Golden Set (Not Random Sampling)

**Decision**: Use stratified sampling across intents, tones, lengths, thread depths, and escalation cases for the golden set.

**Alternatives**:
- Random 200 examples
- First 200 examples chronologically
- Manual curation

**Why selected**: Random sampling would under-represent rare intents, angry customers, and escalation-worthy cases — exactly the scenarios where the system is most likely to fail. Stratified sampling ensures we evaluate edge cases, not just the happy path.

**Trade-off**: The golden set is not representative of production distribution. We acknowledge this in "What is misleading about my headline number?"

---

## 6. Always-Auto as Trivial Escalation Baseline (Not Always-Escalate)

**Decision**: Use "always auto-handle" as the trivial baseline rather than "always escalate."

**Alternatives**:
- Always escalate (100% recall, 0% false-auto)
- Random coin flip

**Why selected**: Always-escalate has trivially perfect recall. The more informative baseline is always-auto because it reveals the false-auto rate — how many escalation-worthy cases get missed. This is the dangerous failure mode in production.

**Trade-off**: Always-auto baseline shows 0% escalation recall, which looks bad but is exactly the floor we need to beat.

---

## 7. TF-IDF + Logistic Regression (Not Deep Learning)

**Decision**: Use TF-IDF + Logistic Regression as the ML baseline, with LinearSVC as a comparison.

**Alternatives**:
- Fine-tuned BERT/DistilBERT
- FastText
- Naive Bayes

**Why selected**: TF-IDF+LR is interpretable, fast, reproducible, and surprisingly competitive on short text classification. It gives us a meaningful baseline that the LLM system must beat. If the LLM can't beat TF-IDF+LR, that's an important finding. Cross-validation picks between LR and SVC based on data.

**Trade-off**: Misses semantic similarity that embeddings capture. This is intentional — the gap between TF-IDF and LLM shows the value of semantic understanding.

---

## 8. Sentence-Transformers for Retrieval (Not Full Vector DB)

**Decision**: Use `all-MiniLM-L6-v2` embeddings with cosine similarity via NumPy, not a vector database.

**Alternatives**:
- FAISS
- ChromaDB / Pinecone / Weaviate
- BM25 keyword retrieval

**Why selected**: For ~5K–20K resolved threads, brute-force cosine similarity over normalized embeddings is fast enough (<100ms) and eliminates external dependencies. `all-MiniLM-L6-v2` is small (80MB), well-tested, and runs on CPU. A vector DB adds operational complexity with no measurable benefit at this scale.

**Trade-off**: Won't scale to millions of examples. At that point, FAISS or a managed vector DB would be necessary.

---

## 9. Conservative Escalation Policy

**Decision**: Prefer false escalation over false auto-handle. Single high-priority signal (security, legal, safety) triggers immediate escalation; 2+ medium signals also escalate.

**Alternatives**:
- Aggressive auto-handling (escalate only on explicit request)
- LLM-based escalation decision
- Fixed threshold on classifier confidence alone

**Why selected**: In customer support, a missed escalation (customer with a security breach gets a template response) has much higher cost than an unnecessary escalation (routine query goes to a human). The rule-based approach is transparent, auditable, and doesn't require LLM calls.

**Trade-off**: Higher false-escalation rate increases human agent workload. We measure and report this trade-off explicitly.

---

## 10. Anti-Hallucination Prompt Design

**Decision**: Reply generator prompt explicitly prohibits inventing policies, refunds, dates, or actions. Fallback is "let me connect you with a specialist."

**Alternatives**:
- Allow the model to be more creative
- Hard-code template responses
- No reply generation (just classify + escalate)

**Why selected**: In support contexts, a hallucinated refund promise or fabricated policy is worse than no response. The prompt forces grounding in retrieved examples. When evidence is insufficient, the model asks for information or defers — which is the correct support behavior.

**Trade-off**: Replies may feel conservative or generic. We measure this via the "completeness" judge dimension.

---

## 11. LLM Judge with 6 Dimensions (Not Single Score)

**Decision**: Evaluate reply quality on 6 independent dimensions (groundedness, correctness, resolution match, relevance, tone, completeness) rather than a single quality score.

**Alternatives**:
- Single 1-10 quality score
- Binary good/bad
- BLEU/ROUGE against reference replies

**Why selected**: A single score hides which aspects fail. Dimensional scoring lets us identify that, for example, tone is good but groundedness is poor. BLEU/ROUGE is inappropriate because there are many valid reply phrasings. The 6 dimensions map to distinct failure modes.

**Trade-off**: More LLM calls (1 per evaluation example). We keep the rubric explicit to maximize judge consistency.

---

## 12. Human Agreement as Validation (Not Optional)

**Decision**: Require human review of 30–50 judge scores to validate the LLM judge before trusting it.

**Alternatives**:
- Trust the LLM judge without validation
- Skip reply quality evaluation entirely
- Use only human evaluation

**Why selected**: An unvalidated LLM judge is circular — we're using a model to evaluate a model. Without human agreement data, the judge scores are uninterpretable. Even 30 examples with agreement metrics make the evaluation credible.

**Trade-off**: Requires manual work. Template is generated automatically; if not yet completed, results are clearly marked as "pending human review."

---

## 13. Auto-Labeling with Explicit Review Workflow

**Decision**: Golden set labels are auto-generated from clustering + heuristics, explicitly marked as `auto_labeled`, with a review workflow and guidelines document.

**Alternatives**:
- Fully manual labeling from scratch
- Treat auto-labels as ground truth
- Use LLM to label everything

**Why selected**: Fully manual labeling of 200 examples is time-intensive. Auto-labeling provides a starting point that humans can correct. The key is transparency — every label is marked with its status, and the validation script checks for completeness.

**Trade-off**: Evaluation results before human review have a quality ceiling. We document this limitation.

---

## 14. No Fine-Tuning

**Decision**: Use the LLM as-is with prompt engineering, no fine-tuning.

**Alternatives**:
- Fine-tune on brand's historical responses
- Fine-tune classifier on labeled data
- Use few-shot examples in context

**Why selected**: Fine-tuning requires more data, compute, and introduces training/serving complexity. For a take-home assignment, the evaluation story is stronger with a clear prompt-engineering approach: we can inspect exactly what the model sees. Few-shot examples ARE used via retrieval — this is effectively dynamic few-shot.

**Trade-off**: May underperform a fine-tuned model. But we can measure and report the gap honestly.

---

## 15. Subsample Processing (Not Full 3M Tweets)

**Decision**: Process only the selected brand's conversations, not the full ~3M tweet dataset.

**Alternatives**:
- Process everything
- Use a fixed random sample across all brands

**Why selected**: The assignment explicitly says full-dataset processing is not required. Processing one brand's data (~10K-50K tweets) is sufficient for a strong evaluation. This keeps the pipeline reproducible in <15 minutes as required.

**Trade-off**: Can't compare across brands or measure cross-brand transfer. This is acceptable for a single-brand agent.
