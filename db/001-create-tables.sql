CREATE TABLE users (
    "user" INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    login TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE conversations (
    conversation INTEGER PRIMARY KEY,
    "user" INTEGER NOT NULL references conversations(conversation) on update cascade on delete cascade,
    date TIMESTAMP NOT NULL,
    title TEXT NOT NULL,
);

CREATE TABLE messages (
    message INTEGER PRIMARY KEY,
    conversation INTEGER NOT NULL references conversations(conversation) on update cascade on delete cascade,
    date TIMESTAMP with time zone NOT NULL default now(),
    message_text TEXT NOT NUL,
);

CREATE TABLE versions (
    version INTEGER PRIMARY KEY,
    date timestamp with time zone not null default now()
);
