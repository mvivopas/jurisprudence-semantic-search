# Jurisprudence Semantic Search Framework 📚🔦

![License](https://img.shields.io/badge/license-MIT-blue.svg)

This repository aims to reproduce all work from my [master's thesis](https://drive.google.com/file/d/17ZPYt94DdkMGd2I7hXkwi6o6qnQ9B0aa/view?usp=sharing).

**Jurisprudence Semantic Search** is a GitHub repository that houses a semantic search tool for legal documents. This tool allows users to perform similarity searches within a corpus of legal documents based on different vectorization techniques. It provides functionalities for data scraping, text processing, and vectorization, along with an interface to perform similarity searches.

#### Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The Jurisprudence Semantic Search repository is designed to enable legal professionals and researchers to search through a corpus of jurisprudence documents using advanced vectorization techniques. The repository provides different vectorization models, such as TF-IDF and Word2Vec, and stores the document corpus along with its vector representations in a PostgreSQL database and SQLite database.

The core functionalities of the repository include data scraping, text processing, vectorization, and similarity search interface. Users can easily configure the vectorization model parameters using the config.yaml file.

## Installation

To set up the Jurisprudence Semantic Search tool on your local machine, follow these steps:

1. Clone the repository:

````bash
$ git clone https://github.com/your-username/jurisprudence-semantic-search.git
````

2. Navigate to the repository directory:

````bash
$ cd jurisprudence-semantic-search
````

3. Create a virtual environment with python 3.10

````bash
# Create environment using conda
$ conda create --name juris python=3.10
$ conda activate juris
````

4. Install the required dependencies using pip:

````bash
$ pip install -r requirements.txt
````

5. Set up PostgreSQL

````bash
# Install using brew
$ brew install postgresql@14

# Run Server, I am using port 5433 but feel free to use another if
# this one is occupied in your PC
$ pg_ctl -D /opt/homebrew/var/postgresql@14 -o "-p 5433" start

# Start psql and open database postgres
$ psql postgres

# Create a role (user) with permissions to login (LOGIN) and create databases (CREATEDB)
postgres-# CREATE ROLE myuser WITH LOGIN;
postgres-# ALTER ROLE myuser CREATEDB;

# Quit psql
postgres-# \q

# On shell, open psql with postgres database with new user:
$ psql postgres -U myuser

# Create a database and grant all privileges to the user
postgres-> CREATE DATABASE mydatabase;
postgres-> GRANT ALL PRIVILEGES ON DATABASE mydatabase TO myuser;
````

Once PostgreSQL is working properly and a new user and database are created, to perform transactions with vectorial representations (inserts and selects), we will have to be connected to the server via the following command:

````bash
$ pg_ctl -D /opt/homebrew/var/postgresql@14 -o "-p 5433" -U myuser start
````

6. Install SQLite

````bash
$ brew install sqlite
````

7. Create a `database_secrets.json` in the repository root with content:

````
{
   "database_name":"mydatabase",
   "port": 5433,
   "user": "myuser",
   "password": "pass"
}
````

## File Structure

The repository has the following organization:

````
- db/
    - postgresql/
    - sqlite/
- models/
    - tfidf_model.py
    - word2vec_model.py
    - utils.py
    - config.yaml
- scripts/
    - generate_app.py
    - data_processing/
        - data_scrapper.py
        - data_preprocessor.py
        - data_storage.py
- src/
    - main.py
- requirements.txt
- README.md
- arguments.json
````

- `db/`: Contains folders for PostgreSQL and SQLite scripts to generate required tables.
- `models/`: Contains vectorization classes for TF-IDF and Word2Vec models. Also an _utils_ script with shared functions and a _config_ file that contains model parameter settings.
- `scripts/`: Contains the class scripts responsible of the retrieval, processing and storage of the data, as well as the script that holds the interface that works as a similarity search enginee.
   - `generate_app.py`: Starts a streamlit server, given a number of parameters, converts a textual query into a vectorial representation, compares it to the stored document representations and retrieves the most similar ones.
   - `data_scrapper.py`: Scrapes the CENDOJ platform retrieving all links to jurisprudence related to the parameters set in the _arguments_ file.
   - `data_preprocessor.py`: Extracts all text embedded in the link to the PDF and therefore selects and organizes relevant information to be saved. 
   - `data_storage.py`: Save all processed data in form of string and int into an SQLite database. Also helps easing transactions related to the database. Is used also for the same process but for the vectorial representations in PostgreSQL database.
- `src/`: Contains the _main_ script that executes the entire workflow to retrieve and save the data, fit the models and store the vector representations.
- `requirements.txt`: List of dependencies needed to run the tool.
- `arguments.json`: JSON file containing parameters used in main.py.


## Usage

To generate the aforementioned search enginee the steps to follow are:

1. Start PostgreSQL server

````bash
$ pg_ctl -D /opt/homebrew/var/postgresql@14 -o "-p 5433" -U myuser start
````

2. Customize the `arguments.json` file with the desired information you want to fill the data base with: textual query to obtain a jurisprudence tematic, date, number of searches...

3. Run the _main_ script

````bash
$ python main.py
````

4. Then simply run the interface script

````bash
$ python scripts/generate_app.py
````

And start performing queries to the enginee!


## Contributing

Contributions to this repository are welcome. If you find any bugs or have suggestions for improvements, feel free to create issues or pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

## Explanation

The generation of a jurisprudence similarity search engine involves three primary processes working together. Initially, it's essential to gather the relevant jurisprudence documents to populate the database. This database serves as the foundation from which the engine identifies the most similar documents based on their unique identifiers (IDs). This information is acquired through web scraping of the CENDOJ website. To accomplish this, the following sequential steps are undertaken:

1. **Data Collection (Web Scraping):** The first step involves collecting the necessary jurisprudence data to build the search engine's database. This data is sourced from the CENDOJ website using a web scraping tool. The tool, referred to as the "data_scraper," accesses the CENDOJ search platform and inputs specific parameters from the `arguments.json` file, such as dates and search queries. The search area for this explanation is set to Barcelona, although the user's ability to select locations might be added later. Given that each search returns a maximum of 200 documents, and to ensure comprehensive results, multiple searches are performed using the last jurisprudence date as a reference. Consequently, the total number of documents obtained is calculated as the "number of searches * 200."

2. **Scraping Jurisprudence Links:** The CENDOJ platform scraping process involves three critical stages: accessing the search site, extracting links to the embedded jurisprudence documents, and acquiring links to the final PDF versions. To obtain the final PDF link for a specific jurisprudence document, the process entails visiting the dynamic PDF link, extracting intermediate PDF links, and then accessing static PDF links that allow for text extraction. In essence, the scraper collects all available intermediate links to dynamic PDFs from the search platform, subsequently visiting each link to extract the static PDF link for comprehensive text scraping.

3. **Data Processing and Storage:** Once all static PDF links have been gathered, the data processing step begins, managed by the "data_preprocessor." This component's primary function is to extract textual content from the provided links, followed by the selection of pertinent information. The selected information is then stored in a localized SQLite database, ensuring accessibility for subsequent searches and analyses.

In summary, the creation of a jurisprudence similarity search engine involves collecting data from CENDOJ through web scraping, obtaining relevant PDF links, and then processing and storing the extracted information for future use.


<img src="images/scraping_explained.png" width="950" height="250" />*Visual explanation of all steps required to obtain the information that is stored into a local data base*





