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

    def exec(self):
        pass

