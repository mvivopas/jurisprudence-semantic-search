import io
import re
import string
from typing import Optional

import nltk
import requests
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pdfminer3.converter import TextConverter
from pdfminer3.layout import LAParams
from pdfminer3.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer3.pdfpage import PDFPage

nltk.download('stopwords')

INFO_NOT_FOUND_STRING = 'Not provided'

# REGEX PATTERNS
CENDOJ_ID_PATTERN = re.compile(r'\d{20}')
DATE_PATTERN = re.compile(r'Fecha:\s(\d{2}/\d{2}/\d{4})')
RECURRING_PATTERN = re.compile(r'(?i)(Parte recurrente/Solicitante:|'
                               r'Parte recurrente|Procurador)')
FUNDAMENTOS_PATTERN = re.compile(
    r'(F\s?U\s?N\s?D\s?A\s?M\s?E\s?N\s?T\s?O\s?S|RAZONAMIENTOS JURÍDICOS)')
FALLO_PATTERN = re.compile(r'(F\W?A\W?L\W?L|PARTE DISPOSITIVA|'
                           r'P A R T E D I S P O S I T I V A|firmamos)')
COSTAS_PATTERN = re.compile(r'\bno\W+(?:\w+\W+){1,6}?costas\b')
SENTIDO_FALLO_PATTERN = re.compile(r'(?i)(desestim)')


