begin;

create extension if not exists vector;

/*
V tabulce se evidují veškeré databázové záplaty, které se na databázovou strukturu aplikovaly.
Záplaty mívají formát:
    begin;
    insert into versions (0);
    alter table ... příkazy pro záplatu
    commit;

Varianta pro opakovatelnou záplatu (obvykle pro ladění):
    begin;
    insert into versions (0) on conflict do nothing;
    alter table ... příkazy pro záplatu
    commit;

*/
CREATE TABLE versions (
    version INTEGER PRIMARY KEY,
    date timestamp with time zone not null default now()
);
comment on table versions is 'Verze databázové struktury, seznam aplikovaných patchů';
comment on column versions.version is 'číslo verze databáze nebo migrace';
comment on column versions.date is 'čas aplikace verze';

/*
Seznam uživatelů.
*/
CREATE TABLE users (
    "user"      integer primary key,
    name        text not null,
    login       text not null,
    password    text not null
);
comment on table users is 'Seznam uživatelů, důležité pro přihlášení';
comment on column users.user is 'identifikátor uživatele';
comment on column users.name is 'celé jméno uživatele';
comment on column users.login is 'přihlašovací jméno';
comment on column users.password is 'hash hesla uživatele';


/*
Seznam systémových promptů.
Promptem je zde myšlena první zpráva s rolí "system" posílaná v konverzaci do LLM.
Různé role mohou mít různé systémové prompty,
jiný prompt pro účetního, jiný pro ředitele, jiný pro vedoucího směny atd
*/
create table system_prompts (
    system_prompt   serial primary key,
    name            text not null,
   "text"           text not null
);
comment on table system_prompts is 'Seznam systémových promptů';
comment on column system_prompts.system_prompt is 'identifikátor řádku';
comment on column system_prompts.name is 'Jméno promptu, stručné označení';
comment on column system_prompts."text" is 'Celý text promptu';


/*
Seznam rolí pro uživatele.
Uživatel může mít více rolí.

Role slouží k nastavení přístupových práv k různým tématům a funkcím v db
*/
create table user_roles (
    user_role       serial primary key,
    system_prompt   integer not null references system_prompts(system_prompt) on update no action on delete no action,
    abbr            text not null,
    name            text not null,
    admin           boolean not null default false
);
comment on table user_roles is 'Seznam rolí pro uživatele. Podle rolí se řídí přístupová práva k různým funkcím v DB a tématům';


/*
Vazba mezi uživatelem a rolí.
Uživatel může mít více rolí.
*/
create table user_has_role (
    "user"      integer not null references users("user") on update cascade on delete cascade,
    "user_role" integer not null references user_roles("user_role") on update cascade on delete cascade,
    primary key ("user", "user_role")
);


/*
Seznam koverzací.
Konverzace se ukládají na serveru, dokud je uživatel nesmaže.
*/
CREATE TABLE conversations (
    conversation INTEGER PRIMARY KEY,
    "user" INTEGER NOT NULL references users("user") on update cascade on delete cascade,
    date TIMESTAMP NOT NULL,
    title TEXT NOT NULL,
    removed bool not null default false
);
comment on table conversations is 'Seznam konverzací, spojeno s uživatelem';
comment on column conversations.conversation is 'identifikátor konverzace';
comment on column conversations.user is 'uživatel, který konverzaci vedl';
comment on column conversations.date is 'čas založení konverzace';
comment on column conversations.title is 'název nebo shrnutí konverzace';
comment on column conversations.removed is 'zda byla konverzace skrytá nebo odstraněná';

/*
Zprávy v jednotlivých konverzacích.
Ukládá se celá konverzace, strana system, user i assistant
*/

CREATE TABLE messages (
    message         serial primary key,
    conversation    integer not null references conversations(conversation) on update cascade on delete cascade,
    role            text not null,
    date            timestamp with time zone NOT NULL default now(),
    "text"          text not null,
    token_count     int,
    embedding       vector(768) not null
);
comment on table messages is 'Obsah konverzací';
comment on column messages.message is 'identifikátor zprávy';
comment on column messages.conversation is 'vazba na konverzaci';
comment on column messages.role is 'role v rámci konverzace (user, assistant, system)';
comment on column messages.date is 'čas odeslání zprávy';
comment on column messages.text is 'text zprávy';
comment on column messages.token_count is 'počet tokenů zprávy';
comment on column messages.embedding is 'embedding zprávy pro sémantické porovnání';

