import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_preprocessor import lemmatization


class TFIDFModel():
    def __init__(self):
        pass

    def __call__(self):
        pass

    def fit(self, data):

        vocabulary = set(flatten(data))
        vectorizer = TfidfVectorizer(vocabulary=vocabulary)
        tfidf_vectors = vectorizer.fit_transform(data)

        return vectorizer, tfidf_vectors

    def find_most_similar_documents(self,
                                    model,
                                    data,
                                    vectors,
                                    textual_query,
                                    top_n=5):

        # preprocess query
        preprocessed_query = re.sub(r'\W', ' ', textual_query).strip()
        lemma_text = ' '.join(lemmatization(preprocessed_query))

        # transform query to vector
        new_document_embedding = model.transform([lemma_text])
        similarities = cosine_similarity(new_document_embedding,
                                         vectors).flatten()
        top_indices = similarities.argsort()[-top_n:][::-1]
        top_documents = [data[i] for i in top_indices]

        return top_documents, top_indices


def flatten(lst):
    return [item for sublist in lst for item in sublist]
