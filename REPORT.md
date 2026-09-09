# AI Support Agent — Report

> **Note**: This report template contains placeholders (`{PLACEHOLDER}`) for metrics that will be populated after running the evaluation pipeline with real data. No metrics are fabricated.

## 1. Problem Framing

**Goal**: Build an AI customer support agent for a single brand that classifies intents, drafts grounded replies, and decides whether to auto-handle or escalate — with rigorous evaluation.

**What "good" means**:
- Intent classification that meaningfully beats trivial and ML baselines
- Replies grounded in historical brand behavior (no hallucinated policies)
- Conservative escalation that minimizes false-auto rate (missed escalations)
- Honest evaluation with documented failure modes

**What we deliberately did NOT build**:
- Multi-brand or general-purpose agent
- Frontend or deployment infrastructure
- Fine-tuned model
- Full-dataset processing pipeline
- Real-time serving system

## 2. Dataset and Sampling

**Source**: `thoughtvector/customer-support-on-twitter` (Kaggle)

The dataset contains ~3M tweets between customers and brand support accounts on Twitter. We process only the selected brand's conversations.

**Brand selection**: Data-driven weighted scoring across conversation volume, multi-turn depth, resolution rate, vocabulary diversity, response quality, and customer message volume. See `data/processed/selected_brand.json` for full scoring.

**Golden evaluation set**: 200 stratified examples covering:
- All intents (minimum 5 per intent)
- Escalation-worthy cases (≥20% of set)
- Tone diversity (angry, frustrated, polite, neutral)
- Message length diversity (short, medium, long)
- Thread depth diversity

Labels are auto-generated from clustering + heuristics and marked for human review.

## 3. Architecture

```
Customer Message
       │
       ▼
┌─────────────┐
│   Intent     │──────────────────────────────┐
│  Classifier  │                              │
│  (LLM-based) │                              │
└──────┬───────┘                              │
       │ intent + confidence                  │
       ▼                                      │
┌─────────────┐                               │
│  Retrieval   │  top-k similar resolved      │
│  Engine      │  conversations               │
│ (embeddings) │                              │
└──────┬───────┘                              │
       │ historical examples                  │
       ▼                                      │
┌─────────────┐                               │
│    Reply     │  grounded in evidence        │
│  Generator   │                              │
│  (LLM-based) │                              │
└──────┬───────┘                              │
       │ reply + confidence                   │
       ▼                                      ▼
┌─────────────────────────────────────────────────┐
│              Escalation Policy                   │
│  (rule-based + confidence thresholds)            │
│                                                  │
│  Inputs: message, intent confidence,             │
│          retrieval score, reply confidence        │
│                                                  │
│  Output: AUTO / ESCALATE + reason                │
└──────────────────────────────────────────────────┘
```

**Key design choice**: Escalation is rule-based (not LLM-based) for transparency and auditability. The LLM handles the subjective tasks (understanding, generation); rules handle the safety-critical decision.

## 4. Intent Taxonomy

Derived from TF-IDF + KMeans clustering of the brand's actual customer messages, with LLM-assisted cluster labeling.

See `reports/intent_taxonomy.md` for the full taxonomy with definitions, examples, and frequencies.

## 5. Evaluation Methodology

### Three systems compared:
1. **Trivial baseline**: Majority-class intent + always-auto-handle escalation
2. **ML baseline**: TF-IDF + Logistic Regression (or LinearSVC)
3. **AI system**: LLM classifier + embedding retrieval + LLM reply generation + rule-based escalation

### Metrics:
- **Intent**: Accuracy, macro F1, weighted F1, per-class F1, confusion matrix
- **Escalation**: Precision, recall, F1, false-auto rate, false-escalation rate
- **Reply quality**: 6-dimension LLM judge (groundedness, correctness, resolution match, relevance, tone, completeness)

### Judge validation:
- 30–50 examples independently scored by human
- Agreement metrics: exact agreement, adjacent agreement, Pearson correlation, major disagreements

## 6. Results

> Results below are populated after running `python -m src.evaluate`. If you see `{PLACEHOLDER}`, the evaluation has not yet been run.

### Intent Classification

| System | Accuracy | Macro F1 | Weighted F1 |
|--------|----------|----------|-------------|
| Trivial (majority) | {MAJORITY_ACC} | {MAJORITY_F1} | {MAJORITY_WF1} |
| TF-IDF + LR/SVC | {TFIDF_ACC} | {TFIDF_F1} | {TFIDF_WF1} |
| AI (LLM) | {AI_ACC} | {AI_F1} | {AI_WF1} |

### Escalation

| System | Precision | Recall | F1 | False-Auto Rate |
|--------|-----------|--------|----|-----------------|
| Trivial (always-auto) | N/A | 0.0% | 0.0 | 100% |
| AI system | {AI_ESC_P} | {AI_ESC_R} | {AI_ESC_F1} | {AI_FALSE_AUTO} |

## 7. Reply Quality

