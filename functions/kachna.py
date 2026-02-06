# kachna.py
import csv
import io
import json
import os
import subprocess
import sys


class Function:
    def __init__(self):
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
        self.confidence = float(value)

    def _print_json(self, payload):
        print(json.dumps(payload, ensure_ascii=False, indent=2))

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

        env = os.environ.copy()
        if self.db_password is not None:
            env["PGPASSWORD"] = self.db_password

        result = subprocess.run(
            [
                "psql",
                "-h",
                self.db_host,
                "-U",
                self.db_user,
                self.db_name,
                "--csv",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                self.sql_query,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=True,
        )

        output = result.stdout.strip()
        if not output:
            return []

        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
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

        try:
            response["data"] = self._execute_sql()
        except Exception as exc:
            response["error"] = str(exc)

        self._print_json(response)
