-- 018_user_accounts: named sign-in accounts, created by an administrator (docs/decisions.md,
-- D-056).
--
-- As for the .env account since 016 (D-053), a named account's sign-in name is kept in
-- app_user.email; a named account also has a scrypt password_hash (the .env account
-- and the built-in local user have none). Accounts are switched off (is_active), never
-- deleted: decisions and the audit trail point at them.
alter table app_user add column if not exists created_by uuid references app_user;
create index if not exists app_user_created_by on app_user (created_by);
-- Sign-in names are unique ignoring case.
create unique index if not exists app_user_email_lower on app_user (lower(email));
