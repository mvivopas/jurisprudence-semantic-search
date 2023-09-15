import json

from models.tfidf_model import TFIDFModel
from models.w2v_model import Word2VecModel
from scripts.data_processing.data_preprocessor import JurisdictionPreprocessor
from scripts.data_processing.data_scraper import JurisdictionScrapper
from scripts.data_processing.data_storage import JurisdictionDataBaseManager

ARGS_PATH = "arguments.json"


def main():

    # load scrapper arguments
    with open(ARGS_PATH) as f:
        args = json.load(f)

    # scrappe data
    scrapper = JurisdictionScrapper()
    scrapper(**args["scrapper"])

    # init storage method
    db_manager = JurisdictionDataBaseManager()

    # get links from scrapper
    db_manager.generate_connection("sqlite")
    res = db_manager.get_query_data("SELECT final_url from jurisprudence_urls")
    links_set = list(sum(res, ()))

    # parallelize document processing and save by batches
    batch_size = args["preprocessor"]["batch_size"]
    preprocessor = JurisdictionPreprocessor()
    preprocessor(links_set, batch_size)

    # retrieve back/ground data to generate the vector representation
    db_manager.generate_connection("sqlite")
    records = db_manager.load_data_from_table(
        "sentence", "factual_background,factual_grounds")

    # we are using summary of last trial + new trial for the similarity search
    data_2_vectorize = [a + f for a, f in records]

    pg_tables_path = args["db"]
    # generate TF-IDF model and vectors and save
    tfidf_model = TFIDFModel()
    tfidf_model.fit_and_save(data_2_vectorize,
                             table_path=pg_tables_path["pgv_tfidf_table_path"])

    # generate Word2Vec model and vectors and save
    w2v_model = Word2VecModel()
    w2v_model.fit_and_save(data_2_vectorize,
                           table_path=pg_tables_path["pgv_w2v_table_path"])


if __name__ == '__main__':
    main()
