
create table bookloader (
    id serial primary key,
    identifier text unique,
    status text default 'pending', -- one of 'pending', 'matched', 'resolved' or 'conflict'
    match_type text,
    match text,
    comments text
);

create index bookloader_match_type_idx on bookloader(match_type);
create index bookloader_status_idx on bookloader(status);
