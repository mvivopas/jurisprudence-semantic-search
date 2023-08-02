import json

import numpy as np
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
    links_set = np.ravel(
        np.load(args["scrapper"]["output_path_pdf_links"],
                allow_pickle=True))[0]

    # # preprocess data
    preprocessor = JurisdictionPreprocessor()
    list_of_dict_info = [preprocessor(link_doc) for link_doc in links_set]
    df_records = pd.DataFrame(list_of_dict_info)

    # store data in DB
    sqlite_table_path = args["db"]["sqlite_table_path"]
    db_manager = JurisdictionDataBaseManager()

    # # create table and insert data
    db_manager("sqlite", sqlite_table_path, df_records)

    # we are using summary of last trial + new trial for the similarity search
    background_data = df_records["factual_background"].tolist()
    ground_data = df_records["factual_grounds"].tolist()
    data_2_vectorize = [a + f for a, f in zip(background_data, ground_data)]

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
