# Web Scraping from dynamic platform: CENDOJ

import json
import os
import random
import re
from typing import List, Tuple

import numpy as np
import pandas as pd
from selenium.webdriver import Edge as EdgeDriver
from selenium.webdriver import EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from scripts.data_processing.data_storage import JurisdictionDataBaseManager

# num requests will always be 4 as it is the maximum number of pages
# in one search
NUM_REQUESTS = 20
NUM_PARALLEL_PROCS = 4
ROOT_URL = "https://www.poderjudicial.es"
ROTATING_USER_AGENTS_FILE = "data/user_agents.txt"
LAST_DATE_FILE_PATH = "data/last_date.json"
ARGS_PATH = "arguments.json"
VECTOR_DB_SECRETS = "database_secrets.json"

month_to_num = {
    "enero": '01',
    "febrero": '02',
    "marzo": '03',
    "abril": '04',
    "mayo": '05',
    "junio": '06',
    "julio": '07',
    "agosto": '08',
    "septiembre": '09',
    "octubre": '10',
    "noviembre": '11',
    "diciembre": '12'
}


class JurisdictionScrapper():
    def __init__(self):

        # load user agents
        with open(ROTATING_USER_AGENTS_FILE, 'r') as file:
            self.agents = file.readlines()

        # initialize driver's service and options
        self.edge_service = EdgeService(
            executable_path=EdgeChromiumDriverManager().install())

        # load scrapper arguments
        with open(ARGS_PATH) as f:
            args = json.load(f)

        self.sqlite_table_path = args["db"]["sqlite_links_table_path"]
        self.db_manager = JurisdictionDataBaseManager()

        # load db secrets
        with open(VECTOR_DB_SECRETS) as f:
            self.db_args = json.load(f)

        self.n_fails = 0
        self.n_success = 0

    def __call__(self, scrape_mode: str, date: str, textual_query: str,
                 num_searches: int,
                 output_path_general_links: str) -> set[str]:
        """
        Scrape general and PDF links to jurisprudences based on the
        given parameters.

        Parameters:
        scrape_mode (str): The scape mode: use "all_links" to scrape from the
        begging and "final_links" if general links are already saved.
        date (str): The date for filtering jurisprudences.
        textual_query (str): The query text to search for in jurisprudences.
        num_searches (int): The number of pagination requests to make.
        output_path_general_links (str): The file path to save the general
        links.

        Returns:
        set[str]: A set of unique general links to jurisprudences.
        """
        if scrape_mode == "all_links":
            date_year = date.split('/')[-1]
            date = ["01/01/" + date_year, date]

            # if last date file exists then use last date and last round to
            # resume scraping
            if os.path.exists(LAST_DATE_FILE_PATH):

                with open(LAST_DATE_FILE_PATH, 'r') as file:
                    resume_info = json.load(file)

                new_end_date, last_i = list(resume_info.values())
                date[1] = new_end_date
                last_i_incr = last_i + 1
                num_searches = num_searches - last_i_incr

                link_set = self.load_np_array(output_path_general_links)

            # otherwise initialize variables
            else:
                link_set = set()
                last_i_incr = 0

            for i in range(num_searches):

                new_end_date, elements = self.get_general_links_to_juris(
                    root=ROOT_URL,
                    juris_topic=textual_query,
                    num_requests=NUM_REQUESTS,
                    date=date)

                date[1] = new_end_date

                for element in elements:
                    link_set.add(element)

                # save last date and round
                dict_date_round = {
                    "date": new_end_date,
                    "round": i + last_i_incr
                }
                with open(LAST_DATE_FILE_PATH, 'w') as f:
                    json.dump(dict_date_round, f)

                # save batch of scraped links plus previous loaded if any
                general_links_array = np.array(link_set)
                np.save(output_path_general_links,
                        general_links_array,
                        allow_pickle=True)

        else:
            link_set = self.load_np_array(output_path_general_links)

        # for the second part, check if any links already in the database
        if os.path.exists(self.db_args['database_name']):
            # generate connection
            self.db_manager.generate_connection("sqlite")
            cur = self.db_manager.connection.cursor()
            # get tables
            res = cur.execute("SELECT name FROM sqlite_master")
            tables = list(sum(res.fetchall(), ()))

            # if table exists, get base_urls and remove them from link_set
            if self.sqlite_table_path in tables:
                base_urls = self.db_manager.get_query_data(
                    f"SELECT base_url FROM {self.sqlite_table_path}")
                base_urls = list(sum(base_urls, ()))

                link_set = link_set - set(base_urls)

        # extract remaining final pdf links
        for lk in link_set:
            self.link_extraction(lk)

    def load_np_array(self, path: str) -> List:
        return set(list(np.ravel(np.load(path, allow_pickle=True))[0]))

    def link_extraction(self, lk: str) -> None:
        """
        Extract links from a given URL and add them to the set.

        Args:
            lk (str): The URL from which to extract the link.
        """
        # Retrieve link
        pdf_base_lk = self.get_link_to_pdf_juris(lk)

        # If no link is found, return
        if not pdf_base_lk:
            return
        else:
            self.n_success += 1

        print(f"Success: {self.n_success} | Fails: {self.n_fails}")

        # Clean and generate final link
        pdf_final_lk = ROOT_URL + pdf_base_lk.replace('amp;', '')
        df_url = pd.DataFrame(list(zip([lk], [pdf_final_lk])),
                              columns=['base_url', 'final_url'])

        self.db_manager("sqlite", self.sqlite_table_path, df_url)

    def init_driver(self) -> EdgeDriver:
        """
        Initialize and return a WebDriver instance.

        Returns:
        WebDriver: A WebDriver instance for web scraping.
        """
        self.option = EdgeOptions()
        self.option.add_argument("start-maximized")
        self.option.add_argument(
            '--disable-blink-features=AutomationControlled')
        self.option.add_experimental_option("excludeSwitches",
                                            ["enable-automation"])
        self.option.add_experimental_option('useAutomationExtension', False)

        random_agent = random.choice(self.agents).removesuffix('\n')

        driver = EdgeDriver(service=self.edge_service, options=self.option)
        driver.execute_cdp_cmd('Network.setUserAgentOverride',
                               {"userAgent": random_agent})

        return driver

    def get_general_link_href(self, element: WebElement) -> str:
        """
        Extracts the href value from the given WebElement.

        Parameters:
        element (WebElement): The WebElement containing the link.

        Returns:
        str: The href value of the link.
        """
        # retrieve all text in the element
        html_element = element.get_attribute('innerHTML')
        # search for the start and end position of the href element
        start_link_str = 'a href="'
        start_link = html_element.find(start_link_str) + len(start_link_str)
        end_link = html_element.find('"', start_link)
        link = html_element[start_link:end_link]
        return link

    def get_link_to_pdf_juris(self, general_link: str) -> str:
        """
        Extracts the link to the PDF jurisprudence from the given general link.

        Parameters:
        general_link (str): The general link to the jurisprudence.

        Returns:
        str: The link to the PDF jurisprudence.
        """
        driver = self.init_driver()
        wait = WebDriverWait(driver, 30)

        driver.get(general_link)

        # Wait for the pop-up window to be clickable
        try:
            pop_up_close_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close")))
            pop_up_close_button.click()
        except Exception:
            # Handle the exception if the pop-up does not appear
            # or the button is not clickable
            print("Exception occurred while closing the pop-up")
            self.n_fails += 1

        try:
            # get link to jurisprudence pdf
            pdf_box_element = driver.find_element(By.ID, "objtcontentpdf")
            link = self.get_general_link_href(pdf_box_element)
        except Exception:
            print("Exception occurred while searching for objtcontentpdf")
            link = None
            self.n_fails += 1

        driver.quit()
        return link

    def get_date_and_format(self, driver: EdgeDriver) -> str:
        """
        Extracts the last jurisprudence date from the web page and formats it.

        Parameters:
        driver (WebDriver): The WebDriver instance.

        Returns:
        str: The formatted last jurisprudence date (DD/MM/YYYY).
        """
        # Identify last element's title
        xpath_content = "//div[starts-with(@id, 'jurisprudenciaresults_content-')]"  # noqa: E501
        content = driver.find_elements(By.XPATH, xpath_content)
        juris_title = content[-1].find_element(By.CLASS_NAME, "title").text

        # Extract date from element title in format: <DD de MONTH de YYYY>
        # and transform to desired format
        date_parts = re.search(r'\d{2}\sde\s\w+\sde\s\d{4}',
                               juris_title).group().split(' de ')

        month_num = month_to_num.get(date_parts[1])
        last_date = f'{date_parts[0]}/{month_num}/{date_parts[2]}'

        return last_date

    def get_general_links_to_juris(self,
                                   root: str,
                                   juris_topic: str,
                                   num_requests: int,
                                   date: str) \
            -> Tuple[str, list[str]]:
        """
        Retrieves links to jurisprudence pdf in web based on the given
        parameters.

        Parameters:
        root (str): The root URL of the jurisprudence searcher.
        juris_topic (str): The topic of jurisprudences to search for.
        num_requests (int): The number of pagination requests to make.
        date (str): The date for filtering jurisprudences.

        Returns:
        Tuple[str, List[str]]: A tuple containing the last jurisprudence date
                               and a list of links to jurisprudences.
        """
        driver = self.init_driver()

        wait = WebDriverWait(driver, 30)
        jurisprudence_searcher_url = os.path.join(root, "search",
                                                  "indexAN.jsp")
        driver.get(jurisprudence_searcher_url)

        # deactivate pop-up window
        wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.close"))).click()

        # Civil Jurisdiction
        wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "(//button[@class='multiselect dropdown-toggle btn btn-default tooltips'])[1]"  # noqa: E501
            ))).click()
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//label[.//input[@value='CIVIL']]"))).click()
        wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "(//button[@class='multiselect dropdown-toggle btn btn-default tooltips'])[1]"  # noqa: E501
            ))).click()

        # Organ type: Audiencia Provincial
        wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "(//button[@class='multiselect dropdown-toggle btn btn-default tooltips'])[2]"  # noqa: E501
            ))).click()
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//label[.//input[@value='37']]"))).click()
        wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "(//button[@class='multiselect dropdown-toggle btn btn-default tooltips'])[2]"  # noqa: E501
            ))).click()

        # Location: Cataluña
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "(//button[@id='COMUNIDADmultiselec'])"))).click()
        # Click on plus Cataluña
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//b[contains(text(),' CATALUÑA')]"))).click()
        # Click on plus Barcelona
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//b[contains(text(),' BARCELONA')]"))).click()
        # Click on Barcelona Ciutat
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//label[.//input[@id='chkSEDE_BARCELONA']]"))).click()
        # Drop botton
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "(//button[@id='COMUNIDADmultiselec'])"))).click()

        # Set date
        fecha = driver.find_element(
            By.ID, "frmBusquedajurisprudencia_FECHARESOLUCIONDESDE")
        fecha.send_keys(date[0])
        fecha = driver.find_element(
            By.ID, "frmBusquedajurisprudencia_FECHARESOLUCIONHASTA")
        fecha.send_keys(date[1])

        # Set topic and search
        search = driver.find_element(By.ID, "frmBusquedajurisprudencia_TEXT")
        search.send_keys(juris_topic)
        search.send_keys(Keys.RETURN)

        last_date = None
        links_juris = list()
        for i in range(int(num_requests)):

            # wait while page is loading
            text = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "jurisprudenciaresults_searchresults")))

            # identify and retrieve links
            link_elements = text.find_elements(By.CLASS_NAME, 'title')
            links_juris.extend(
                [self.get_general_link_href(link) for link in link_elements])

            # click on next page button
            main = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "gotopage")))

            # if last page select date of last sentence
            # get last jurisprudence date to repeat the search
            # from that date
            if i == int(num_requests) - 1:
                last_date = self.get_date_and_format(driver)

            main.clear()
            main.send_keys("{}".format(i + 2))
            main.send_keys(Keys.RETURN)

        driver.quit()
        return last_date, links_juris
