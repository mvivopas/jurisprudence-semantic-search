import json

import streamlit as st
import faiss
import psycopg2
import numpy as np

EMBEDDING_PATH = "data/embeddings"
VECTOR_DB_SECRETS = "database_secrets.json"

# Connect to the PostgreSQL database
def connect_to_database():
    # load scrapper arguments
    with open(VECTOR_DB_SECRETS) as f:
        db_args = json.load(f)

    conn = psycopg2.connect(
        host="localhost",
        database=db_args["database_name"],
        user=db_args["user"],
        password=db_args["password"]
    )
    return conn

# Load the embeddings from the database
def load_embeddings_from_database(conn):
    cur = conn.cursor()
    cur.execute("SELECT vector FROM tfidf_vectors")
    embeddings = cur.fetchall()
    cur.close()
    return np.array(embeddings)

# Normalize the embeddings
def normalize_embeddings(embeddings):
    return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

# Build the FAISS index
def build_faiss_index(embeddings):
    index = faiss.IndexFlatIP(embeddings.shape[1])  # Cosine similarity index
    index.add(embeddings)
    return index

# Perform similarity search
def perform_similarity_search(index, query_embedding, k):
    normalized_query = query_embedding / np.linalg.norm(query_embedding)
    D, I = index.search(normalized_query, k)
    return I[0]

# Streamlit app
def streamlit_app(conn, index, k):
    st.title("Similar Document Search")
    st.write("Enter a new document:")
    new_document = st.text_input("")

    if st.button("Search"):
        cur = conn.cursor()
        cur.execute("SELECT document FROM documents WHERE id = ANY(%s)", 
                    (perform_similarity_search(index, new_document, k),))
        similar_documents = cur.fetchall()
        cur.close()

        st.write("Similar documents:")
        for document in similar_documents:
            st.write(document[0])

# Main function
def main():
    conn = connect_to_database()
    embeddings = load_embeddings_from_database(conn)
    normalized_embeddings = normalize_embeddings(embeddings)
    index = build_faiss_index(normalized_embeddings)

    k = 5  # Number of most similar documents to retrieve
    streamlit_app(conn, index, k)


if __name__ == "__main__":
    main()