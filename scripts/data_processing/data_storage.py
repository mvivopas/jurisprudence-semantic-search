import json
import sqlite3

import psycopg2

VECTOR_DB_SECRETS = "database_secrets.json"


class JurisdictionDataBaseManager():
    def __init__(self):
        pass

    def generate_sqlite_connection(self):
        # load db secrets
        with open(VECTOR_DB_SECRETS) as f:
            db_args = json.load(f)

        connection = sqlite3.connect(db_args["database_name"])
        cursor = connection.cursor()
        return connection, cursor

    def create_sqlite_table(self, cursor, table_path):
        with open(table_path, 'rb') as handle:
            cursor.execute(handle)

    def generate_pgvector_connection(self):
        # load db secrets
        with open(VECTOR_DB_SECRETS) as f:
            db_args = json.load(f)

        connection = psycopg2.connect(
            host="localhost",
            port=db_args["port"],
            database=db_args["database_name"],
            user=db_args["user"],
            password=db_args["password"],
        )
        cursor = connection.cursor()
        return connection, cursor

    def create_pgvector_table(self, cursor, table_path):
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
