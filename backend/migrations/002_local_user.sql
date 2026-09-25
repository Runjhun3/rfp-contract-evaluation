-- 002_local_user: the app runs without login (docs/decisions.md, D-no-login).
-- Every action is recorded against this one built-in user, so created_by /
-- approved_by / reviewer keep pointing at a real app_user row.
insert into app_user (user_id, email, full_name, role)
values ('00000000-0000-0000-0000-000000000001', 'local', 'Local user', 'ADMIN')
on conflict (user_id) do nothing;
