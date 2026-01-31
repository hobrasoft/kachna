from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import asyncpg

from .config import BackendConfig


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self._config.host,
                port=self._config.port,
                database=self._config.database,
                user=self._config.user,
                password=self._config.password,
            )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def get_user_by_login(self, login: str) -> asyncpg.Record | None:
        return await self.fetchrow(
            "select \"user\", name, login, password from users where login=$1",
            login,
        )

    async def get_user_roles(self, user_id: int) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select ur.user_role,
                   ur.system_prompt,
                   ur.abbr,
                   ur.name,
                   ur.admin
              from user_roles ur
              join user_has_role uhr on uhr.user_role = ur.user_role
             where uhr."user" = $1
             order by ur.name
            """,
            user_id,
        )

    async def list_user_system_prompts(self, user_id: int) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select distinct on (sp.system_prompt) sp.system_prompt, sp.text
              from system_prompts sp
              join user_roles ur on ur.system_prompt = sp.system_prompt
              join user_has_role uhr on uhr.user_role = ur.user_role
             where uhr."user" = $1
             order by sp.system_prompt, sp.name
            """,
            user_id,
        )

    async def list_users(self) -> list[asyncpg.Record]:
        return await self.fetch(
            "select \"user\", name, login from users order by name",
        )

    async def create_user(self, name: str, login: str, password: str) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into users (name, login, password)
            values ($1, $2, $3)
            returning "user", name, login
            """,
            name,
            login,
            password,
        )

    async def get_user(self, user_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            "select \"user\", name, login from users where \"user\"=$1",
            user_id,
        )

    async def get_user_with_password(self, user_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            "select \"user\", name, login, password from users where \"user\"=$1",
            user_id,
        )

    async def update_user(
        self,
        user_id: int,
        name: str,
        login: str,
        password: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update users
               set name=$1, login=$2, password=$3
             where "user"=$4
             returning "user", name, login
            """,
            name,
            login,
            password,
            user_id,
        )

    async def delete_user(self, user_id: int) -> str:
        return await self.execute("delete from users where \"user\"=$1", user_id)

    async def list_conversations(self, user_id: int) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select conversation, "user", date, title, removed
              from conversations
             where "user"=$1 and removed=false
             order by date desc, conversation desc
            """,
            user_id,
        )

    async def create_conversation(self, user_id: int, title: str) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into conversations ("user", date, title)
            values ($1, now(), $2)
            returning conversation, "user", date, title, removed
            """,
            user_id,
            title,
        )

    async def get_conversation(self, conversation_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select conversation, "user", date, title, removed
              from conversations
             where conversation=$1
            """,
            conversation_id,
        )

    async def update_conversation_title(
        self,
        conversation_id: int,
        title: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update conversations
               set title=$1
             where conversation=$2
            returning conversation, "user", date, title, removed
            """,
            title,
            conversation_id,
        )

    async def delete_conversation(self, conversation_id: int) -> str:
        return await self.execute(
            """
            update conversations
               set removed=true
             where conversation=$1
            """,
            conversation_id,
        )

    async def list_messages(self, conversation_id: int) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select message, conversation, role, date, "text", token_count
              from messages
             where conversation=$1
             order by date, message
            """,
            conversation_id,
        )

    async def create_message(
        self,
        conversation_id: int,
        role: str,
        text: str,
        token_count: int | None,
        embedding_value: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into messages (conversation, role, "text", token_count, embedding)
            values ($1, $2, $3, $4, $5::vector)
            returning message, conversation, role, date, "text", token_count
            """,
            conversation_id,
            role,
            text,
            token_count,
            embedding_value,
        )

    async def replace_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "delete from user_has_role where \"user\"=$1",
                    user_id,
                )
                if role_ids:
                    await connection.executemany(
                        "insert into user_has_role (\"user\", user_role) values ($1, $2)",
                        [(user_id, role_id) for role_id in role_ids],
                    )

    async def list_roles(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select user_role, system_prompt, abbr, name, admin
              from user_roles
             order by name
            """,
        )

    async def create_role(
        self,
        system_prompt: int,
        abbr: str,
        name: str,
        admin: bool,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into user_roles (system_prompt, abbr, name, admin)
            values ($1, $2, $3, $4)
            returning user_role, system_prompt, abbr, name, admin
            """,
            system_prompt,
            abbr,
            name,
            admin,
        )

    async def get_role(self, role_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select user_role, system_prompt, abbr, name, admin
              from user_roles
             where user_role=$1
            """,
            role_id,
        )

    async def update_role(
        self,
        role_id: int,
        system_prompt: int,
        abbr: str,
        name: str,
        admin: bool,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update user_roles
               set system_prompt=$1, abbr=$2, name=$3, admin=$4
             where user_role=$5
             returning user_role, system_prompt, abbr, name, admin
            """,
            system_prompt,
            abbr,
            name,
            admin,
            role_id,
        )

    async def delete_role(self, role_id: int) -> str:
        return await self.execute("delete from user_roles where user_role=$1", role_id)

    async def list_system_prompts(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select system_prompt, name, text
              from system_prompts
             order by name
            """,
        )

    async def create_system_prompt(self, name: str, text: str) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into system_prompts (name, text)
            values ($1, $2)
            returning system_prompt, name, text
            """,
            name,
            text,
        )

    async def get_system_prompt(self, system_prompt: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select system_prompt, name, text
              from system_prompts
             where system_prompt=$1
            """,
            system_prompt,
        )

    async def update_system_prompt(
        self,
        system_prompt: int,
        name: str,
        text: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update system_prompts
               set name=$1,
                   text=$2
             where system_prompt=$3
            returning system_prompt, name, text
            """,
            name,
            text,
            system_prompt,
        )

    async def delete_system_prompt(self, system_prompt: int) -> str:
        return await self.execute(
            "delete from system_prompts where system_prompt=$1",
            system_prompt,
        )

    async def list_topic_categories(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select topic_category, name, description
              from topic_categories
             order by name
            """,
        )

    async def create_topic_category(
        self,
        name: str,
        description: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into topic_categories (name, description)
            values ($1, $2)
            returning topic_category, name, description
            """,
            name,
            description,
        )

    async def get_topic_category(self, topic_category: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select topic_category, name, description
              from topic_categories
             where topic_category=$1
            """,
            topic_category,
        )

    async def update_topic_category(
        self,
        topic_category: int,
        name: str,
        description: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update topic_categories
               set name=$1, description=$2
             where topic_category=$3
             returning topic_category, name, description
            """,
            name,
            description,
            topic_category,
        )

    async def delete_topic_category(self, topic_category: int) -> str:
        return await self.execute(
            "delete from topic_categories where topic_category=$1",
            topic_category,
        )

    async def list_topics(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select topic, topic_category, text, embedding::text as embedding
              from topics
             order by topic
            """,
        )

    async def create_topic(
        self,
        topic_category: int,
        text: str,
        embedding_value: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into topics (topic_category, text, embedding)
            values ($1, $2, $3::vector)
            returning topic, topic_category, text, embedding::text as embedding
            """,
            topic_category,
            text,
            embedding_value,
        )

    async def get_topic(self, topic_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select topic, topic_category, text, embedding::text as embedding
              from topics
             where topic=$1
            """,
            topic_id,
        )

    async def update_topic(
        self,
        topic_id: int,
        topic_category: int,
        text: str,
        embedding_value: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update topics
               set topic_category=$1, text=$2, embedding=$3::vector
             where topic=$4
             returning topic, topic_category, text, embedding::text as embedding
            """,
            topic_category,
            text,
            embedding_value,
            topic_id,
        )

    async def delete_topic(self, topic_id: int) -> str:
        return await self.execute("delete from topics where topic=$1", topic_id)

    async def list_function_questions(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select function_question, function, text
              from functions_questions
             order by function_question
            """,
        )

    async def create_function_question(
        self,
        function_id: int,
        text: str,
        embedding_value: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into functions_questions ("function", text, embedding)
            values ($1, $2, $3::vector)
            returning function_question, "function", text
            """,
            function_id,
            text,
            embedding_value,
        )

    async def get_function_question(self, function_question_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select function_question, "function", text
              from functions_questions
             where function_question=$1
            """,
            function_question_id,
        )

    async def update_function_question(
        self,
        function_question_id: int,
        function_id: int,
        text: str,
        embedding_value: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update functions_questions
               set "function"=$1, text=$2, embedding=$3::vector
             where function_question=$4
             returning function_question, "function", text
            """,
            function_id,
            text,
            embedding_value,
            function_question_id,
        )

    async def delete_function_question(self, function_question_id: int) -> str:
        return await self.execute(
            "delete from functions_questions where function_question=$1",
            function_question_id,
        )

    async def list_functions(self) -> list[asyncpg.Record]:
        return await self.fetch(
            """
            select function, name, description, active, type, script
              from functions
             order by name
            """,
        )

    async def create_function(
        self,
        name: str,
        description: str,
        active: bool,
        type_value: str,
        script: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            insert into functions (name, description, active, type, script)
            values ($1, $2, $3, $4, $5)
            returning function, name, description, active, type, script
            """,
            name,
            description,
            active,
            type_value,
            script,
        )

    async def get_function(self, function_id: int) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            select function, name, description, active, type, script
              from functions
             where function=$1
            """,
            function_id,
        )

    async def update_function(
        self,
        function_id: int,
        name: str,
        description: str,
        active: bool,
        type_value: str,
        script: str,
    ) -> asyncpg.Record | None:
        return await self.fetchrow(
            """
            update functions
               set name=$1, description=$2, active=$3, type=$4, script=$5
             where function=$6
             returning function, name, description, active, type, script
            """,
            name,
            description,
            active,
            type_value,
            script,
            function_id,
        )

    async def delete_function(self, function_id: int) -> str:
        return await self.execute("delete from functions where function=$1", function_id)


def load_database() -> Database:
    config = DatabaseConfig(
        host=BackendConfig.dbHostname(),
        port=BackendConfig.dbPort(),
        database=BackendConfig.dbDatabase(),
        user=BackendConfig.dbUser(),
        password=BackendConfig.dbPassword(),
    )
    return Database(config)
