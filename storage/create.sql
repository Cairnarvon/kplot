create table datasets (
    dataset_id serial primary key,
    title text,
    xlabel text,
    ylabel text
);

create table data (
    data_id bigint default date_part('epoch', now()) * 1000,
    updated timestamp default now(),
    dataset_id int references datasets(dataset_id),
    tag varchar(255),
    data text,
    primary key(data_id, dataset_id)
);
