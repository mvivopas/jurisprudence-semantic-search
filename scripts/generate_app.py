import os
import tempfile

import docx2txt
import faiss
import numpy as np
import PyPDF2
import streamlit as st
from data_processing.data_storage import JurisdictionDataBaseManager

from models.tfidf_model import TFIDFModel
from models.w2v_model import Word2VecModel

CURDIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(CURDIR, "data/models/vectorizer.pickle")

DICT_CATEGORY_MODEL = {"TfIdf": TFIDFModel(), "WordVector": Word2VecModel()}


def extract_text_from_pdf(file_path):
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        num_pages = len(reader.pages)
        text = ""
        for page in range(num_pages):
            text += reader.pages[page].extract_text()
        return text


def extract_text_from_docx(file_path):
    text = docx2txt.process(file_path)
    return text


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


def streamlit_app():
    """Streamlit app"""
    db_sqlite = JurisdictionDataBaseManager()
    db_sqlite.generate_connection("sqlite")

    st.title("Similar Document Search")

    st.write("Select a category")
    category = st.selectbox("categories", list(DICT_CATEGORY_MODEL))

    new_document = st.text_input("Enter a new document:")

    uploaded_file = st.file_uploader(
        "Upload a PDF or Word document", type=["pdf", "docx"]
    )

    number_results = st.text_input("Enter the number of results [1 - 50]:")

    if category and number_results and (new_document or uploaded_file):
        model = DICT_CATEGORY_MODEL.get(category)
        model.load()

        number_results = int(number_results)

        # Retrieve text from uploaded file
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file.seek(0)
                file_extension = uploaded_file.name.split(".")[-1]

                if file_extension == "pdf":
                    new_document = extract_text_from_pdf(tmp_file.name)
                elif file_extension == "docx":
                    new_document = extract_text_from_docx(tmp_file.name)
                else:
                    st.error(
                        "Invalid file format. " "Only PDF and DOCX files are supported."
                    )
                    return

        top_k_ids = perform_similarity_search(
            category, model, new_document, number_results
        )

        # retrieve document information for top results
        results = db_sqlite.load_data_from_table("sentence", "*", top_k_ids)

        # retrieve column names for retrieved info
        info_table = db_sqlite.get_query_data("PRAGMA table_info(sentence)")
        # Extract the column names from the results
        column_names = [result[1] for result in info_table]

        st.header("Similar documents:")
        for result in results:
            with st.container():
                st.subheader(f"__CENDOJ ID__: {result[0]}")
                for col, r in zip(column_names[2:], result[2:]):
                    st.write(f"__{col.capitalize()}__: {r}")

                with st.expander("View Document"):
                    st.write(result[1])


# Main function
def main():
    streamlit_app()


if __name__ == "__main__":
    main()
