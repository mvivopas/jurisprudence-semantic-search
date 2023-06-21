import sqlite3


class JurisdictionDataBaseManager():
    def __init__(self, db_name):
        self.db_name = db_name

    def generate_connection(self):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        return connection, cursor

    def create_db(self, table_name, cursor):

        sql_create_sentencias_table = f""" CREATE TABLE IF NOT EXISTS {table_name} (
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
