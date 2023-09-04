# Web Scraping from dynamic platform: CENDOJ

import os
import random
import re
from typing import Tuple

import numpy as np
from selenium.webdriver import Edge as EdgeDriver
from selenium.webdriver import EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# num requests will always be 4 as it is the maximum number of pages
# in one search
NUM_REQUESTS = 20
ROOT_URL = "https://www.poderjudicial.es"
ROTATING_IP_ADRESSES_FILE = "data/http_proxies.txt"

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

        # load rotating ips
        with open(ROTATING_IP_ADRESSES_FILE, 'r') as file:
            self.proxies = file.readlines()

        # initialize driver's service and options
        self.edge_service = EdgeService(
            executable_path=EdgeChromiumDriverManager().install())

    def __call__(self, date: str, textual_query: str, num_searches: int,
                 output_path_general_links: str,
                 output_path_pdf_links: str) -> set[str]:
        """
        Scrape general and PDF links to jurisprudences based on the
        given parameters.

        Parameters:
        date (str): The date for filtering jurisprudences.
        textual_query (str): The query text to search for in jurisprudences.
        num_searches (int): The number of pagination requests to make.
        output_path_general_links (str): The file path to save the general
        links.
        output_path_pdf_links (str): The file path to save the PDF links.

        Returns:
        set[str]: A set of unique general links to jurisprudences.
        """

        links_set = set()
        for i in range(num_searches):

            if i == 0:
                state = False
            else:
                state = True

            date, elements = self.get_general_links_to_juris(
                root=ROOT_URL,
                juris_topic=textual_query,
                num_requests=NUM_REQUESTS,
                date=date,
                fecha_state=state)

            for element in elements:
                links_set.add(element)

        geral_links_array = np.array(links_set)
        np.save(output_path_general_links,
                geral_links_array,
                allow_pickle=True)

        pdf_links = set()
        for lk in links_set:
            pdf_base_lk = self.get_link_to_pdf_juris(lk)
            pdf_final_lk = ROOT_URL + pdf_base_lk.replace('amp;', '')
            pdf_links.add(pdf_final_lk)

        pdf_links_array = np.array(pdf_links)
        np.save(output_path_pdf_links, pdf_links_array, allow_pickle=True)

    def init_driver(self) -> EdgeDriver:
        """
        Initialize and return a WebDriver instance.

        Returns:
        WebDriver: A WebDriver instance for web scraping.
        """
        self.option = EdgeOptions()
        self.option.add_argument("start-maximized")

        # Get a random proxy server from the list.
        proxy_ip = random.choice(self.proxies).removesuffix('\n')
        self.option.add_argument("--proxy-server={}".format(proxy_ip))

        driver = EdgeDriver(service=self.edge_service, options=self.option)
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

        # deactivate pop-up window
        wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.close"))).click()

        # get link to jurisprudence pdf
        pdf_box_element = driver.find_element(By.ID, "objtcontentpdf")
        link = self.get_general_link_href(pdf_box_element)

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
                                   date: str,
                                   fecha_state: bool = False) \
            -> Tuple[str, list[str]]:
        """
        Retrieves links to jurisprudence pdf in web based on the given
        parameters.

        Parameters:
        root (str): The root URL of the jurisprudence searcher.
        juris_topic (str): The topic of jurisprudences to search for.
        num_requests (int): The number of pagination requests to make.
        date (str): The date for filtering jurisprudences.
        fecha_state (bool, optional): Whether to set the date for filtering.
                                      Defaults to False.

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
        if fecha_state:
            fecha = driver.find_element(
                By.ID, "frmBusquedajurisprudencia_FECHARESOLUCIONHASTA")
            fecha.send_keys(date)

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
