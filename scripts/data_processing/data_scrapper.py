# Web Scraping from dynamic platform: CENDOJ

import os
import re

import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# num requests will always be 4 as it is the maximum number of pages
# in one search
NUM_REQUESTS = 19
ROOT_URL = "https://www.poderjudicial.es"
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

        # initialize driver's service and options
        self.edge_service = EdgeService(
            executable_path=EdgeChromiumDriverManager().install())

        self.option = webdriver.EdgeOptions()
        self.option.add_argument("start-maximized")

    def __call__(self, date, textual_query, num_searches,
                 output_path_general_links, output_path_pdf_links):

        links_set = set()
        for i in range(num_searches):

            if i == 0:
                state = False
            else:
                state = True

            date, elements = self.get_general_links_to_juris(
                root=ROOT_URL,
                name=textual_query,
                num_requests=NUM_REQUESTS,
                date=date,
                fecha_state=state)

            for element in elements:
                links_set.add(element)

        geral_links_array = np.array(links_set)
        np.savez(output_path_general_links, geral_links_array)

        pdf_links = set()
        for lk in links_set:
            pdf_lk = self.get_link_to_pdf_juris(lk)
            pdf_links.add(pdf_lk)

        pdf_links_array = np.array(pdf_links)
        np.savez(output_path_pdf_links, pdf_links_array)

        return links_set

    def init_driver(self):
        driver = webdriver.Edge(service=self.edge_service, options=self.option)
        return driver

    def get_general_link_href(self, link):
        """Get HREF from embedded HTML link information"""
        element = link.get_attribute('innerHTML')
        start_link = element.find("a href", 0)
        start_quote = element.find('"', start_link)
        end_quote = element.find('"', start_quote + 1)
        link = element[start_quote + 1:end_quote]
        return link

    def get_link_to_pdf_juris(self, general_link):

        driver = self.init_driver()
        wait = WebDriverWait(driver, 30)

        driver.get(general_link)

        # deactivate pop-up window
        wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.close"))).click()

        # get link to jurisprudence pdf
        pdf_box_element = driver.find_element(By.ID, "objtcontentpdf")
        html_element = pdf_box_element.get_attribute('innerHTML')
        start_link_str = 'a href="'
        start_link = html_element.find(start_link_str) + len(start_link_str)
        end_link = html_element.find('"', start_link)
        link = html_element[start_link:end_link]

        driver.quit()
        return link

    def get_general_links_to_juris(self,
                                   root,
                                   name,
                                   num_requests,
                                   date,
                                   fecha_state=False):
        """
        Create a driver and access to the searcher, make the query with
        all required conditions (date, location, organ, etc) run que query
        and extract the links from the results
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

        # Set query and search
        search = driver.find_element(By.ID, "frmBusquedajurisprudencia_TEXT")
        search.send_keys(name)
        search.send_keys(Keys.RETURN)

        last_date = None
        links_juris = list()
        for i in range(int(num_requests)):

            # wait while page is loading
            text = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "jurisprudenciaresults_searchresults")))

            # identify links
            link_elements = text.find_elements(By.CLASS_NAME, 'title')
            links_juris.extend(
                [self.get_general_link_href(link) for link in link_elements])

            # click on next page button
            main = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "gotopage")))

            # if last page select date of last sentence
            if i == int(num_requests) - 1:
                xpath_content = "//div[starts-with(@id, 'jurisprudenciaresults_content-')]"  # noqa: E501
                content = driver.find_elements(By.XPATH, xpath_content)
                juris_title = content[-1].find_element(By.CLASS_NAME,
                                                       "title").text

                date_parts = re.search(r'\d{2}\sde\s\w+\sde\s\d{4}',
                                       juris_title).group().split(' de ')

                month_num = month_to_num.get(date_parts[1])
                last_date = f'{date_parts[0]}/{month_num}/{date_parts[2]}'

            main.clear()
            main.send_keys("{}".format(i + 2))
            main.send_keys(Keys.RETURN)

        driver.quit()
        return last_date, links_juris
