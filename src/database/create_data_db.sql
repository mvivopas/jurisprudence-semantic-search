CREATE TABLE IF NOT EXISTS sentence (
                                    id                INT PRIMARY KEY,
                                    year              INT,
                                    cuestiones        TEXT,
                                    materia           TEXT,
                                    parte_recurrente  TEXT,
                                    parte_recurrida   TEXT,
                                    first_fallo       INT,
                                    target_fallo      INT,
                                    costas_pro        INT,
                                    clean_fundamentos TEXT
                                    );