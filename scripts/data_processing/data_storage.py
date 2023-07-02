import json
import os
import sqlite3

import psycopg2
from pandas import DataFrame

VECTOR_DB_SECRETS = "database_secrets.json"


class JurisdictionDataBaseManager():
    def __init__(self):
        pass

    def __call__(self, conn_type, table_path, embeddings):
        # connect to DB
        conn, cur = self.generate_connection(conn_type)

        # create table for processed data
        self.create_table(cur, table_path)

        table_name = os.path.basename(table_path).replace('.sql', '')
        if type(embeddings) is DataFrame:
            embeddings.to_sql(table_name, conn)
        else:
            self.insert_embeddings_into_pgvector_table(conn, cur, embeddings)

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
        with open(table_path, 'rb') as handle:
            cursor.execute(handle)

    def insert_embeddings_into_pgvector_table(self, conn, cursor, vector_list):
        # SQL statement to insert vectors into the table
        sql = "INSERT INTO tfidf_vectors (vector) VALUES (%s)"
        # Execute the SQL statement with multiple sets of parameters
        cursor.executemany(sql, vector_list)
        # Commit the changes to the database
        conn.commit()

    def exit_db(self, conn, cursor):
        cursor.close()
        conn.close()
