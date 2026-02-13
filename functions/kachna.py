# kachna.py
import json
import re
import sys
from datetime import date, datetime, time, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import psycopg
from psycopg.rows import dict_row
import configparser
from pathlib import Path


class Config:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".kachna.conf"

        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {self.path}")

        self.cfg = configparser.ConfigParser()
        self.cfg.read(self.path)

    def get(self, section, key, fallback=None, *, required=False):
        value = self.cfg.get(section, key, fallback=fallback)

        if required and value is None:
            raise ValueError(f"Missing [{section}] {key} in config")

        if isinstance(value, str):
            value = value.strip().strip('"').strip("'")

        return value


class Function:
    def __init__(self):
        self.provider = None
        self.config = Config()
        self.name = None
        self.description = None
        self.questions = []
        self.params = []

        # executor
        self.db_host = None
        self.db_name = None
        self.db_user = None
        self.db_password = None
        self.sql_query = None
        self.readonly = True

        # output
        self.output_schema = {}

        # presentation
        self.format = None
        self.prompt = None
        self.advice = None

        self.confidence = 1.0
        self._confidence_override = None
        self.user_question = ""

    # ---- poskytovatel dat ----
    def setProvider(self, provider):
        self.provider = provider

    # ---- sql executor ----
    def setSQL(self, sql):
        self.setProvider(self._execute_sql)
        self.sql_query = sql

    # ---- name ----
    def setName(self, name):
        self.name = name

    # ---- description ----
    def setDescription(self, description):
        self.description = description

    # ---- questions ----
    def addQuestion(self, text):
        self.questions.append(text)

    def param(self, id, prompt, value=None):
        param_id = str(id).strip()
        if not param_id:
            raise ValueError("Parametr musí mít neprázdné id")
        if any(item["id"] == param_id for item in self.params):
            raise ValueError(f"Parametr '{param_id}' je definovaný vícekrát")
        self.params.append(
            {
                "id": param_id,
                "prompt": str(prompt),
                "value": value,
            }
        )

    # ---- database config ----
    def setDbHost(self, host):
        self.db_host = host

    def setDbDatabase(self, database):
        self.db_name = database

    def setDbUser(self, user):
        self.db_user = user

    def setDbPassword(self, password):
        self.db_password = password

    # ---- output ----
    def setOutput(self, schema):
        self.output_schema = schema

    # ---- presentation ----
    def setFormat(self, fmt):
        self.format = fmt

    def setPrompt(self, text):
        self.prompt = text.strip()

    def setAdvice(self, text):
        self.advice = text.strip()

    def setConfidence(self, value):
        self._confidence_override = float(value)
        self.confidence = self._confidence_override

    def _resolve_confidence(self, data):
        if self._confidence_override is not None:
            return self._confidence_override

        if isinstance(data, dict) and "confidence" in data:
            return float(data["confidence"])

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "confidence" in data[0]:
            return float(data[0]["confidence"])

        return 1.0

    def _json_default(self, value):
        if isinstance(value, (date, datetime, time)):
            return value.isoformat()
        if isinstance(value, timedelta):
            return str(value)
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    def _print_json(self, payload):
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=self._json_default))

    def _describe(self):
        self._print_json(
            {
                "name": self.name,
                "description": self.description,
                "questions": self.questions,
                "params": self.params,
            }
        )

    def _llm_base_url(self):
        llm_base = self.config.get("llm", "base_url")
        if llm_base:
            return llm_base.rstrip("/")

        chat_host = self.config.get("chat", "hostname")
        if chat_host:
            chat_port = self.config.get("chat", "port", "8097")
            return f"http://{chat_host}:{chat_port}"

        chat_host = self.config.get("chat", "hostname", "localhost")
        chat_port = self.config.get("chat", "port", "8097")
        return f"http://{chat_host}:{chat_port}"

    def _llm_api_key(self):
        return (
            self.config.get("chat", "api-key")
            or self.config.get("chat", "api-key")
            or self.config.get("llm", "api_key")
        )

    def _llm_model(self, base_url, headers):
        model = self.config.get("chat", "model") or self.config.get("chat", "model")
        if model:
            return model

        request = Request(f"{base_url}/v1/models", headers=headers, method="GET")
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        models = data.get("data") if isinstance(data, dict) else None
        if not isinstance(models, list) or not models:
            raise ValueError("LLM nevrátil žádný model")

        model_id = models[0].get("id") if isinstance(models[0], dict) else None
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("LLM model id je neplatný")

        return model_id

    def _call_completion(self, prompt):
        base_url = self._llm_base_url()
        api_key = self._llm_api_key()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        model = self._llm_model(base_url, headers)
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": 0,
            "max_tokens": 64,
        }
        body = json.dumps(payload).encode("utf-8")

        endpoints = ["/v1/completion", "/v1/completions"]
        last_error = None
        for endpoint in endpoints:
            request = Request(f"{base_url}{endpoint}", data=body, headers=headers, method="POST")
            try:
                with urlopen(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    choices = data.get("choices") if isinstance(data, dict) else None
                    if not isinstance(choices, list) or not choices:
                        raise ValueError("Completion nevrátil choices")
                    text = choices[0].get("text") if isinstance(choices[0], dict) else None
                    if not isinstance(text, str):
                        raise ValueError("Completion nevrátil text")
                    return text.strip().splitlines()[0]
            except HTTPError as exc:
                last_error = exc
                continue
            except URLError as exc:
                raise RuntimeError(f"Volání LLM selhalo: {exc}") from exc

        if last_error is not None:
            detail = last_error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM odpověděl chybou {last_error.code}: {detail}")
        raise RuntimeError("Volání LLM selhalo")

    def _resolve_params(self):
        if not self.params:
            return {}

        user_question = self.user_question
        values = {}
        for param in self.params:
            value = param.get("value")
            if value is None:
                prompt = str(param.get("prompt", "")).replace("{USER_QUESTION}", user_question)
                value = self._call_completion(prompt)
                param["value"] = value
            values[param["id"]] = value

        return values

    def _apply_sql_params(self, sql, params):
        resolved_sql = sql
        for key, value in params.items():
            placeholder = "{" + key + "}"
            if placeholder not in resolved_sql:
                continue
            quoted = "'" + value + "'"
            resolved_sql = resolved_sql.replace(placeholder, quoted)

        user_question = self.user_question.replace("'", "")
        resolved_sql = resolved_sql.replace("{USER_QUESTION}", user_question)

        unresolved = re.findall(r"\{([A-Za-z0-9_]+)\}", resolved_sql)
        if unresolved:
            missing = ", ".join(sorted(set(unresolved)))
            raise ValueError(f"Neznámé SQL parametry: {missing}")

        print (resolved_sql)

        return resolved_sql

    def _parse_cli_args(self):
        describe = False
        query = ""
        args = sys.argv[1:]
        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg == "--describe":
                describe = True
            elif arg == "--query" and idx + 1 < len(args):
                idx += 1
                query = args[idx]
            idx += 1

        return describe, query

    def _execute_sql(self):
        required = {
            "db_host": self.db_host,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "sql_query": self.sql_query,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        with psycopg.connect(
            host=self.db_host,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            row_factory=dict_row,
        ) as connection:
            params = self._resolve_params()
            query = self._apply_sql_params(self.sql_query, params)
            # print(query)
            with connection.cursor() as cursor:
                cursor.execute(query)
                if cursor.description is None:
                    return []
                rows = cursor.fetchall()

        if len(rows) == 1:
            return rows[0]
        return rows

    def exec(self):
        describe, query = self._parse_cli_args()
        self.user_question = query
        if describe:
            self._describe()
            return

        response = {
            "format": self.format,
            "prompt": self.prompt,
            "advice": self.advice,
            "confidence": self.confidence,
            "error": None,
            "data": None,
        }

        if not callable(self.provider):
            raise TypeError("Provider musí být callable")

        try:
            response["data"] = self.provider()
            response["confidence"] = self._resolve_confidence(response["data"])
        except Exception as exc:
            response["error"] = str(exc)

        self._print_json(response)
