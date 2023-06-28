import pickle

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..data_preprocessor import JurisdictionPreprocessor


class TFIDFModel():
    def __init__(self, model_path):
        self.processor = JurisdictionPreprocessor()
        self.model_path = model_path

    def fit_and_save(self,
                     data,
                     max_ratio=0.9,
                     min_ratio=0.1,
                     max_dim=800,
                     to_save=True,
                     out_vecs=None):
        # Create TFIDF matrix and model
        self.vectorizer = TfidfVectorizer(max_df=max_ratio,
                                          min_df=min_ratio,
                                          max_features=max_dim)

        self.tfidf_vectors = self.vectorizer.fit_transform(self.data)

        if to_save:
            # save vectorizer
            with open(self.model_path, 'wb') as handle:
                pickle.dump(self.vectorizer, handle)

            if out_vecs:
                # save vectors
                embeddings = np.array(self.tfidf_vectors)
                np.save(out_vecs, embeddings)

    def load(self):
        with open(self.model_path, 'rb') as handle:
            self.vectorizer = pickle.load(handle)

    def get_query_embedding(self, query_text):
        query_embedding = self.vectorizer.transform([query_text]).toarray()
        return query_embedding
