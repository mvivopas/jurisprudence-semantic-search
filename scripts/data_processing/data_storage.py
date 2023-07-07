import json
import os
import sqlite3

import psycopg2
from numpy import array
from pandas import DataFrame

VECTOR_DB_SECRETS = "database_secrets.json"


class JurisdictionDataBaseManager():
    def __init__(self):
        pass

    def __call__(self, conn_type, table_path, data):
        # connect to DB
        self.generate_connection(conn_type)

        # create table for processed data
        self.create_table(table_path)

        table_name = os.path.basename(table_path).replace('.sql', '')
        try:
            if type(data) is DataFrame:
                data.to_sql(table_name,
                            self.connection,
                            if_exists='replace',
                            index=False)
            else:
                self.insert_embeddings_into_pgvector_table(table_name, data)

            self.connection.commit()
            self.exit_db()

        except Exception as error:
            self.exit_db()
            raise error

    def generate_connection(self, conn_type):
        # load db secrets
        with open(VECTOR_DB_SECRETS) as f:
            db_args = json.load(f)

        if conn_type == "pgvector":
            self.connection = psycopg2.connect(
                host="localhost",
                port=db_args["port"],
                database=db_args["database_name"],
                user=db_args["user"],
                password=db_args["password"],
            )
            self.cursor = self.connection.cursor()

        elif conn_type == "sqlite":
            self.connection = sqlite3.connect(db_args["database_name"])
            self.cursor = self.connection.cursor()

    def create_table(self, table_path):
        with open(table_path, 'r') as handle:
            self.cursor.execute(handle.read())

    def insert_embeddings_into_pgvector_table(self, table_name, vector_list):
        # SQL statement to insert vectors into the table
        sql = f"INSERT INTO {table_name} (vector) VALUES (%s)"
        # Execute the SQL statement with multiple sets of parameters
        self.cursor.executemany(sql, vector_list)

    def load_embeddings_from_pgvector_table(self,
                                            table_name,
                                            condition_ids=None):
        if condition_ids:
            condition_query = f"WHERE id = ANY(ARRAY{condition_ids})"
        else:
            condition_query = ""

        self.cursor.execute(
            f"SELECT id, vector FROM {table_name} {condition_query}")
        results = self.cursor.fetchall()
        ids = array([i[0] for i in results])
        embeddings = array([i[1] for i in results])
        return ids, embeddings

    def exit_db(self):
        self.cursor.close()
        self.conn.close()
