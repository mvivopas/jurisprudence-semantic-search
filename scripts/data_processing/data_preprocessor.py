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
FACTUAL_GROUND_HEADER_PATTERN = re.compile(
    r'(F\s?U\s?N\s?D\s?A\s?M\s?E\s?N\s?T\s?O\s?S|RAZONAMIENTOS JURÍDICOS)')
VERDICT_HEADER_PATTERN = re.compile(
    r'(F\s?A\s?L\s?L|PARTE DISPOSITIVA|'
    r'P A R T E D I S P O S I T I V A|firmamos)')
VERDICT_RESULT_PATTERN = re.compile(
    r'(?i)\W(des)?estim\w+\s(parcial|en\sparte)?')

FACTUAL_BACKGROUND_HEADER = 'ANTECEDENTES DE HECHO'
KEYPHRASE_TITLE = 'Cuestiones'
APELLANT_TITLE = 'Parte recurrida'

LEGAL_COSTS_MATCHER = {
    'C1':
    re.compile(r'(?i)(conden\w+|impo\w+|pago).{1,40}costas.{1,3}'
               r'(de primera instancia|de la demanda reconvencional)'),
    'C2':
    re.compile(r'(conden\w+|impo\w+|pago)\sde\scostas\sen\sesta\sinstancia')
}


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

        # NOTE: Create func to clean page numeration and JURISPRUDENCIA words

        # Add url to doc into document information
        dict_information["doc_url"] = url_doc

        # Tokenize and lemmatize
        # std_corpus = self.tokenize_and_lemmatize_text(clean_corpus)
        # dict_information["clean_fundamentos"] = std_corpus

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

    def retrieve_verdict_result(self, verdict_section: str) -> str:
        """
        Retrieves the verdict result from the given verdict_section.

        The function searches for the verdict result pattern in the
        provided verdict_section and then determines the type of verdict
        based on the result text.

        Parameters:
            verdict_section (str): The text containing the verdict result.

        Returns:
            str: The type of verdict represented by a single character:
                 - 'D': Represents 'Desestimado' (Unfavorable).
                 - 'EP': Represents 'Estimado Parcialmente'
                        (Partially Favorable).
                 - 'E': Represents 'Estimado' (Favorable).
                 - If the verdict result is not found, returns
                        INFO_NOT_FOUND_STRING.
        """
        match_verdict_result = VERDICT_RESULT_PATTERN.search(verdict_section)

        if match_verdict_result:
            verdict_result_txt = match_verdict_result.group().lower()
            if 'des' in verdict_result_txt:
                result = 'D'
            elif ' par' in verdict_result_txt:
                result = 'EP'
            else:
                result = 'E'
        else:
            result = INFO_NOT_FOUND_STRING

        return result

    def retrieve_litigation_costs(self, section: str) -> str:
        """
        Retrieves the litigation costs from the specified section.

        The function searches for various legal costs patterns in the
        given section. If any of the patterns are found and not negated
        (i.e., "sin" not present before the match), the corresponding legal
        cost is added to the result string. If no valid legal costs are found,
        'NC' (No Costs) is returned.

        Parameters:
            section (str): The text containing the relevant section of the
                           document where the legal costs are located.

        Returns:
            str: A string representing the legal costs from the section.
                 If no valid legal costs are found, 'NC' (No Costs) is returned
        """
        # Match legal costs pattern
        result = ''

        for pat in list(LEGAL_COSTS_MATCHER):
            match_costs = LEGAL_COSTS_MATCHER[pat].search(section)
            if match_costs:
                # If not negated, proceed to assign costs
                match_pos_start_bf = min(0, match_costs.span()[0] - 15)
                match_str_bf = section[match_pos_start_bf:match_costs.span(
                )[0]]
                if 'sin ' not in match_str_bf:
                    result += pat

        if result == '':
            result = 'NC'

        return result

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
            doc, section_name=KEYPHRASE_TITLE)

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
            doc, section_name=APELLANT_TITLE)

        # Factual Background section
        match_new_facts = FACTUAL_GROUND_HEADER_PATTERN.search(doc)
        if match_new_facts:
            background_end_position = match_new_facts.span()[0]
            dict_info["factual_background"] = self.extract_section_content(
                doc,
                section_name=FACTUAL_BACKGROUND_HEADER,
                section_end_pos=background_end_position,
                clean_text=False)
        else:
            dict_info["factual_background"] = INFO_NOT_FOUND_STRING

        # Previous Verdict
        dict_info["first_verdict"] = self.retrieve_verdict_result(
            dict_info["factual_background"])

        # Factual Ground section
        match_last_verdict = VERDICT_HEADER_PATTERN.search(
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
            dict_info["verdict_arguments"] = \
                doc[match_last_verdict.span()[0] + background_end_position:]

        # Final Verdict Result
        dict_info["last_verdict"] = self.retrieve_verdict_result(
            dict_info["verdict_arguments"])

        # Legal Costs last litigation
        dict_info["legal_costs"] = self.retrieve_litigation_costs(
            dict_info["verdict_arguments"])

        return dict_info

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
