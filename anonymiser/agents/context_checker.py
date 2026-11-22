from anonymiser.agents.detector import format_categories
from anonymiser.base_prompt import compose
from anonymiser.categories import Category
from anonymiser.llm import LLMClient
from anonymiser.schemas import ContextResult, Finding


def check_context(text: str, categories: list[Category],
                  findings: list[Finding], base: str,
                  client: LLMClient) -> ContextResult:
    findings_block = "\n".join(
        f'- [{f.category}] "{f.text}" (linha: "{f.context}")'
        for f in findings
    )
    prompt = compose(base, "context_checker", text,
                     category_block=format_categories(categories),
                     findings_block=findings_block)
    return client.generate_json(prompt, ContextResult)
