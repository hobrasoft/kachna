import json
from typing import Any, Callable, Type

from pydantic import BaseModel


class FunctionResultFormatter:
    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        api_key: str | None,
        forward_to_llm: Callable[[str, str, float, str | None, dict], Any],
        sanitize_completion_response: Callable[[dict], dict],
        completion_request_cls: Type[BaseModel],
    ) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._api_key = api_key
        self._forward_to_llm = forward_to_llm
        self._sanitize_completion_response = sanitize_completion_response
        self._completion_request_cls = completion_request_cls

    @staticmethod
    def format_prompt() -> str:
        return ("""

Jsi formátovač odpovědí.

Dostaneš:
- otázku uživatele (v češtině) v USER_QUESTION
- data v TOOL_RESULT_JSON s faktickými daty

Úkol:
- zformátuj data z TOOL_RESULT_JSON do jedné oznamovací věty v češtině
- použij pouza fakta z TOOL_RESULT_JSON. Nic se nevymýšlej
- žádná interpretace, žádný výběr, žádné odvozování

Pravidla výstupu:
- pouze jedna krátká oznamovací věta v češtině
- žádné poznámky, komentáře ani vysvětlení
- žádné nadpisy, odrážky ani další text
- nikdy necituj otázku
- použij pouze nutná data z JSON
- datum a čas formátuj jako datum: DD.MM.YYYY nebo čas hh:mm (bez sekund)
{PROMPT_RECOMMENDATION}

USER_QUESTION:
{USER_QUESTION}

TOOL_RESULT_JSON:
{TOOL_RESULT_JSON}

Zformátuj zadání do odpovědi:

""")

    async def format(self, question: str, result: Any, model: str) -> str:
        result_json = json.dumps(result, ensure_ascii=False, indent=2)

        table_markdown = self._format_table(result)
        if table_markdown is not None:
            return table_markdown

        # vytáhni doporučení z JSONu
        recommendation = ""
        if isinstance(result, dict) and "prompt" in result:
            recommendation = result["prompt"].strip()

        # pokud existuje, zabal ho jako blok instrukcí
        prompt_recommendation = ""
        if recommendation:
            prompt_recommendation = f"- {recommendation}\n"

        # slož finální prompt
        prompt = self.format_prompt().format(
            PROMPT_RECOMMENDATION=prompt_recommendation,
            USER_QUESTION=question,
            TOOL_RESULT_JSON=result_json,
        )

        payload = self._completion_request_cls(
            model=model,
            prompt=prompt,
            temperature=0,
            top_p=0.1,
            presence_penalty=0,
            frequency_penalty=0,
        ).model_dump()
        data = await self._forward_to_llm(
            self._base_url,
            "/v1/completions",
            self._timeout_s,
            self._api_key,
            payload,
        )
        data = self._sanitize_completion_response(data)
        choice = (data.get("choices") or [{}])[0]
        text = choice.get("text") if isinstance(choice, dict) else None
        if not isinstance(text, str) or not text.strip():
            return result_json
        return text.strip()

    def _format_table(self, result: Any) -> str | None:
        if not isinstance(result, dict):
            return None
        format_value = result.get("format")
        if not isinstance(format_value, str) or format_value.strip().lower() != "table":
            return None
        if "data" not in result:
            return None
        data = result.get("data")
        return self._render_markdown_table(data)

    def _render_markdown_table(self, data: Any) -> str | None:
        if isinstance(data, dict):
            rows = [data]
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            rows = data
        else:
            return None

        headers: list[str] = []
        for row in rows:
            for key in row.keys():
                key_str = str(key)
                if key_str not in headers:
                    headers.append(key_str)

        if not headers:
            return None

        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            row_values = {str(key): value for key, value in row.items()}
            cells = [
                self._escape_markdown_cell(self._stringify_cell(row_values.get(key)))
                for key in headers
            ]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    @staticmethod
    def _stringify_cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _escape_markdown_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", "<br>")
