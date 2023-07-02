
CREATE TABLE IF NOT EXISTS wordvector (
    id SERIAL PRIMARY KEY,
    vector FLOAT[500]
);