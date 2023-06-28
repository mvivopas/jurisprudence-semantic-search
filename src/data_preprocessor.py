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

    def extract_text_from_link(self, url):
        """Extract text from PDF url"""
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

        # CENDOJ id of the document
        pattern_id = re.search(r'(\d{20})', doc)
        id_cendoj = pattern_id.group()
        dict_info["id_cendoj"] = id_cendoj

        # Date
        start_año = doc.find('Fecha', 0) + 13
        end_año = doc.find('\n', start_año)
        año = int(doc[start_año:end_año])
        dict_info["year"] = año

        # Cuestiones part of document
        if doc[0:2000].find('Cuestiones', 0) != -1:
            start_cuest = doc.find('Cuestiones', 0) + 12
            end_cuest = doc.find('\n', start_cuest)
            cuestiones = doc[start_cuest:end_cuest]
        else:
            cuestiones = ""

        dict_info["cuestiones"] = cuestiones

        # Materia part of document
        start_materia = doc.find('Materia', 0) + 8
        end_materia = doc.find('\n', start_materia)
        materia = doc[start_materia:end_materia]
        dict_info["materia"] = materia

        # Parte recurrente/apelante part of document
        pattern_recurrente = [
            re.compile(r'(Parte recurrente/Solicitante:|Parte recurrente)'),
            re.compile(r'\nProcurador')
        ]

        if re.search(pattern_recurrente[0], doc):
            doc_loc_recurrente = [
                re.search(pattern_recurrente[0], doc).span()[1],
                re.search(pattern_recurrente[1], doc).span()[0]
            ]

            parte_recurrente = doc[int(doc_loc_recurrente[0]
                                       ):int(doc_loc_recurrente[1])]
        else:
            parte_recurrente = "not_found"

        dict_info["parte_recurrente"] = parte_recurrente

        # Parte recurrida/apelada part of document
        start_recurrida = doc.find('recurrida', 0) + 10
        end_recurrida = doc.find('\n', start_recurrida)
        parte_recurrida = doc[start_recurrida:end_recurrida]
        dict_info["parte_recurrida"] = parte_recurrida

        # Antecedentes de hecho part of document
        pattern_antecedentes = [
            re.compile(r'ANTECEDENTES DE HECHO'),
            re.compile(
                r'FUNDAMENTOS|F U N D A M E N T O S|RAZONAMIENTOS JURÍDICOS')
        ]

        doc_loc_antecedentes = [
            re.search(pattern_antecedentes[0], doc).span()[1],
            re.search(pattern_antecedentes[1], doc).span()[0]
        ]

        antecedentes = doc[int(doc_loc_antecedentes[0]
                               ):int(doc_loc_antecedentes[1])]

        dict_info["antecedentes"] = antecedentes

        # FUNDAMENTOS DE DERECHO
        pattern_fallo = [
            re.compile(r'F\W?A\W?L\W?L|PARTE DISPOSITIVA|'
                       r'P A R T E D I S P O S I T I V A'),
            re.compile(r'ﬁrmamos')
        ]

        fund_fallo = doc[doc_loc_antecedentes[1]:len(doc)]
        doc_loc_fundamentos = [
            re.search(pattern_antecedentes[1], fund_fallo).span()[1],
            re.search(pattern_fallo[0], fund_fallo).span()[0]
        ]

        fundamentos = fund_fallo[int(doc_loc_fundamentos[0]
                                     ):int(doc_loc_fundamentos[1])]

        dict_info["fundamentos"] = fundamentos

        # fallo previo
        first_fallo = self.sentido_fallo(antecedentes)
        dict_info["first_fallo"] = first_fallo

        # fallo definitivo
        target_fallo = self.sentido_fallo(fund_fallo)
        dict_info["target_fallo"] = target_fallo

        # costas procesales
        costas_pro = 1
        if re.search(r'\bno\W+(?:\w+\W+){1,6}?costas\b', fund_fallo):
            costas_pro = 0

        dict_info["costas_pro"] = costas_pro

        return dict_info

    def sentido_fallo(self, fallo):
        if re.search(r'[Dd][Ee][Ss][Ee][Ss][Tt][Ii][Mm]', fallo):
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
