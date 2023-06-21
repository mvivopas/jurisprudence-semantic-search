import json

from src.data_scrapper import JurisdictionScrapper

SCRAPPER_ARGS_PATH = "scrapper_config.yaml"


def extract_data():
    
    # load scrapper arguments
    with open(SCRAPPER_ARGS_PATH) as f:
        args = json.load(f)
    
    # scrappe data
    scrapper = JurisdictionScrapper()
    scrapper(**args)





if __name__ == '__main__':
    extract_data()
