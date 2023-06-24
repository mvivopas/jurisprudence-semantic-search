import json
import os

import pandas as pd
import numpy as np

from src.data_preprocessor import JurisdictionPreprocessor
from src.data_scrapper import JurisdictionScrapper
from src.data_storage import JurisdictionDataBaseManager
from src.models.tfidf_model import TFIDFModel

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
    table_name = args["db"]["table_name"]
    db_manager = JurisdictionDataBaseManager(args["db"]["schema_name"])

    # connect to DB
    conn, cur = db_manager.generate_connection()
    # create table
    db_manager.create_db(table_name, cur)
    # insert data
    df_records.to_sql(table_name, conn)

    data = df_records["clean_fundamentos"].tolist()

    # generate TF-IDF model and vectors and save
    tfidf_model = TFIDFModel(data)
    tfidf_model.fit()

    out_path = os.path.join(args["embeddings"]["ouput_path"], 
                            "tfidf_embeddings.npy")
    embeddings = np.array(tfidf_model.tfidf_vectors)
    np.save(out_path, embeddings)


if __name__ == '__main__':
    main()
