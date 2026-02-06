# kachna.py
import json

class Function:
    def __init__(self):
        self.name = None
        self.description = None
        self.questions = []

        # executor
        self.db_host = None
        self.db_name = None
        self.db_user = None
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

    # ---- descripiont ----
    def setDescription(self, description):
        self.description = description

    # ---- questions ----
    def addQuestion(self, text):
        self.questions.append(text)

    # ---- sql executor ----
    def setSQL(self, host, database, user, query, readonly=True):
        self.db_host = host
        self.db_name = database
        self.db_user = user
        self.sql_query = query.strip()
        self.readonly = readonly

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

    # ---- finalize ----
    def exec(self):
        definition = {
            "name": self.name,
            "description": self.description,
            "questions": self.questions,
            "executor": {
                "type": "sql",
                "host": self.db_host,
                "database": self.db_name,
                "user": self.db_user,
                "readonly": self.readonly,
                "query": self.sql_query,
            },
            "output": self.output_schema,
            "presentation": {
                "format": self.format,
                "prompt": self.prompt,
                "advice": self.advice,
            },
            "confidence": self.confidence,
        }

        print(json.dumps(definition, indent=2, ensure_ascii=False))

