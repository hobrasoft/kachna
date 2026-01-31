begin;

insert into versions values (3);

drop view if exists users_view cascade;

create view users_view as 

with admins as (
    select distinct on (uhr."user") uhr."user", ur.admin
        from user_roles ur
        left join user_has_role uhr using (user_role)
        where ur.admin
        order by uhr."user"
)


select u.*, coalesce(a.admin, false) as admin
    from users u
    left join admins a using ("user")
;

commit;


