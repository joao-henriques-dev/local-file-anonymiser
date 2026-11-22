"""Anonymise a PDF document.

Run from the repo root:
    python -m submission.run report.pdf                  # -> report.masked.txt
    python -m submission.run report.pdf -o masked.txt    # chosen output path
"""
import argparse
import sys
from pathlib import Path

from submission.anonymizer import config
from submission.anonymizer.base_prompt import load_base
from submission.anonymizer.extract import pdf_to_text
from submission.anonymizer.llm import LLMClient, make_client
from submission.anonymizer.orchestrator import run_pipeline
from submission.anonymizer.report import write_report, write_utf8
from submission.validation import DocumentValidator


def main(argv: list[str] | None = None,
         client: LLMClient | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="the PDF to anonymise")
    parser.add_argument("-o", "--output", type=Path,
                        help="where to write the masked text "
                             "(default: <input>.masked.txt next to it)")
    parser.add_argument("--no-validate", action="store_true",
                        help="skip the meaning-preservation score")
    parser.add_argument("--no-cache", action="store_true",
                        help="ask the model again instead of reusing replies")
    args = parser.parse_args(argv)
    output = args.output or args.input.with_suffix(".masked.txt")

    try:
        if client is None:
            client = make_client(config.main_model(),
                                 refresh=args.no_cache)

        _pipeline(args.input, output, client, validate=not args.no_validate)
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


def _pipeline(source: Path, output: Path, client: LLMClient,
              validate: bool) -> None:
    text = pdf_to_text(source)
    result = run_pipeline(text, load_base(), client)

    # Written only after the whole pipeline succeeded, so a failed run
    # never leaves a half-finished output behind.
    write_utf8(output, result.masked)

    entailment = None
    if validate and config.validation_model():
        try:
            entailment = DocumentValidator().entailment(text, result.masked)
        except Exception as error:
            print(f"warning: validation skipped: {error}", file=sys.stderr)

    write_report(result, config.OUTPUTS_DIR, entailment)


if __name__ == "__main__":
    sys.exit(main())
