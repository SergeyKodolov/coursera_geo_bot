create table if not exists users (
    user_id int  primary key,
    radius int not null
);

create table if not exists locations (
    location_id serial primary key,
    title varchar(150) not null default 'Геопозиция',
    address varchar(500),
    location json,
    photo json,
    user_id int not null,
    foreign key (user_id)
        REFERENCES users (user_id)
            ON DELETE CASCADE
)