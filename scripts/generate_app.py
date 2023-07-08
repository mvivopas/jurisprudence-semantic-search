import os

import faiss
import numpy as np
import streamlit as st
from data_processing.data_storage import JurisdictionDataBaseManager

from models.tfidf_model import TFIDFModel
from models.w2v_model import Word2VecModel

CURDIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(CURDIR, "data/models/vectorizer.pickle")
TOP_K = 5
METHOD = "tfidf"

DICT_CATEGORY_MODEL = {"TfIdf": TFIDFModel(), "WordVector": Word2VecModel()}


# Normalize the embeddings
def normalize_embeddings(embeddings):
    return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)


# Build the FAISS index
def build_faiss_index(embeddings, ids):
    # Cosine similarity index
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


# Perform similarity search
def perform_similarity_search(index, model, query_text, k):
    query_embedding = model.get_doc_vector(query_text)
    # generate similarity scores and sorted index list
    _, index_list = index.search(query_embedding, k)
    return index_list


# Streamlit app
def streamlit_app(db_manager, k):

    st.title("Similar Document Search")

    st.write("Select a category")
    category = st.selectbox("categories", list(DICT_CATEGORY_MODEL))

    new_document = st.text_input("Enter a new document:")

    # and st.button("Search")
    if category and new_document:
        model = DICT_CATEGORY_MODEL.get(category)
        model.load()

        ids, embeddings = db_manager.load_embeddings_from_pgvector_table(
            category.lower())
        index = build_faiss_index(embeddings, ids)

        top_k_ids = perform_similarity_search(index, model, new_document,
                                              k).tolist()[0]

        _, similar_documents = db_manager.load_embeddings_from_pgvector_table(
            category, top_k_ids)

        st.write("Similar documents:")
        for document in similar_documents:
            st.write(document[0])


# Main function
def main(top_k, method):
    db_manager = JurisdictionDataBaseManager()
    db_manager.generate_connection("pgvector")

    streamlit_app(db_manager, top_k)


if __name__ == "__main__":
    main(TOP_K, METHOD)
