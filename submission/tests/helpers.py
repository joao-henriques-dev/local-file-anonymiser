from pathlib import Path

import pymupdf

FIXTURES_DIR = Path(__file__).with_name("fixtures")
SAMPLE_PATH = FIXTURES_DIR / "sample.txt"


def sample_text() -> str:
    return SAMPLE_PATH.read_text(encoding="utf-8").strip()


def write_sample_pdf(directory: Path) -> Path:
    """Render the sample as a one-page PDF inside `directory`.

    Building it at test time keeps a binary out of the repo and the PDF
    always in sync with sample.txt.
    """
    path = directory / "sample.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), sample_text(), fontsize=11)
        document.save(path)
    return path
