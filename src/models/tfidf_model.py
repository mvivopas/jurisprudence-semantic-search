import os
import pickle

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..data_preprocessor import JurisdictionPreprocessor
from .utils import CONFIG_PATH, read_config


class TFIDFModel():
    def __init__(self):
        self.processor = JurisdictionPreprocessor()
        self.paths = read_config(CONFIG_PATH)["general"]

    def fit_and_save(self, data, to_save=True):

        # Read model parameter configuration
        params = read_config(CONFIG_PATH)["tfidf"]

        # Create TFIDF matrix and model
        self.vectorizer = TfidfVectorizer(max_df=params["max_ratio"],
                                          min_df=params["min_ratio"],
                                          max_features=params["max_dim"])

        self.tfidf_vectors = self.vectorizer.fit_transform(data)

        if to_save:
            # save vectorizer
            model_out = os.path.join(self.paths["model_path"],
                                     params["model_file_name"])

            with open(model_out, 'wb') as handle:
                pickle.dump(self.vectorizer, handle)

            # save vectors
            vec_out = os.path.join(self.paths["embedding_path"],
                                   params["vectors_file_name"])
            embeddings = np.array(self.tfidf_vectors)
            np.save(vec_out, embeddings)

    def load(self):
        with open(self.model_path, 'rb') as handle:
            self.vectorizer = pickle.load(handle)

    def get_query_embedding(self, query_text):
        query_embedding = self.vectorizer.transform([query_text]).toarray()
        return query_embedding
