create table account(
    id serial primary key,
    user_id bigint,
    "service" varchar(255),
    "login" varchar(255),
    "password" bytea,
    password_salt bytea
);

create table "user"(
    id serial primary key,
    user_id bigint unique,
    password_hash bytea,
    password_hash_salt bytea
);
