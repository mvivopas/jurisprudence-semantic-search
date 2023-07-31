CREATE TABLE IF NOT EXISTS sentence (
                                    sentence_id          INT PRIMARY KEY,
                                    cendoj_id            TEXT,
                                    doc_date              INT,
                                    keyphrases           TEXT,
                                    recurring_part       TEXT,
                                    appellant            TEXT,
                                    factual_background   TEXT,
                                    factual_grounds      TEXT,
                                    verdict_arguments    TEXT,
                                    first_verdict        TEXT,
                                    last_verdict         TEXT,
                                    legal_costs          TEXT,
                                    link                 TEXT
                                    );