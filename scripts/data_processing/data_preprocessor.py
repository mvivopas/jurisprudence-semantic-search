import io
import re
import string

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

    def extract_information_from_doc(self, doc):
        """Extract information from document that will
        be stored in the database"""
        dict_info = dict()

        # CENDOJ id
        cendoj_id_match = CENDOJ_ID_PATTERN.search(doc).group()
        dict_info["id_cendoj"] = cendoj_id_match

        # Date
        date_match = DATE_PATTERN.search(doc).group(1)
        dict_info["date"] = date_match

        # Cuestiones part of document
        cuestiones_str = 'Cuestiones'
        if doc[:2000].find(cuestiones_str, 0) != -1:
            start_cuest = doc.find(cuestiones_str, 0) + len(cuestiones_str)
            end_cuest = doc.find('\n', start_cuest)
            cuestiones = re.sub(r'\W+', ' ',
                                doc[start_cuest:end_cuest]).strip()
        else:
            cuestiones = INFO_NOT_FOUND_STRING

        dict_info["cuestiones"] = cuestiones

        # Materia part of document
        materia_str = 'Materia'
        match_materia = doc.find(materia_str, 0)
        if match_materia == -1:
            materia = INFO_NOT_FOUND_STRING
        else:
            start_materia = match_materia + len(materia_str)
            end_materia = doc.find('\n', start_materia)
            materia = re.sub(r'\W+', ' ',
                             doc[start_materia:end_materia]).strip()

        dict_info["materia"] = materia

        # Parte recurrente/apelante part of document
        parte_recurrente_match = PARTE_RECURRENTE_PATTERN.search(doc)
        if parte_recurrente_match:
            start_recurrente = parte_recurrente_match.span(1)[-1]
            end_recurrente = doc.find('\n', start_recurrente)
            recurrente = doc[start_recurrente:end_recurrente]
            parte_recurrente_match = re.sub(r'\W+', ' ', recurrente).strip()
        else:
            parte_recurrente_match = INFO_NOT_FOUND_STRING

        dict_info["parte_recurrente"] = parte_recurrente_match

        # Parte recurrida/apelada part of document
        recurrida_str = 'Parte recurrida'
        match_recurrida = doc.find(recurrida_str, 0)
        if match_recurrida == -1:
            parte_recurrida = INFO_NOT_FOUND_STRING
        else:
            start_recurrida = match_recurrida + len(recurrida_str)
            end_recurrida = doc.find('\n', start_recurrida)
            parte_recurrida = doc[start_recurrida:end_recurrida]

        dict_info["parte_recurrida"] = parte_recurrida

        # Antecedentes de hecho part of document
        antecedentes_str = 'ANTECEDENTES DE HECHO'
        match_antec = doc.find(antecedentes_str, 0)
        match_fundamentos = FUNDAMENTOS_PATTERN.search(doc)
        if match_antec == -1:
            antecedentes = INFO_NOT_FOUND_STRING
        else:
            start_antecedentes = match_antec + len(antecedentes_str)
            end_antecedentes = match_fundamentos.span()[0]
            antecedentes = doc[start_antecedentes:end_antecedentes]

        dict_info["antecedentes"] = antecedentes

        # Fundamentos part
        match_fallo = FALLO_PATTERN.search(doc)
        fundamentos = doc[match_fundamentos.span()[1]:match_fallo.span()[0]]
        dict_info["fundamentos"] = fundamentos

        # Fallo previo
        first_fallo = self.sentido_fallo(antecedentes)
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