class JurisdictionPreprocessor():
    def __init__(self):
        # define nlp object as lemmatizer
        self.nlp = spacy.load('es_core_news_sm')
        self.nlp.replace_pipe("lemmatizer", "es.lemmatizer")

    def __call__(self, url_doc):

        # Extract text from PDF url
        text = self.extract_text_from_link(url_doc)

        # Extract valuable information from document into dictionary
        dict_information = self.extract_information_from_doc(text)

        # Basic cleaning
        clean_corpus = self.basic_text_cleaning(
            dict_information["fundamentos"])

        # Tokenize and lemmatize
        std_corpus = self.tokenize_and_lemmatize_text(clean_corpus)
        dict_information["clean_fundamentos"] = std_corpus

        return dict_information

    def extract_text_from_link(self, url: str) -> str:
        """
        Extracts text from a PDF URL.

        Parameters:
            url (str): The URL of the PDF to extract text from.

        Returns:
            str: The extracted text from the PDF.
        """
        resource_manager = PDFResourceManager()

        fake_file_handle = io.StringIO()

        converter = TextConverter(resource_manager,
                                  fake_file_handle,
                                  laparams=LAParams())

        page_interpreter = PDFPageInterpreter(resource_manager, converter)

        response = requests.get(url)
        f = io.BytesIO(response.content)

        with f as fh:
            for page in PDFPage.get_pages(fh,
                                          caching=True,
                                          check_extractable=True):

                page_interpreter.process_page(page)

            doc = fake_file_handle.getvalue()

        converter.close()
        fake_file_handle.close()

        return doc

    def extract_section_content(self,
                                doc: str,
                                section_name: Optional[str] = None,
                                section_start_pos: Optional[int] = None,
                                section_end_pos: Optional[int] = None,
                                clean_text: bool = True) -> str:
        """
        Extracts the content under the specified section name from
        the document.

        Parameters:
            doc (str): The text of the document to extract information from.
            section_name (str): The name of the section to extract.

        Returns:
            str: The extracted content of the specified section or
                 INFO_NOT_FOUND_STRING if not found.
        """
        if section_name:
            start_section = doc.find(section_name, 0)

            if start_section == -1:
                return INFO_NOT_FOUND_STRING
            else:
                start_section += len(section_name)

        if section_start_pos:
            start_section = section_start_pos

        if section_end_pos:
            end_section = section_end_pos
        else:
            end_section = doc.find('\n', start_section)

        section_text = doc[start_section:end_section]

        if clean_text:
            section_text = re.sub(r'\W+', ' ', section_text).strip()

        return section_text

    def extract_information_from_doc(self, doc: str) -> dict:
        """
        Extracts information from the document that will be stored in the
        database.

        Parameters:
            doc (str): The text of the document to extract information from.

        Returns:
            dict: A dictionary containing extracted information with the
                    following keys:
                  - "id_cendoj": The CENDOJ id extracted from the document.
                  - "date": The date extracted from the document.
                  - "keyphrases": The content under the section "Cuestiones" in
                        the document.
                  - "recurring_part": The content under the section
                        "Parte recurrente/apelante" in the document.
                  - "appellant": The content under the section
                        "Parte recurrida/apelada" in document
                  - "factual_background": The content under the section
                        "Antecedentes de hecho" in the document.
                  - "factual_grounds": The content under the section
                        "Fundamentos" in the document.
                  - "first_verdict": The first fallo extracted from the
                        antecedentes section.
                  - "last_verdict": The fallo definitivo extracted from
                        the document.
                  - "legal_costs": A flag (1 or 0) indicating if
                        "Costas Procesales" were found in document.
        """
        dict_info = dict()

        # Retrieve CENDOJ id
        cendoj_id_match = CENDOJ_ID_PATTERN.search(doc).group()
        dict_info["id_cendoj"] = cendoj_id_match

        # Retrieve Litigation Date
        date_match = DATE_PATTERN.search(doc).group(1)
        dict_info["date"] = date_match

        # Retrieve Litigation Tematic
        dict_info["keyphrases"] = self.extract_section_content(
            doc, section_name="Cuestiones")

        # Retrieve Recurrent Entity
        recurring_ent_match = RECURRING_PATTERN.search(doc)
        if recurring_ent_match:
            rec_start_position = recurring_ent_match.span(1)[-1]
            recurring_ent_match = self.extract_section_content(
                doc, section_start_pos=rec_start_position)
        else:
            recurring_ent_match = INFO_NOT_FOUND_STRING

        dict_info["recurring_part"] = recurring_ent_match

        # Retrieve Apellant Entity
        dict_info["appellant"] = self.extract_section_content(
            doc, section_name="Parte recurrida")

        # Factual Background section
        background_str = 'ANTECEDENTES DE HECHO'
        match_new_facts = FUNDAMENTOS_PATTERN.search(doc)
        if match_new_facts:
            background_end_position = match_new_facts.span()[0]
            dict_info["factual_background"] = self.extract_section_content(
                doc,
                section_name=background_str,
                section_end_pos=background_end_position,
                clean_text=False)
        else:
            dict_info["factual_background"] = INFO_NOT_FOUND_STRING

        # Previous Verdict
        match_backgound_verdict = SENTIDO_FALLO_PATTERN.search(
            dict_info["factual_background"])
        # if pattern is found: first verdict -> dismiss (0) otherwise 1
        dict_info["first_verdict"] = 0 if match_backgound_verdict else 1

        # Factual Ground section
        match_last_verdict = FALLO_PATTERN.search(
            doc[background_end_position:])
        if match_new_facts and match_last_verdict:
            new_facts_start_position = match_new_facts.span()[1]
            verdict_start_position = match_last_verdict.span()[0]
            dict_info["factual_grounds"] = self.extract_section_content(
                doc,
                section_start_pos=new_facts_start_position,
                section_end_pos=verdict_start_position)
        else:
            dict_info["factual_grounds"] = INFO_NOT_FOUND_STRING

        # Verdict argumentation
        if match_last_verdict:
            dict_info["verdict_arguments"] = doc[match_last_verdict.span()[1]:]

        # Verdict position
        match_sentido_fallo_last = SENTIDO_FALLO_PATTERN.search(
            dict_info["verdict_arguments"])
        dict_info["last_verdict"] = 0 if match_sentido_fallo_last else 1

        # Costas Procesales
        match_costas = COSTAS_PATTERN.search(dict_info["verdict_arguments"])
        dict_info["legal_costs"] = 0 if match_costas else 1

        return dict_info

    def basic_text_cleaning(self, text):
        """
        Perform a basic cleaning of the document to remove
        unnecessary characters and standarize some common patterns.
        --> This function will render unnecessary with a sufficient
        amount of data
        """

        # num pag out
        text_clean = re.sub(r'(\n\d\n)', '', text)

        # ordered lists out
        text_clean = re.sub(r'(\n\d[\d]?\. | \d\.\-)', '', text_clean)

        # \x0c out
        text_clean = re.sub(r'(\x0c)', '', text_clean)

        # \n out
        text_clean = re.sub('\n', ' ', text_clean)

        # to lower case
        text_clean = text_clean.lower()

        # primero segundo tercero out
        text_clean = re.sub(
            r'(primero[\s]?(\.\-|\.)|segundo[\s]?(\.\-|\.)|'
            r'tercero[\s]?(\.\-|\.))', '', text_clean)

        # find all artículos
        text_clean = re.sub(
            r'(artículo[s]?|articulo[s]?|art\.|\bart\b|arts[.])', 'articulo',
            text_clean)

        # Find and Sub órganos judiciales por acrónimos ##
        # Sentencias / Tribunal Supremo
        text_clean = re.sub(r'sentencia[s]? de[l]? tribunal supremo', 'stjs',
                            text_clean)
        text_clean = re.sub(r'tribunal supremo', 'ts', text_clean)

        # Sentencia/Tribunal de Justicia de la Unión Europea
        text_clean = re.sub(r'tribunal de justicia de la unión europea',
                            'tjue', text_clean)

        # Ley de Enjuiciamiento Civil
        text_clean = re.sub(r'ley de enjuiciamiento civil', 'lec', text_clean)

        # Código Civil de Cataluña

        codigo_cat = [
            re.compile(r'cccat'),
            re.compile(r'código civil de catalunya'),
            re.compile(r'código civil de cataluña'),
            re.compile(r'cc de cataluña'),
            re.compile(r'cc de catalunya')
        ]

        for pattern in codigo_cat:
            text_clean = re.sub(pattern, 'ccat', text_clean)

        # código civil
        text_clean = re.sub(r'código civil|codigo civil', 'cc', text_clean)

        # Ley General para la Defensa de los Consumidores y Usuarios
        text_clean = re.sub(
            r'ley general para la defensa de los consumidores y usuarios',
            'lgdcu', text_clean)

        return text_clean

    def tokenize_and_lemmatize_text(self, text):
        """Tokenize text, remove stopwords, common punctuation and lemmatize"""
        # Import spanish stopwords
        spanish_stopwords = set(stopwords.words('spanish'))
        spanish_stopwords.discard("no")
        # Add punctuation to stopwords
        stop = set(spanish_stopwords + list(string.punctuation))
        # Tokenize and keep if not an stopword
        tokens = [i for i in word_tokenize(text.lower()) if i not in stop]
        # Lemmatization
        lemma_words = [word.lemma_ for word in self.nlp(' '.join(tokens))]
        # Join into a string
        lemma_text = ' '.join(lemma_words)

        return lemma_text
