# Local File Anonymiser

Masks personal data in documents with a language model, while plain Python
does the masking itself, so the text around each mask never changes.

> **Status:** the pipeline still calls Google Gemini. Moving it to a local
> model served by Ollama, and then reshaping it for very large documents,
> is the current work (see [`Roadmap.md`](Roadmap.md)).

## How it works

**LLMs find, Python masks.** The model never rewrites the document: it only
returns *findings* (the exact text, its category, a reason and the line it
sits on). A deterministic masker (`anonymiser/masking.py`) then replaces
each sensitive word with a single `*`, keeping line breaks, accents and
punctuation as they were.

```text
PDF --extract--> text (empty lines dropped)
  -> detector         (all categories)        -> findings
  -> context checker  (skipped if none found) -> + indirect identifiers, - false alarms
  -> mask
  -> reviewer         (reads the masked text) -> leaks still visible
  -> mask again -> <input>.masked.txt + outputs/report.md + outputs/findings.json
```

The orchestrator is plain Python, not an LLM: the flow is fixed, so an LLM
in charge of it would only add calls and randomness. What counts as
sensitive lives in [`anonymiser/categories.json`](anonymiser/categories.json)
(identity, contact and location, official and financial IDs, health,
sensitive social data).

Masking rule, in short:

| Input | Output |
|---|---|
| `Ana Correia` | `* *` |
| `Flores,` | `*,` (edge punctuation kept) |
| `ana.correia@example.com` | `*` (inner `@ . - / +` belong to the word) |
| `+351 912 345 678` | `* * * *` |

A finding that carries its line is only masked inside that line, so the
same word elsewhere (a city in the report's title, say) stays visible. The
full design is in [`docs/design.md`](docs/design.md).

## Setup

Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

Settings come from a `.env` file at the repo root (gitignored), read only
through `anonymiser/config.py`:

| Variable | Role | When unset |
|---|---|---|
| `API_KEY` | Gemini authentication | error |
| `MAIN_MODEL` | pipeline agents and scoring | `DEFAULT_MODEL` in `config.py` |
| `DATA_GEN_MODEL` | synthetic data generator | `MAIN_MODEL` |
| `VALIDATION_MODEL` | meaning-preservation judge | judge skipped |

## Usage

Run everything from the repo root with `python -m` (the modules use
absolute `anonymiser.*` imports).

```bash
python -m anonymiser report.pdf                # -> report.masked.txt
python -m anonymiser report.pdf -o masked.txt  # chosen output path
python -m anonymiser report.pdf --no-validate  # skip the judge call
python -m anonymiser report.pdf --no-cache     # ask the model again
```

Each run also writes `outputs/report.md` (findings, rejections, spans not
found verbatim, and the optional 0-100 meaning score) and
`outputs/findings.json`. Successful replies are cached in
`outputs/.cache/`, keyed by model and prompt, so a failed run only repeats
the calls that never succeeded.

**Measuring quality.** The generator writes fictitious labelled documents,
masked with the same `apply_findings`, and the scorer compares the
pipeline's output with them word by word (precision, recall, F1):

```bash
python -m anonymiser.data_generator --count 5
python -m anonymiser.evaluate.score
```

**Tests and lint.** Tests never touch the network or a real `.env`
(`tests/fakes.FakeLLMClient` answers instead of the model).

```bash
python -m unittest discover -s anonymiser -t .
flake8 .
```

## Layout

```text
anonymiser/
  __main__.py, cli.py   # python -m anonymiser <pdf>
  config.py             # paths and settings (.env)
  llm.py                # LLMClient protocol, model client, reply cache
  extract.py            # PDF -> text
  masking.py            # findings -> masked text
  orchestrator.py       # run_pipeline()
  agents/, prompts/     # detector, context checker, reviewer
  categories.json       # what is sensitive (single source of truth)
  report.py             # report.md + findings.json
  validation.py         # LLM judge for meaning preservation
  data_generator.py     # synthetic labelled documents
  evaluate/score.py     # precision / recall / F1
  synth/                # generated data
  tests/                # unittest suite and fixtures
docs/design.md
```

## Origin

The project started at JunctionX Lisbon 2026, as team Nova Finance Club's
answer to the NOS Gen-AI challenge (forked from
[`nosportugal/nos-gen-ai-hackathon`](https://github.com/nosportugal/nos-gen-ai-hackathon)).
Built by João Henriques (core pipeline), Rogério Soares (`validation.py`)
and Salvador Antunes (`data_generator.py`).