/*
Seznam funkcí.
V seznamu se prohledává podle embeddingu.
Jakmile je funkce nalezena, podle typu se zavolá/provede příkaz ve sloupci script.
Pozor, funkce podléhá přístupovým právům podle role uživatele.
Viz tabulka role_has_function
*/
create table functions (
   "function"       serial primary key,
    name            text not null,
    description     text not null,
    active          boolean not null default true,
    type            text not null,
    script          text not null
);
comment on table functions IS 'Seznam známých funkcí, které lze vyvolat dotazem nebo přímo skriptem.';
comment on column functions.function is 'identifikátor funkce';
comment on column functions.name is 'název funkce';
comment on column functions.description is 'slovní popis funkce';
comment on column functions.active is 'zda je funkce aktivní';
comment on column functions.type is 'typ funkce (např. backend, agent)';
comment on column functions.script is 'skript nebo název volání';

/*
Které role mohou přistupovat k různým funkcím
*/
create table role_has_function (
    "user_role" integer not null references user_roles("user_role") on update cascade on delete cascade,
    "function"  integer not null references functions("function") on update cascade on delete cascade,
    primary key ("user_role", "function")
);
comment on table role_has_function is 'Které role mohou přistupovat k různým funkcím';
comment on column role_has_function.user_role is 'vazba na roli';
comment on column role_has_function.function  is 'vazba na funkci';


/*
Funkce samotná nemá vlastní embedding.
Ke každé funkci může vést celá řada různých dotazů, které se mohou embeddingem lišit.
Proto má každá funkce v této tabulce jeden či více embeddingů.
*/
create table functions_questions (
    function_question   serial primary key,
   "function"           integer not null references functions("function") on update cascade on delete cascade,
    embedding           vector(768) not null,
    "text"              text not null
);
comment on table functions_questions IS 'Příkladové formulace dotazů, které mapují na danou funkci. Obsahují embedding pro sémantické porovnání.';
comment on column functions_questions.function_question is 'identifikátor dotazu';
comment on column functions_questions.function is 'vazba na funkci';
comment on column functions_questions.embedding is 'embedding dotazu pro mapování na funkci';
comment on column functions_questions.text is 'formulace dotazu';


/*
Politiky pro přístup k různým tématům.
V tabulce je seznam různých reakcí, které může otevření nějakého tématu vyvolat.
*/
create table topic_policies (
    topic_policy        text primary key,
    name                text not null,
    policy              text                -- warn, restrict, ignore, log - jedno z toho
);
comment on table topic_policies is 'definice politik, jak zacházet s tematickými kategoriemi';
comment on column topic_policies.topic_policy is 'identifikátor politiky';
comment on column topic_policies.name is 'název politiky';
comment on column topic_policies.policy is 'Co se má udělat v případě aplikování politiky';


/*
Kategorie témat, například:
- porušuje soukromí
- obecné kecy
- firemní záležitosti
- politika
*/
create table topic_categories (
    topic_category      text primary key,
    name                text not null,
    description         text not null
);
comment on table topic_categories is 'tematické okruhy, každý napojen na konkrétní politiku';
comment on column topic_categories.topic_category is 'identifikátor kategorie tématu';
comment on column topic_categories.name is 'název kategorie';
comment on column topic_categories.description is 'popis kategorie';

/*
Tabulka vytváří vazbu mezi rolí uživatele, tématem a aplikovanou politikou:
    user_role, topic_category => topic_policies
Umožní to pro různé uživatelské role nastavit různé reakce na témata
*/
create table topic_categories_has_policies (
    user_role           integer not null references user_roles(user_role) on update cascade on delete cascade,
    topic_category      text not null references topic_categories(topic_category) on update cascade on delete cascade,
    topic_policy        text not null references topic_policies(topic_policy) on update no action on delete no action,
    primary key (user_role, topic_category)
);
comment on table topic_categories_has_policies is 'Vazba mezi rolí a kategorií tematu na politiku';
comment on column topic_categories_has_policies.topic_category is 'identifikátor kategorie tématu';
comment on column topic_categories_has_policies.user_role is 'identifikátor uživatelské role';
comment on column topic_categories_has_policies.topic_policy is 'identifikátor politiky';


/*
Okruhy témat, ke kterým je potřebné nějakým způsobem řídit přístupy.
Přístupy jsou usměrňovány rolemi.
Zde je seznam ebeddingů, které vedou na různá definovaná témata.
*/
create table topics (
    topic               serial primary key,
    topic_category      text not null references topic_categories(topic_category) on update cascade on delete cascade,
   "text"               text not null,
    embedding           vector(768) not null
);
comment on table topics is 'příkladové texty a embeddingy reprezentující konkrétní témata';
comment on column topics.topic is 'identifikátor vzoru tématu';
comment on column topics.topic_category is 'vazba na tematickou kategorii';
comment on column topics.text is 'příkladový text reprezentující dané téma';
comment on column topics.embedding is 'embedding vzoru pro vyhodnocování podobnosti';

insert into versions values (0);

commit;

