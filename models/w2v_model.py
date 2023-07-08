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

        data_list = [d.split() for d in data]

        self.model = Word2Vec(data_list,
                              vector_size=self.params["size"],
                              window=self.params["window"],
                              min_count=self.params["min_count"],
                              workers=self.params["workers"])

        if to_save:
            # Save model
            self.model.save(self.model_path)

            # Generate document vectorial representations
            doc_embeddings = [self.get_doc_vector(doc) for doc in data]

            # Store just the words + their trained embeddings.
            vec_out = os.path.join(self.paths["embedding_path"],
                                   self.params["vectors_file_name"])
            word_vectors = self.model.wv
            word_vectors.save(vec_out)

            if table_path:
                # format adequately to insert into db
                dense_vector_list = [[vec.tolist()] for vec in doc_embeddings]
                # save vectors into pgvector data base
                db_manager = JurisdictionDataBaseManager()
                db_manager("pgvector", table_path, dense_vector_list)

    def load(self):
        self.model = Word2Vec.load(self.model_path)
        # self.index2word_set = set(self.model.wv.index2word)

    def get_doc_vector(self, document):
        # Initialize an empty vector
        aggregate_vector = np.zeros(self.model.vector_size)
        word_list = document.split()
        word_count = 0

        # Iterate over each word in the document
        for word in word_list:
            if word in self.model.wv.key_to_index:
                # If the word is in the model's vocabulary
                # add its vector to the aggregate
                aggregate_vector += self.model.wv[word]
                word_count += 1

        # Average the aggregate vector by dividing by the word count
        if word_count > 0:
            aggregate_vector = np.divide(aggregate_vector, word_count)

        return aggregate_vector.reshape(1, len(aggregate_vector))
