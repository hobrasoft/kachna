begin;

insert into versions values (4);

create sequence if not exists conversations_conversation_seq;

select setval(
    'conversations_conversation_seq',
    coalesce((select max(conversation) from conversations), 0) + 1,
    false
);

alter table conversations
    alter column conversation set default nextval('conversations_conversation_seq');

alter sequence conversations_conversation_seq owned by conversations.conversation;

commit;
