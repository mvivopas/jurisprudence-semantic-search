import sqlite3


class JurisdictionDataBaseManager():
    def __init__(self, table_name):
        self.table_name = table_name

    def __call__(self, record):

        create_db(self.table_name)

        connection = sqlite3.connect(self.table_name)

        print("Successfully Connected to SQLite")
        cursor = connection.cursor()

        try:
            insert_record_into_db(cursor, record)
            connection.commit()

        except sqlite3.Error as error:
            print("Failed to insert record into sqlite table", error)

        # NOTE: Place init conn and finish out of here also close connection
        cursor.close()


def create_db(table_name):
    # define connection and cursor and create table
    connection = sqlite3.connect(table_name)
    cursor = connection.cursor()

    sql_create_sentencias_table = """ CREATE TABLE IF NOT EXISTS sentencias (
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
                                        ); """

    cursor.execute(sql_create_sentencias_table)


# NOTE: Convert input in data type
def insert_record_into_db(cursor, id_cendoj, año, cuestiones, materia,
                          parte_recurrente, parte_recurrida, first_fallo,
                          target_fallo, costas_pro, fundamentos):

    sqlite_insert_with_param = """INSERT INTO sentencias
                          (id, year, cuestiones, materia, parte_recurrente,
                          parte_recurrida, first_fallo,
                          target_fallo, costas_pro, clean_fundamentos)
                           VALUES (?,?,?,?,?,?,?,?,?,?)"""

    data_tuple = (id_cendoj, año, cuestiones, materia, parte_recurrente,
                  parte_recurrida, first_fallo, target_fallo, costas_pro,
                  fundamentos)

    cursor.execute(sqlite_insert_with_param, data_tuple)
