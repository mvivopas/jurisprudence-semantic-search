# Web Scraping from dynamic platform: CENDOJ

from urllib.request import urlopen
import os
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

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

            date, elements = get_links(root=ROOT_URL,
                                       name=textual_query,
                                       num_requests=4,
                                       date=date,
                                       fecha_state=state)

            for element in elements:
                links_set.add(element)

        data = np.array(links_set)
        np.savez(output_path, data)


def get_href(element):
    start_link = element.find("a href", 0)
    start_quote = element.find('"', start_link)
    end_quote = element.find('"', start_quote + 1)
    link = element[start_quote + 1:end_quote]
    return link


def get_src(element):
    start = element.find("objtcontentpdf", 0)
    start_link = element.find("a href", start)
    start_quote = element.find('"', start_link)
    end_quote = element.find('"', start_quote + 1)
    link = element[start_quote + 1:end_quote]
    return link


def get_links(root, name, num_requests, date, fecha_state=False):

    driver = webdriver.Chrome(ChromeDriverManager().install())
    wait = WebDriverWait(driver, 30)

    jurisprudence_searcher_url = os.path.join(root, "search", "indexAN.jsp")
    driver.get(jurisprudence_searcher_url)

    wait.until(EC.element_to_be_clickable(
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
            (By.XPATH, "//label[.//input[@id='chkSEDE_BARCELONA']]"))).click()
    # Drop botton
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//button[@id='COMUNIDADmultiselec'])"))).click()

    # Expand number of results per page
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "(//button[@data-id='frmBusquedajurisprudencia_recordsPerPage'])"
             ))).click()
    # Click on 50
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//span[contains(text(),50)])"))).click()

    # Set date
    if fecha_state:
        fecha = driver.find_element_by_id(
            "frmBusquedajurisprudencia_FECHARESOLUCIONHASTA")
        fecha.send_keys(date)

    # Set query and search
    search = driver.find_element_by_id("frmBusquedajurisprudencia_TEXT")
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
        links = text.find_elements_by_class_name('title')

        for link in links:
            n = link.get_attribute('innerHTML')
            m = get_src(urlopen(get_href(n)).read().decode("latin-1"))
            link_list.append(root + m)

        # click on next page button
        main = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "gotopage")))

        # if last page select date of last sentence
        if i == int(num_requests) - 1:
            last_date = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "(//li[contains(text(),'Fecha')])[50]"
                     ))).get_attribute('innerHTML')
            last_date = last_date[10:-5]

        main.clear()
        main.send_keys("{}".format(i + 2))
        main.send_keys(Keys.RETURN)

    driver.quit()
    return last_date, link_list

