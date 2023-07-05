import json
import os
import sqlite3

import psycopg2
from pandas import DataFrame

VECTOR_DB_SECRETS = "database_secrets.json"


class JurisdictionDataBaseManager():
    def __init__(self):
        pass

    def __call__(self, conn_type, table_path, data):
        # connect to DB
        conn, cur = self.generate_connection(conn_type)

        # create table for processed data
        self.create_table(cur, table_path)

        table_name = os.path.basename(table_path).replace('.sql', '')
        try:
            if type(data) is DataFrame:
                data.to_sql(table_name, conn, if_exists='replace', index=False)
            else:
                self.insert_embeddings_into_pgvector_table(
                    cur, table_name, data)

            conn.commit()
            self.exit_db(conn, cur)

        except Exception as error:
            self.exit_db(conn, cur)
            raise error

    def generate_connection(self, conn_type):
        # load db secrets
        with open(VECTOR_DB_SECRETS) as f:
            db_args = json.load(f)

        if conn_type == "pgvector":
            connection = psycopg2.connect(
                host="localhost",
                port=db_args["port"],
                database=db_args["database_name"],
                user=db_args["user"],
                password=db_args["password"],
            )
            cursor = connection.cursor()

        elif conn_type == "sqlite":
            connection = sqlite3.connect(db_args["database_name"])
            cursor = connection.cursor()

        return connection, cursor

    def create_table(self, cursor, table_path):
        with open(table_path, 'r') as handle:
            cursor.execute(handle.read())

    def insert_embeddings_into_pgvector_table(self, cursor, table_name,
                                              vector_list):
        # SQL statement to insert vectors into the table
        sql = f"INSERT INTO {table_name} (vector) VALUES (%s)"
        # Execute the SQL statement with multiple sets of parameters
        cursor.executemany(sql, vector_list)

    def exit_db(self, conn, cursor):
        cursor.close()
        conn.close()
