# Jurisprudence Semantic Search Framework 📚🔦

![License](https://img.shields.io/badge/license-MIT-blue.svg)

This repository aims to reproduce all work from my [master's thesis](https://drive.google.com/file/d/17ZPYt94DdkMGd2I7hXkwi6o6qnQ9B0aa/view?usp=sharing).

**Jurisprudence Semantic Search** is a GitHub repository that houses a semantic search tool for legal documents. This tool allows users to perform similarity searches within a corpus of legal documents based on different vectorization techniques. It provides functionalities for data scraping, text processing, and vectorization, along with an interface to perform similarity searches.

Table of Contents

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
git clone https://github.com/your-username/jurisprudence-semantic-search.git
````

2. Navigate to the repository directory:

````bash
cd jurisprudence-semantic-search
````

3. Install the required dependencies using pip:

````bash
pip install -r requirements.txt
````

Set up the PostgreSQL and SQLite databases by running the scripts in the db folder. Please ensure you have both PostgreSQL and SQLite installed and configured on your system.
Prepare the necessary data by running the data scraping and processing classes. Modify the parameters in the arguments.json file as needed.

## Usage

The Jurisprudence Semantic Search tool consists of several components, each serving a specific purpose:

#### <u>Data Scraping</u>

The `data_scraper.py` script handles the web scraping of jurisprudence documents from relevant sources.

#### <u>Text Processing</u>

The `data_preprocessor.py` script extracts text from embedded PDF files, processes the textual data, and prepares it for vectorization.

#### <u>Data Storage</u>

The `data_storage.py` script stores the processed textual data into the PostgreSQL and SQLite databases.

#### <u>Vectorization Models</u>

The models folder contains classes for different vectorization techniques, such as TF-IDF and Word2Vec.

#### <u>Semantic Search Interface</u>

The generate_app.py script allows users to perform similarity searches within the corpus using the pre-trained vector representations.

To execute the entire workflow, run the main.py script located in the src folder. This script will execute data scraping, text processing, data storage, and vectorization sequentially.

````bash
python src/main.py
````

The script will save the vector representations of the documents into the respective tables in the databases.

## File Structure

The repository has the following file structure:

````
- db/
    - postgresql/
    - sqlite/
- models/
    - tfidf.py
    - word2vec.py
- scripts/
    - generate_app.py
- data_processing/
    - data_scraper.py
    - data_preprocessor.py
    - data_storage.py
- src/
    - main.py
- config.yaml
- utils.py
- requirements.txt
- README.md
- arguments.json
````

- `db/`: Contains folders for PostgreSQL and SQLite scripts to generate required tables.
- `models/`: Contains vectorization classes for TF-IDF and Word2Vec.
- `scripts/`: Holds the interface script generate_app.py for similarity search.
- `data_processing/`: Contains classes for data scraping, text processing, and data storage.
- `src/`: Contains the main script main.py that executes the entire workflow.
- `config.yaml`: Configuration file for setting model parameters.
- `utils.py`: Shared utility functions.
- `requirements.txt`: List of dependencies needed to run the tool.
- `arguments.`json: JSON file containing parameters used in main.py.

## Contributing

Contributions to this repository are welcome. If you find any bugs or have suggestions for improvements, feel free to create issues or pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
