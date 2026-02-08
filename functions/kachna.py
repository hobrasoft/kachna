# kachna.py
import json
import sys
from datetime import date, datetime, time, timedelta
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

    # ---- poskytovatel dat ----
    def setProvider(self, provider):
        self.provider = provider

    # ---- name ----
    def setName(self, name):
        self.name = name

    # ---- description ----
    def setDescription(self, description):
        self.description = description

    # ---- questions ----
    def addQuestion(self, text):
        self.questions.append(text)

    # ---- database config ----
    def setDbHost(self, host):
        self.db_host = host

    def setDbDatabase(self, database):
        self.db_name = database

    def setDbUser(self, user):
        self.db_user = user

    def setDbPassword(self, password):
        self.db_password = password

    # ---- sql executor ----
    def setSQL(self, sql):
        self.setProvider(self._execute_sql)
        self.sql_query = sql

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
                "params": {},
            }
        )

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
            with connection.cursor() as cursor:
                cursor.execute(self.sql_query)
                if cursor.description is None:
                    return []
                rows = cursor.fetchall()

        if len(rows) == 1:
            return rows[0]
        return rows

    def exec(self):
        if len(sys.argv) > 1 and sys.argv[1] == "--describe":
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

