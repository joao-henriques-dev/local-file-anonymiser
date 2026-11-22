# Synthetic data (owner: Salvador)

Fictitious labelled documents (Portuguese medical admission reports, for
now). They exist to **measure** the pipeline (`evaluate/score.py`) and are
never part of a real run.

## Generating

From the repo root:

```
python -m anonymiser.data_generator --count 5
```

By default, files land in `anonymiser/synth/data/`. Use `--outdir` to
change it, and `--write-items-file` to also list the labelled spans.

## Files

For each document `NNN`:

| File | Content |
|---|---|
| `synthetic_document_NNN.txt` | the document, without empty lines |
| `synthetic_document_NNN_masked.txt` | the ground truth (masked) |
| `synthetic_document_NNN_sensitive_to_mask.txt` | optional: `category \| text \| context` |

Each file ends with a single `\n`.

## Why the ground truth is comparable

- **Same categories.** The generator's prompt lists the categories from
  `anonymiser/categories.json`, so what it labels as sensitive is exactly
  what the pipeline looks for. Changing the taxonomy there changes both.
- **Same masker.** The masked files come from the pipeline's own
  `apply_findings`: one `*` per word, edge punctuation kept, whole-word
  matches, limited to each span's `context` line (design §5).

Because of this, `evaluate/score.py` can compare the pipeline's output with
the ground truth word by word.

## Scoring

```
python -m anonymiser.evaluate.score
```

This runs the pipeline on every pair and prints precision, recall and F1
over masked words, per document and in total.
