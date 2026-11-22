# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## What this repo is

A document anonymiser: a language model finds personal data, plain Python
masks it. It started as team Nova Finance Club's JunctionX Lisbon 2026
entry (NOS Gen-AI challenge) and is now João's own project. The pipeline
still calls Gemini; moving it to local models on Ollama, then reshaping it
for very large documents in any language, is the current work. Tasks and
status: `Roadmap.md`. Spec: `docs/design.md`.

## Architecture (`anonymiser/`)

- **Flow:** PDF -> `extract.py` -> detector (all categories) -> context
  checker (skipped if nothing found) -> `masking.py` -> reviewer ->
  `masking.py` -> `<input>.masked.txt` + `outputs/report.md` +
  `outputs/findings.json`. At most 3 LLM calls per document, one after
  another.
- **The orchestrator is plain Python, not an LLM.** Agents only *find*
  sensitive text (`Finding`: text, category, reason, context line); the
  deterministic `apply_findings` does all masking. LLMs never rewrite the
  document, since any rewording corrupts the output.
- **Masking rule:** one `*` per whitespace-separated word; leading and
  trailing `,.;:()!?` kept; inner `@ . - / +` belong to the word; whole-word
  matches only; a finding with a `context` line is only masked inside that
  line.
- **`categories.json`** is the single source of truth for what is
  sensitive (5 categories; health data *is* masked). The detector prompts,
  `prompts/base.md` (a test checks the ids are in sync) and the synthetic
  data generator all follow it.
- **Prompts:** `prompts/base.md` (shared instructions) + `prompts/<agent>.md`
  + a `### DOCUMENTO ###` line + the document, built by
  `base_prompt.compose`. `base.md` must not contain the marker line. The
  prompts are in Portuguese for now.
- **`llm.py`:** `LLMClient` protocol; every model call goes through it, so a
  provider swap touches only `llm.py` and `config.py`. `make_client` wraps
  the client in `CachedClient` (replies cached in `outputs/.cache/`).
- **Synthetic data** (`data_generator.py`): writes `synth/data/*.txt` +
  `*_masked.txt`, masked with the same `apply_findings`.
  `evaluate/score.py` compares the pipeline's output word by word
  (precision / recall / F1).
- **`validation.py`:** LLM judge for meaning preservation (0-100).

## Commands (repo root, `.venv` active)

All modules use absolute `anonymiser.*` imports, so always run them with
`python -m`, never by file path.

- Tests: `python -m unittest discover -s anonymiser -t .`
- Lint: `flake8 .` (config in `setup.cfg`: 99 columns, `.venv` excluded)
- Pipeline: `python -m anonymiser report.pdf [-o out.txt]`
  (`--no-validate` skips the judge, `--no-cache` asks the model again)
- Synthetic data: `python -m anonymiser.data_generator --count N`
- Scoring: `python -m anonymiser.evaluate.score`

CI (`.github/workflows/lint.yml`) runs only `flake8 .`, on every push and
PR.

## Configuration

- `.env` (gitignored, never read it): `API_KEY`, plus per-role models
  `MAIN_MODEL`, `DATA_GEN_MODEL` (falls back to `MAIN_MODEL`) and
  `VALIDATION_MODEL` (optional; judge skipped if unset). Read them only
  through `config.py`, which loads `.env` on every lookup; `DEFAULT_MODEL`
  is the single hardcoded fallback.

## Conventions

- Lines <= 99 characters (JSON descriptions in `categories.json` are the
  agreed exception).
- Write files as UTF-8 with `\n` line endings (`report.write_utf8`); on
  Windows, text mode would write `\r\n`.
- Tests are `unittest`, with `tests/fakes.FakeLLMClient` (routes on prompt
  content, never on call order) and `tests/helpers.py` (the fictitious
  `fixtures/sample.txt`, rendered to a PDF at test time). Tests must never
  load the real `.env`: patch `anonymiser.config.load_dotenv`.
- `validation.py` was written by Rogério and `data_generator.py` by
  Salvador; mention it when changing their files.
