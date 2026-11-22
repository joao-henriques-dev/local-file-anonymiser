import tempfile
import unittest
from pathlib import Path

from submission.anonymizer.base_prompt import MARKER, compose, load_base
from submission.anonymizer.categories import load_categories


class TestLoadBase(unittest.TestCase):
    def test_load_base_strips_surrounding_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "base.md"
            path.write_text("\nInstr only\n", encoding="utf-8")
            self.assertEqual(load_base(path), "Instr only")


class TestCompose(unittest.TestCase):
    def test_compose_orders_parts(self):
        prompt = compose("BASE", "detector", "DOC", category_block="CAT")
        self.assertTrue(prompt.startswith("BASE"))
        self.assertIn("CAT", prompt)
        self.assertTrue(prompt.endswith(f"{MARKER}\nDOC"))

    def test_every_template_composes(self):
        fields = {"category_block": "CAT", "findings_block": "FIND"}
        for agent in ("detector", "context_checker", "reviewer"):
            prompt = compose("BASE", agent, "DOC", **fields)
            self.assertNotIn("$", prompt)


class TestBasePrompt(unittest.TestCase):
    def setUp(self):
        self.text = load_base()

    def test_base_mentions_every_category(self):
        for category in load_categories():
            self.assertIn(category.id, self.text)

    def test_base_embeds_no_document(self):
        # compose appends the document after the marker line; a marker line
        # in the base would make every agent see two documents.
        self.assertNotIn(MARKER, self.text.splitlines())


if __name__ == "__main__":
    unittest.main()
