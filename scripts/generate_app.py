import json
import os

import faiss
import numpy as np
import psycopg2
import streamlit as st

from ..models.tfidf_model import TFIDFModel

CURDIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(CURDIR, "data/models/vectorizer.pickle")
VECTOR_DB_SECRETS = "database_secrets.json"
TOP_K = 5


# Connect to the PostgreSQL database
def connect_to_database():
    # load scrapper arguments
    with open(VECTOR_DB_SECRETS) as f:
        db_args = json.load(f)

    conn = psycopg2.connect(
        host="localhost",
        port=db_args["port"],
        database=db_args["database_name"],
        user=db_args["user"],
        password=db_args["password"],
    )
    return conn


# Load the embeddings from the database
def load_embeddings_from_database(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, vector FROM tfidf_vectors")
    results = cur.fetchall()
    ids = np.array([i[0] for i in results])
    embeddings = np.array([i[1] for i in results])
    cur.close()
    return ids, embeddings


# Normalize the embeddings
def normalize_embeddings(embeddings):
    return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)


# Build the FAISS index
def build_faiss_index(embeddings, ids):
    index = faiss.IndexFlatIP(embeddings.shape[1])  # Cosine similarity index
    index.add(embeddings)
    return index


# Perform similarity search
def perform_similarity_search(index, model, query_text, k):
    query_embedding = model.get_query_embedding(query_text)
    # generate similarity scores and sorted index list
    sim_scores, idex_list = index.search(query_embedding, k)
    return idex_list


# Streamlit app
def streamlit_app(conn, index, model, k):
    st.title("Similar Document Search")
    st.write("Enter a new document:")
    new_document = st.text_input("")

    if st.button("Search"):
        cur = conn.cursor()
        top_k_ids = perform_similarity_search(index, model, new_document,
                                              k).tolist()[0]
        cur.execute(f"""SELECT id, vector
                FROM tfidf_vectors
                WHERE id = ANY(ARRAY{top_k_ids})""")
        similar_documents = cur.fetchall()
        cur.close()

        st.write("Similar documents:")
        for document in similar_documents:
            st.write(document[0])


# Main function
def main(top_k):
    conn = connect_to_database()
    ids, embeddings = load_embeddings_from_database(conn)
    index = build_faiss_index(embeddings, ids)

    # init model
    model = TFIDFModel(MODEL_PATH)
    # load the model
    model.load()

    streamlit_app(conn, index, model, top_k)


if __name__ == "__main__":
    main(TOP_K)
