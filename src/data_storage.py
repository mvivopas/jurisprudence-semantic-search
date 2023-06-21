import sqlite3


class JurisdictionDataBaseManager():
    def __init__(self, table_name):
        self.table_name = table_name

    def generate_connection(self):
        connection = sqlite3.connect(self.table_name)
        cursor = connection.cursor()
        return connection, cursor

    def create_db(self):
        # define connection and cursor and create table
        connection = sqlite3.connect(self.table_name)
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

    # def insert_df_into_table(self, connection, df, table):
    #     df.to_sql(table, connection)
