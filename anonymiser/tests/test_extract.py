import tempfile
import unittest
from pathlib import Path

from anonymiser.extract import clean_lines, pdf_to_text
from anonymiser.tests.helpers import sample_text, write_sample_pdf


class TestExtract(unittest.TestCase):
    def test_clean_lines_drops_empty_and_trailing_space(self):
        raw = "Relatório\n\n  \nA paciente relatou dores \nabdominais\n"
        self.assertEqual(
            clean_lines(raw),
            "Relatório\nA paciente relatou dores\nabdominais",
        )

    def test_pdf_text_keeps_lines_and_accents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_sample_pdf(Path(directory))
            self.assertEqual(pdf_to_text(path), sample_text())


if __name__ == "__main__":
    unittest.main()
