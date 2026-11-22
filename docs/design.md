# Anonymisation pipeline: design

## 1. Goal

Mask the personal data in a document so that:

- each sensitive **word** becomes a single `*` (`Ana Correia` -> `* *`);
- everything else (line breaks, accents, punctuation) is kept exactly as it
  was. Empty lines are dropped during extraction;
- context decides what is sensitive: a report's own date or reference code
  stays visible, a birth date does not.

## 2. Design principles

1. **LLMs only find; Python masks.** Agents return `Finding`s (exact text,
   category, reason, line). A deterministic masker applies `*`. A model
   that rewrote the whole document would tend to alter spacing, accents or
   line breaks, and every such change corrupts the output.
2. **The orchestrator is plain Python.** The flow is fixed, so an LLM
   orchestrator would only add calls, cost and randomness. The agents are
   the LLM calls it dispatches.
3. **The context checker adds spans; it never rewrites.** It finds words
   that indirectly reveal an already-masked entity (e.g. "a city known for
   its tram 28" after a masked "Lisbon"), and it can reject false
   positives.
4. **The taxonomy is data.** The categories live in `categories.json`.
   Regrouping them is an edit to that file, not a code change.

## 3. Architecture

```
prompts/base.md -> shared instructions
PDF --extract--> text (no empty lines)
  -> detector (all categories, 1 call)               -> labelled findings
  -> context_checker (all findings, 1 call; skipped
     when nothing was found)                         -> +spans / -rejects
  -> merge + dedupe -> masking.apply_findings         -> masked v1
  -> reviewer (sees masked v1, flags leaks; 1 call)  -> extra findings
  -> masking again -> <input>.masked.txt ; report.md ; findings.json
```

- **Agent prompt** = `prompts/base.md` + the agent's focus from
  `prompts/<agent>.md` (with every category inserted) + a
  `### DOCUMENTO ###` line + the document text. `base.md` itself must not
  contain that marker line, or each agent would see two documents (a test
  guards this).
- **Budget:** at most 3 calls per document, made one after another, at
  temperature 0, with JSON output validated against a pydantic model. The
  budget is sized for the Gemini free tier (as few as 5 requests per
  minute); one detector covers every category, and the category it assigns
  is only a report label, since masking doesn't depend on it.
- The whole document goes into every prompt, so the model's context window
  bounds the document size.

## 4. Contracts

### 4.1 Data models (`schemas.py`)

```python
class Finding(BaseModel):
    text: str          # copied verbatim from the document
    category: str      # an id from categories.json
    reason: str        # one short sentence, shown in the report
    context: str = ""  # the line the finding sits on, copied verbatim

class DetectorResult(BaseModel):
    findings: list[Finding]

class ContextResult(BaseModel):
    additions: list[Finding]   # indirect identifiers to mask too
    rejections: list[str]      # finding texts judged not sensitive

class ReviewResult(BaseModel):
    findings: list[Finding]    # leaks still visible in the masked text

class EntailmentScore(BaseModel):
    score: int = Field(ge=0, le=100)
```

### 4.2 LLM client (`llm.py`)

```python
class LLMClient(Protocol):
    def generate_json(self, prompt: str, schema: type[T]) -> T: ...
    def generate_text(self, prompt: str) -> str: ...
```

Everything that talks to a model goes through this protocol, so swapping
the provider touches only `llm.py` and `config.py`.

`GeminiClient(model, temperature=0.0)` implements it with `google-genai`.
It spaces requests to each model at least 13 s apart (5 requests per
minute plus a 1 s margin, since Google counts over a sliding minute) and
retries HTTP 429/500/503 and dropped connections: a per-minute 429 waits
the delay stated in the error, server errors back off 5, 15, 45, 60, 60 s,
and a per-day 429 fails fast.

The commands wrap the client in `CachedClient` (`make_client`), which
stores each successful reply in `outputs/.cache/`, keyed by model and
prompt: a rerun after a failure only sends the calls that never succeeded,
and a changed prompt is always sent. `--no-cache` asks again and replaces
the stored replies.

Tests use `FakeLLMClient` (`tests/fakes.py`), which answers through a
`responder(prompt, schema)` function, routing on prompt content rather than
call order.

### 4.3 Agents, pipeline and validation

```python
detect(text, categories, base, client) -> list[Finding]
check_context(text, categories, findings, base, client) -> ContextResult
review(masked_text, base, client) -> list[Finding]

apply_findings(text, findings) -> MaskResult
    # .masked: str, .unmatched: list[Finding] (not found verbatim)

run_pipeline(text, base, client) -> PipelineResult
    # .masked, .findings, .rejected: list[str], .unmatched

DocumentValidator(client=None)
    .entailment(original, anonymised) -> int    # 0-100
    .check_removed_words(document, expected) -> bool
```

### 4.4 Synthetic data format

`data_generator.py` writes pairs of files to `synth/data/`:
`synthetic_document_NNN.txt` (the document, without empty lines) and
`synthetic_document_NNN_masked.txt` (the ground truth). The generator
labels spans with the categories from `categories.json` and masks them with
`apply_findings`, so the ground truth follows the pipeline's own rules.
`evaluate/score.py` compares the pipeline's output with it word by word
(precision, recall and F1 over masked words, by position).

## 5. Masking rule

- A **word** is a token separated by whitespace.
- A token is masked when any part of it overlaps a finding's text. The text
  only matches as whole words (`Ana` never matches inside `Anamnese`).
- When a finding has a `context` (its line), only occurrences inside that
  line are masked. Masking every occurrence would also hide, for instance,
  the city in a clinic's name in the report title. A finding with no
  `context` is masked everywhere.
- Punctuation at the start or end of the token (`, . ; : ( ) ! ?`) is kept,
  and the rest of the token becomes a single `*`.
- Punctuation inside the token (`@ . - / +`) belongs to the word.

| Input | Output |
|---|---|
| `Maria Conceição Oliveira Santos` | `* * * *` |
| `Flores,` | `*,` |
| `(João,` | `(*,` |
| `maria.santos@example.pt` | `*` |
| `+351 912 345 678` | `* * * *` |
| `12345678-9ZX0` | `*` |

Line structure is never changed. The rule lives in one function in
`masking.py`.

## 6. Categories (`categories.json`)

| id | Covers |
|---|---|
| `identity` | names of people (patient, relatives, friends, doctor), age |
| `contact_location` | address, phone, email, profession, workplace |
| `gov_financial_ids` | tax and citizen IDs, social security no., card number, expiry, CVV, insurance policy no., income, professional licence no. |
| `health` | diagnoses, HIV status, genetics, family medical history, medication, biometrics |
| `sensitive_social` | religion, ethnicity, nationality, political affiliation, sexual orientation, marital status, substance use |

Each entry has `id`, `name`, `description`, `examples` and `do_not_mask`.
Health data is masked. A unit test checks that every category id is
mentioned in `prompts/base.md`, so the two cannot drift apart.

## 7. Reports and validation

Each run writes `outputs/findings.json` (every finding, its category and
reason, the rejections) and `outputs/report.md` (a readable table, plus
`DocumentValidator().entailment()` as the meaning-preservation score when
`VALIDATION_MODEL` is set).

## 8. Known risks

- **Document size.** Every agent receives the whole document, so a long
  document can exceed the model's context window.
- **PDF line wrapping.** `page.get_text()` keeps the PDF's visual line
  breaks (a sentence may span two lines), and so does the output.
- **Rate limits.** Request spacing only sees this process: another
  terminal using the same key still shares the quota.
