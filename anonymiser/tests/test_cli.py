import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from anonymiser import cli
from anonymiser import config
from anonymiser.tests.fakes import FakeLLMClient
from anonymiser.tests.helpers import sample_text, write_sample_pdf


def no_findings(prompt, schema):
    if "verificação de contexto" in prompt:
        return json.dumps({"additions": [], "rejections": []})
    return json.dumps({"findings": []})


class TestMain(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.source = write_sample_pdf(root)
        self.output = root / "masked.txt"
        self.output.write_text("OLD", encoding="utf-8")
        self.outputs = root / "outputs"

        patcher = patch.object(config, "OUTPUTS_DIR", self.outputs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, args, client):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = cli.main(args, client=client)
        return code, stderr.getvalue()

    def test_main_writes_output_only_on_success(self):
        code, _ = self.run_main(
            [str(self.source), "-o", str(self.output), "--no-validate"],
            FakeLLMClient(no_findings),
        )

        self.assertEqual(code, 0)
        written = self.output.read_bytes()
        self.assertNotIn(b"\r", written)
        self.assertEqual(written.decode("utf-8"), sample_text())
        self.assertTrue((self.outputs / "report.md").exists())

    def test_default_output_sits_next_to_input(self):
        code, _ = self.run_main([str(self.source), "--no-validate"],
                                FakeLLMClient(no_findings))

        self.assertEqual(code, 0)
        default = self.source.with_name("sample.masked.txt")
        self.assertEqual(default.read_text(encoding="utf-8"), sample_text())

    def test_main_failure_leaves_output_untouched(self):
        def fail(prompt, schema):
            raise RuntimeError("model failed after retries: 503")

        code, stderr = self.run_main(
            [str(self.source), "-o", str(self.output), "--no-validate"],
            FakeLLMClient(fail),
        )

        self.assertEqual(code, 1)
        self.assertIn("503", stderr)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "OLD")

    def test_replies_are_cached_unless_no_cache(self):
        base_args = [str(self.source), "-o", str(self.output), "--no-validate"]
        for extra, refresh in (([], False), (["--no-cache"], True)):
            with self.subTest(extra=extra), \
                    patch.object(config, "main_model", return_value="m"), \
                    patch.object(cli, "make_client") as make_client:
                make_client.return_value = FakeLLMClient(no_findings)

                code, _ = self.run_main(base_args + extra, None)

                self.assertEqual(code, 0)
                make_client.assert_called_once_with("m", refresh=refresh)


if __name__ == "__main__":
    unittest.main()
