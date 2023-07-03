import json

import pandas as pd

from models.tfidf_model import TFIDFModel
from models.w2v_model import Word2VecModel
from scripts.data_processing.data_preprocessor import JurisdictionPreprocessor
from scripts.data_processing.data_scrapper import JurisdictionScrapper
from scripts.data_processing.data_storage import JurisdictionDataBaseManager

ARGS_PATH = "arguments.json"


def main():

    # load scrapper arguments
    with open(ARGS_PATH) as f:
        args = json.load(f)

    # scrappe data
    scrapper = JurisdictionScrapper()
    links_set = scrapper(**args["scrapper"])

    # preprocess data
    preprocessor = JurisdictionPreprocessor()
    list_of_dict_info = [preprocessor(link_doc) for link_doc in links_set]
    df_records = pd.DataFrame(list_of_dict_info)

    # store data in DB
    sqlite_table_path = args["db"]["sqlite_table_path"]
    db_manager = JurisdictionDataBaseManager()

    # create table and insert data
    db_manager("sqlite", sqlite_table_path, df_records)

    # we are using fundamentos for the similarity search
    data = df_records["clean_fundamentos"].tolist()
    pg_tables_path = args["db"]
    # generate TF-IDF model and vectors and save
    tfidf_model = TFIDFModel()
    tfidf_model.fit_and_save(data,
                             table_path=pg_tables_path["pgv_tfidf_table_path"])

    # generate Word2Vec model and vectors and save
    w2v_model = Word2VecModel()
    w2v_model.fit_and_save(data,
                           table_path=pg_tables_path["pgv_w2v_table_path"])


if __name__ == '__main__':
    main()
