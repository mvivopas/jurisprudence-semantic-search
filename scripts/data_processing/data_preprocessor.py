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
PARTE_RECURRENTE_PATTERN = re.compile(r'(?i)(Parte recurrente/Solicitante:|'
                                      r'Parte recurrente|Procurador)')
FUNDAMENTOS_PATTERN = re.compile(
    r'(F\s?U\s?N\s?D\s?A\s?M\s?E\s?N\s?T\s?O\s?S|RAZONAMIENTOS JURÍDICOS)')
FALLO_PATTERN = re.compile(r'(?i)(F\W?A\W?L\W?L|PARTE DISPOSITIVA|'
                           r'P A R T E D I S P O S I T I V A|firmamos)')
COSTAS_PATTERN = re.compile(r'\bno\W+(?:\w+\W+){1,6}?costas\b')


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
                                section_name: Optional[str],
                                section_start_pos: Optional[int],
                                section_end_pos: Optional[int],
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
                  - "cuestiones": The content under the section "Cuestiones" in
                                  the document.
                  - "materia": The content under the section "Materia" in the
                               document.
                  - "parte_recurrente": The content under the section
                                        "Parte recurrente/apelante" in the
                                        document.
                  - "parte_recurrida": The content under the section
                                       "Parte recurrida/apelada" in document
                  - "antecedentes": The content under the section
                                    "Antecedentes de hecho" in the document.
                  - "fundamentos": The content under the section "Fundamentos"
                                   in the document.
                  - "first_fallo": The first fallo extracted from the
                                   antecedentes section.
                  - "target_fallo": The fallo definitivo extracted from
                                    the document.
                  - "costas_pro": A flag (1 or 0) indicating if
                                 "Costas Procesales" were found in document.
        """
        dict_info = dict()

        # CENDOJ id
        cendoj_id_match = CENDOJ_ID_PATTERN.search(doc).group()
        dict_info["id_cendoj"] = cendoj_id_match

        # Date
        date_match = DATE_PATTERN.search(doc).group(1)
        dict_info["date"] = date_match

        # Cuestiones part of document
        dict_info["cuestiones"] = self.extract_section_content(
            doc, section_name="Cuestiones")

        # Materia part of document
        dict_info["materia"] = self.extract_section_content(
            doc, section_name="Materia")

        # Parte recurrente/apelante part of document
        parte_recurrente_match = PARTE_RECURRENTE_PATTERN.search(doc)
        if parte_recurrente_match:
            start_recurrente = parte_recurrente_match.span(1)[-1]
            parte_recurrente_match = self.extract_section_content(
                doc, section_start_pos=start_recurrente)
        else:
            parte_recurrente_match = INFO_NOT_FOUND_STRING

        dict_info["parte_recurrente"] = parte_recurrente_match

        # Parte recurrida/apelada part of document
        dict_info["parte_recurrida"] = self.extract_section_content(
            doc, section_name="Parte recurrida")

        # Antecedentes de hecho part of document
        antecedentes_str = 'ANTECEDENTES DE HECHO'
        match_fundamentos = FUNDAMENTOS_PATTERN.search(doc)
        if match_fundamentos:
            end_antecedentes = match_fundamentos.span()[0]
            dict_info["antecedentes"] = self.extract_section_content(
                doc,
                section_name=antecedentes_str,
                section_end_pos=end_antecedentes,
                clean_text=False)
        else:
            dict_info["antecedentes"] = INFO_NOT_FOUND_STRING

        # Fundamentos part
        match_fallo = FALLO_PATTERN.search(doc)
        if match_fundamentos and match_fallo:
            start_fund = match_fundamentos.span()[1]
            start_fallo = match_fallo.span()[0]
            dict_info["fundamentos"] = self.extract_section_content(
                doc, section_start_pos=start_fund, section_end_pos=start_fallo)
        else:
            dict_info["fundamentos"] = INFO_NOT_FOUND_STRING

        # Fallo previo
        first_fallo = self.sentido_fallo(dict_info["antecedentes"])
        dict_info["first_fallo"] = first_fallo

        doc_fundamentos_fallo = doc[end_antecedentes:]
        # Fallo definitivo
        target_fallo = self.sentido_fallo(doc_fundamentos_fallo)
        dict_info["target_fallo"] = target_fallo

        # Costas Procesales
        costas_pro = 1
        if COSTAS_PATTERN.search(doc_fundamentos_fallo):
            costas_pro = 0

        dict_info["costas_pro"] = costas_pro

        return dict_info

    def sentido_fallo(self, fallo):
        if re.search(r'(?i)(desestim)', fallo):
            sentido_fallo = 0
        else:
            sentido_fallo = 1
        return sentido_fallo

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
