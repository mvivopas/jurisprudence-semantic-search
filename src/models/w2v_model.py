import os
import pickle

import numpy as np
from gensim.models import Word2Vec

from ..data_preprocessor import JurisdictionPreprocessor
from .utils import CONFIG_PATH, read_config

class Word2VecModel():
    def __init__(self):
        self.processor = JurisdictionPreprocessor()
        self.paths = read_config(CONFIG_PATH)["general"]

    def fit_and_save(self,
                     data,
                     to_save=True):        
        # Read model parameter configuration
        params = read_config(CONFIG_PATH)["word2vec"]

        self.model = Word2Vec(data, 
                              size=params["size"], 
                              window=params["window"], 
                              min_count=params["min_count"], 
                              workers=params["workers"])
        
        if to_save:
            # Save model
            model_out = os.path.join(self.paths["model_path"], 
                                     params["model_file_name"])
            self.model.save(model_out)

            # Store just the words + their trained embeddings.
            vec_out = os.path.join(self.paths["embedding_path"], 
                                     params["vectors_file_name"])
            word_vectors = self.model.wv
            word_vectors.save(vec_out)