| Dimension | Mean (0-2) | Median |
|-----------|-----------|--------|
| Groundedness | {GROUND} | {GROUND_MED} |
| Correctness | {CORRECT} | {CORRECT_MED} |
| Resolution Match | {RESMATCH} | {RESMATCH_MED} |
| Relevance | {RELEV} | {RELEV_MED} |
| Tone | {TONE} | {TONE_MED} |
| Completeness | {COMPLETE} | {COMPLETE_MED} |
| **Overall** | **{OVERALL}/12** | **{OVERALL_MED}** |

### Human-Judge Agreement

> **Status**: Template generated. Pending human review.
>
> Complete `data/golden/human_review_template.csv` and re-run `python -m src.human_judge_agreement` to populate these metrics.

## 8. Escalation Analysis

The escalation policy is deliberately conservative: prefer false-escalation over false-auto-handle.

**False-auto rate** (missed escalations) is the critical safety metric. Even a low rate means some customers with security breaches, legal concerns, or repeated unresolved issues receive automated responses instead of human attention.

## 9. Top 5 Failure Modes

> Populated after evaluation. See `reports/evaluation.md` for details.

### 1. Intent confusion between similar categories
- **Example**: {EXAMPLE_1}
- **Expected**: {EXPECTED_1}
- **Actual**: {ACTUAL_1}
- **Why**: Overlapping vocabulary between related intents
- **Fix**: Better intent definitions or merge confusable intents

### 2. Retrieval returning superficially similar but wrong-intent examples
- **Example**: {EXAMPLE_2}
- **Why**: Semantic similarity doesn't always correlate with same intent
- **Fix**: Intent-filtered retrieval reranking

### 3. Generic/safe replies for ambiguous messages
- **Example**: {EXAMPLE_3}
- **Why**: Anti-hallucination prompt makes model cautious with weak evidence
- **Fix**: Calibrated confidence thresholds, better few-shot retrieval

### 4. Missed escalation for subtle signals
- **Example**: {EXAMPLE_4}
- **Why**: Keyword-based rules miss implicit frustration or sarcasm
- **Fix**: LLM-assisted escalation signal detection

### 5. Timestamp/context limitations
- **Example**: {EXAMPLE_5}
- **Why**: Tweet-level data loses conversation flow nuances
- **Fix**: Better thread context modeling, multi-turn awareness

## 10. What Is Misleading About My Headline Number?

> **Headline**: {HEADLINE_ACC}% intent accuracy

**What makes this misleading**:

1. **Class imbalance**: The most common intent may represent {MAJORITY_FREQ}% of examples. Aggregate accuracy is dominated by performance on frequent intents.

2. **Stratified golden set**: Our golden set over-samples rare intents and edge cases, so the accuracy is measured on a harder distribution than production traffic. The number is both pessimistic (harder test) and optimistic (we trained on similar distributions).

3. **Auto-labeled ground truth**: Labels come from clustering + heuristics, not verified human annotation. Some "errors" may be label noise, not model failures.

4. **Golden set size**: 200 examples means ~±7% confidence interval at 95% confidence. Small class sizes have even wider intervals.

5. **Escalation cost asymmetry**: A false-auto (missed escalation) is far more costly than a false-escalation, but F1 treats them symmetrically.

**More informative metrics**:
- Macro F1 (weights all intents equally)
- Per-class F1 for rare intents
- False-auto rate (the metric that matters most for safety)
- LLM judge scores with human agreement data

## 11. What I'd Do With One More Week

Ranked by expected impact:

1. **Human-review all 200 golden labels** (high impact, medium effort): The single biggest improvement to evaluation credibility. Correct clustering errors, resolve ambiguous cases, validate escalation labels.

2. **Intent-filtered retrieval reranking** (high impact, low effort): After retrieving top-20 by embedding similarity, rerank by intent match. This would reduce "superficially similar but wrong category" retrieval failures.

3. **Active learning for ambiguous examples** (high impact, medium effort): Identify examples where the classifier is uncertain and prioritize them for human labeling. This improves the training signal on exactly the cases where the model struggles.

4. **Calibrated escalation thresholds** (medium impact, low effort): Tune escalation thresholds on a validation set to optimize the false-auto/false-escalation trade-off for specific business requirements.

5. **Multi-turn context modeling** (medium impact, high effort): Currently we use the first customer message per thread. Incorporating the full conversation history would improve intent classification for follow-up messages.

6. **Monitoring and drift detection** (medium impact, medium effort): Track intent distribution, retrieval scores, and escalation rates over time. Alert when the distribution shifts significantly from the golden set.

7. **Policy-aware grounding** (lower impact, high effort): Augment retrieval with structured policy documents (if available) so the reply generator can reference official policies, not just past conversations.

## 12. Conclusion

This project optimizes for evaluation rigor over system sophistication. The architecture is deliberately simple — a classifier, a retriever, a generator, and a rule-based escalation policy. The value is in the evaluation: three baselines, dimensional reply quality scoring, human-validated judge, honest failure analysis, and transparent reporting of limitations.

The system demonstrates that even a simple retrieval-augmented approach can produce grounded, relevant support replies when paired with conservative escalation and honest evaluation.
