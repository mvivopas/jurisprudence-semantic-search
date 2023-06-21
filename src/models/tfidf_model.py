from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..data_preprocessor import JurisdictionPreprocessor


class TFIDFModel():
    def __init__(self, data):
        self.data = data
        self.processor = JurisdictionPreprocessor()

    def fit(self):
        # Get vocabulary as a set of words in all provided documents
        vocabulary = set(flatten(self.data))
        # Create TFIDF matrix and model
        self.vectorizer = TfidfVectorizer(vocabulary=vocabulary)
        self.tfidf_vectors = self.vectorizer.fit_transform(self.data)

    def find_most_similar_documents(self, textual_query, top_n=5):

        # preprocess query
        lemma_text = self.processor.tokenize_and_lemmatize_text(textual_query)
        # transform query to vector
        new_document_embedding = self.vectorizer.transform([lemma_text])
        # calculate cosine similarity
        similarities = cosine_similarity(new_document_embedding,
                                         self.tfidf_vectors).flatten()
        # get top n documents (with highest similarity score)
        top_indices = similarities.argsort()[-top_n:][::-1]
        top_documents = [self.data[i] for i in top_indices]

        return top_documents, top_indices


def flatten(lst):
    return [item for sublist in lst for item in sublist]
