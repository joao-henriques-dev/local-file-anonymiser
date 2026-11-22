# Roadmap

One task at a time, top to bottom.

## Phase 1: leave the hackathon behind

- [x] Remove the hackathon material (tutorials, scoring workflows, NOS
      files, generated outputs)
- [x] Lint at 99 columns
- [x] Decouple the pipeline from the hackathon contract (`prompts/base.md`,
      CLI takes an input path, own test fixture)
- [x] Rename the package to `anonymiser`
- [x] Rewrite the README, design doc and CLAUDE.md

## Phase 2: Gemini -> Ollama

- [ ] Install Ollama locally, run `ollama serve` and pull a first model
      (needed only for real runs; the code is tested with mocks)
- [ ] Add an `OllamaClient` behind `LLMClient` (explicit `num_ctx`, fail
      loudly when the prompt fills the context window)
- [ ] Run the pipeline and the judge on Ollama
- [ ] Generate synthetic data through the shared client
- [ ] Remove Gemini (client, rate limiting, `google-genai`)

## Phase 3: architecture for local models (discussion first)

- [ ] Very large documents (thousands of pages): chunking with overlap and
      a stable line index so findings map back to the full document
- [ ] Revisit the call budget: per-category detectors and context checks
      now cost time, not quota
- [ ] Which role needs a big model and which a small one
- [ ] Hardware-aware setup: detect RAM/VRAM and pick model tiers from a
      config file
- [ ] Any language: English instructions and language-agnostic categories
- [ ] Run the tests in CI, not only flake8
