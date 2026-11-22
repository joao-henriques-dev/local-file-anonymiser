from pathlib import Path
from string import Template

MARKER = "### DOCUMENTO ###"
PROMPTS_DIR = Path(__file__).with_name("prompts")
BASE_PATH = PROMPTS_DIR / "base.md"


def load_base(path: Path = BASE_PATH) -> str:
    """Return the instructions every agent prompt starts with."""
    return path.read_text(encoding="utf-8").strip()


def compose(base: str, agent: str, document: str, **fields: str) -> str:
    # string.Template ($name) instead of str.format, so the JSON examples
    # in the templates need no brace escaping.
    template = Template(
        (PROMPTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
    )
    focus = template.substitute(fields).strip()
    return f"{base}\n\n{focus}\n\n{MARKER}\n{document}"
