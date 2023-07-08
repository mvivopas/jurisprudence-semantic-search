DROP TABLE IF EXISTS wordvector;

CREATE TABLE wordvector (
    id SERIAL PRIMARY KEY,
    vector FLOAT[500]
);