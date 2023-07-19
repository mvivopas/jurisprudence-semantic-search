# Web Scraping from dynamic platform: CENDOJ

import os
from urllib.request import urlopen

import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

option = webdriver.ChromeOptions()
option.add_argument("start-maximized")

# num requests will always be 4 as it is the maximum number of pages
# in one search
NUM_REQUESTS = 19
ROOT_URL = "https://www.poderjudicial.es"


class JurisdictionScrapper():
    def __init__(self):
        pass

    def __call__(self, date, textual_query, num_searches, output_path):

        links_set = set()
        for i in range(num_searches):

            if i == 0:
                state = False
            else:
                state = True

            date, elements = self.get_links(root=ROOT_URL,
                                            name=textual_query,
                                            num_requests=NUM_REQUESTS,
                                            date=date,
                                            fecha_state=state)

            for element in elements:
                links_set.add(element)

        data = np.array(links_set)
        np.savez(output_path, data)
        return links_set

    def get_href(self, element):
        """Get HREF from embedded HTML link information"""
        start_link = element.find("a href", 0)
        start_quote = element.find('"', start_link)
        end_quote = element.find('"', start_quote + 1)
        link = element[start_quote + 1:end_quote]
        return link

    def get_src(self, element):
        """Get SRC from HREF direction"""
        start = element.find("objtcontentpdf", 0)
        start_link = element.find("a href", start)
        start_quote = element.find('"', start_link)
        end_quote = element.find('"', start_quote + 1)
        link = element[start_quote + 1:end_quote]
        return link

    def get_links(self, root, name, num_requests, date, fecha_state=False):
        """
        Create a driver and access to the searcher, make the query with
        all required conditions (date, location, organ, etc) run que query
        and extract the links from the results
        """
        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()),
                                  options=option)
        wait = WebDriverWait(driver, 30)

        jurisprudence_searcher_url = os.path.join(root, "search",
                                                  "indexAN.jsp")
        driver.get(jurisprudence_searcher_url)

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
        link_list = list()
        for i in range(int(num_requests)):

            # wait while page is loading
            text = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "jurisprudenciaresults_searchresults")))

            # identify links
            links = text.find_elements(By.CLASS_NAME, 'title')

            for link in links:
                link_attrs = link.get_attribute('innerHTML')
                link_href = self.get_href(link_attrs)
                final_url = self.get_src(
                    urlopen(link_href).read().decode("latin-1"))
                link_list.append(root + final_url)

            # click on next page button
            main = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "gotopage")))

            # if last page select date of last sentence
            if i == int(num_requests) - 1:
                last_date = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "(//li[contains(text(),'Fecha')])[10]"
                         ))).get_attribute('innerHTML')
                last_date = last_date[10:-5]

            main.clear()
            main.send_keys("{}".format(i + 2))
            main.send_keys(Keys.RETURN)

        driver.quit()
        return last_date, link_list
