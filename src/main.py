import json
from multiprocessing import Pool, cpu_count
from typing import Any, Callable

import numpy as np

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
    links_set = list(
        np.ravel(
            np.load(args["scrapper"]["output_path_pdf_links"],
                    allow_pickle=True))[0])

    # init preprocessor
    batch_size = args["preprocessor"]["batch_size"]
    preprocessor = JurisdictionPreprocessor()

    # init storage method
    sqlite_table_path = args["db"]["sqlite_table_path"]
    db_manager = JurisdictionDataBaseManager()

    # parallelize document processing and save by batches
    paralelize_doc_processing(db_manager, preprocessor, sqlite_table_path,
                              links_set, batch_size)

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


def process_and_save_batch(db_manager: Callable[[str, str, Any], None],
                           preprocessor: Callable[[Any], Any], table_path: str,
                           batch: Any) -> None:
    """
    Process a batch of data using a preprocessor and save it to a sqlite
    local data base.

    Args:
        db_manager (Callable[[str, str, Any], None]): A method that manages
            the database connection and insertion. Accepts the database
            type (e.g., 'sqlite'), table path, and data to be inserted.
        preprocessor (Callable[[Any], Any]): A method that processes a batch
            of documents. Accepts the batch of data and return the
            processed result.
        table_path (str): The path to the database table where the data will
            be saved.
        batch (Any): The batch of data to be processed and saved.

    Returns:
        None: This function doesn't return a value.
    """
    # Preprocess batch of documents
    df = preprocessor(batch)
    # Save batch
    db_manager("sqlite", table_path, df)


def paralelize_doc_processing(db_manager, preprocessor, sqlite_table_path,
                              links_set, batch_size):
    """
    Process and save batches of documents in parallel.

    Args:
        db_manager (Callable[[str, str, Any], None]): A method that manages the
            database connection and insertion. Accepts the database type
            (e.g., 'sqlite'), table path, and data to be inserted.
        preprocessor (Callable[[Any], Any]): A method that processes a batch of
            data. Accepts the batch of data and return the processed result.
        sqlite_table_path (str): The path to the SQLite database table where
            data will be saved.
        links_set (List[Any]): The list of document's links to be processed
            and saved.
        batch_size (int): The size of each batch for processing.

    Returns:
        None: This function doesn't return a value.
    """
    # Split the links_set into batches
    batches = [
        links_set[i:i + batch_size]
        for i in range(0, len(links_set), batch_size)
    ]

    # Create a multiprocessing pool to parallelize the processing and saving
    pool = Pool(processes=cpu_count())

    # Process and save batches in parallel
    pool.starmap(process_and_save_batch,
                 [(db_manager, preprocessor, sqlite_table_path, batch)
                  for batch in batches])

    # Close the multiprocessing pool
    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
