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

DICT_CATEGORY_MODEL = {"TfIdf": TFIDFModel(), "WordVector": Word2VecModel()}


def normalize_embeddings(embeddings):
    """Normalize the embeddings"""
    return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)


def build_faiss_index(embeddings, ids):
    """Build the FAISS index"""
    # Cosine similarity index
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def perform_similarity_search(category, model, query_text, k):
    """Perform similarity search"""
    db_pgvec = JurisdictionDataBaseManager()
    db_pgvec.generate_connection("pgvector")

    result = db_pgvec.load_data_from_table(category.lower(), "id, vector")

    ids, embeddings = zip(*result)
    index = build_faiss_index(np.array(embeddings), np.array(ids))

    query_embedding = model.get_query_vector(query_text)

    # generate similarity scores and sorted index list
    _, index_list = index.search(query_embedding, k)
    index_list = index_list.tolist()[0]
    return index_list


def streamlit_app(k):
    """Streamlit app"""
    db_sqlite = JurisdictionDataBaseManager()
    db_sqlite.generate_connection("sqlite")

    st.title("Similar Document Search")

    st.write("Select a category")
    category = st.selectbox("categories", list(DICT_CATEGORY_MODEL))

    new_document = st.text_input("Enter a new document:")

    # and st.button("Search") --for debug mode deactivate
    if category and new_document:
        model = DICT_CATEGORY_MODEL.get(category)
        model.load()

        top_k_ids = perform_similarity_search(category, model, new_document, k)

        result = db_sqlite.load_data_from_table("sentence",
                                                "id, clean_fundamentos",
                                                top_k_ids)
        ids, corpus = zip(*result)

        st.write("Similar documents:")
        for id_, doc in zip(ids, corpus):
            descr = f"""__CENDOJ ID__: {id_} ---
                        __INTRO__: {doc[:20]}"""
            with st.expander(descr):
                st.write(doc)


# Main function
def main(top_k):
    streamlit_app(top_k)


if __name__ == "__main__":
    main(TOP_K)
