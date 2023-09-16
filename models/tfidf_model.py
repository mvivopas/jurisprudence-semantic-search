import os
import pickle

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts.data_processing.data_preprocessor import JurisdictionPreprocessor
from scripts.data_processing.data_storage import JurisdictionDataBaseManager

from .utils import CONFIG_PATH, read_config


class TFIDFModel:
    def __init__(self):
        self.processor = JurisdictionPreprocessor()
        self.paths = read_config(CONFIG_PATH)["general"]
        # Read model parameter configuration
        self.params = read_config(CONFIG_PATH)["tfidf"]

        self.model_path = os.path.join(
            self.paths["model_path"], self.params["model_file_name"]
        )

    def fit_and_save(self, data, to_save=True, table_path=None):
        # Create TFIDF matrix and model
        self.vectorizer = TfidfVectorizer(
            max_df=self.params["max_ratio"],
            min_df=self.params["min_ratio"],
            max_features=self.params["max_dim"],
        )

        self.tfidf_vectors = self.vectorizer.fit_transform(data)

        if to_save:
            # save vectorizer
            with open(self.model_path, "wb") as handle:
                pickle.dump(self.vectorizer, handle)

            # save vectors
            vec_out = os.path.join(
                self.paths["embedding_path"], self.params["vectors_file_name"]
            )
            embeddings = np.array(self.tfidf_vectors)
            np.save(vec_out, embeddings)

            if table_path:
                sparse_vectors = csr_matrix(embeddings.all())
                dense_vectors = sparse_vectors.toarray()
                # format adequately to insert into db
                dense_vector_list = [[vec.tolist()] for vec in dense_vectors]
                # save vectors into pgvector data base
                db_manager = JurisdictionDataBaseManager()
                db_manager("pgvector", table_path, dense_vector_list)

    def load(self):
        with open(self.model_path, "rb") as handle:
            self.vectorizer = pickle.load(handle)

    def get_query_vector(self, query_text):
        query_embedding = self.vectorizer.transform([query_text]).toarray()
        return query_embedding
