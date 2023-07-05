import os

import numpy as np
from gensim.models import Word2Vec

from scripts.data_processing.data_preprocessor import JurisdictionPreprocessor
from scripts.data_processing.data_storage import JurisdictionDataBaseManager

from .utils import CONFIG_PATH, read_config


class Word2VecModel():
    def __init__(self):
        self.processor = JurisdictionPreprocessor()
        self.paths = read_config(CONFIG_PATH)["general"]

        # Read model parameter configuration
        self.params = read_config(CONFIG_PATH)["word2vec"]
        self.model_path = os.path.join(self.paths["model_path"],
                                       self.params["model_file_name"])

    def fit_and_save(self, data, to_save=True, table_path=None):

        self.model = Word2Vec(data,
                              vector_size=self.params["size"],
                              window=self.params["window"],
                              min_count=self.params["min_count"],
                              workers=self.params["workers"])

        if to_save:
            # Save model
            self.model.save(self.model_path)

            # Store just the words + their trained embeddings.
            vec_out = os.path.join(self.paths["embedding_path"],
                                   self.params["vectors_file_name"])
            word_vectors = self.model.wv
            word_vectors.save(vec_out)

            if table_path:
                # save vectors into pgvector data base
                db_manager = JurisdictionDataBaseManager()
                db_manager("pgvector", table_path, word_vectors)

    def load(self):
        self.model = Word2Vec.load(self.model_path)
        self.index2word_set = set(self.model.wv.index2word)

    def get_query_embedding(self, query_text):
        query_embedding = np.zeros((self.model.vector_size, ), dtype='float32')
        query_text_list = query_text.split()
        word_count = 0
        for word in query_text_list:
            if word in self.index2word_set:
                word_count += 1
                query_embedding = np.add(query_embedding, self.model[word])
        if word_count > 0:
            query_embedding = np.divide(query_embedding, word_count)
        return query_embedding
