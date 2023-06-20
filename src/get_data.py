# Web Scraping from dynamic platform: CENDOJ

from urllib.request import urlopen

import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class JurisdictionScrapper():
    def __init__(self):
        # self.date = date
        # self.num_links = num_links
        # self.root
        # li podria pasar an existing ref
        pass

    def __call__(self):

        links_list = list()
        date = "10/12/2020"

        for i in range(3):

            if i == 0:
                state = False
            else:
                state = True

            date, elements = get_links(root="https://www.poderjudicial.es",
                                       name="clausulas abusivas",
                                       num_requests=4,
                                       date=date,
                                       fecha_state=state)

            for element in elements:
                if element not in links_list:
                    links_list.append(element)

        data = np.array(links_list)
        np.savez("data_links", data)


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

    driver.get("https://www.poderjudicial.es/search/indexAN.jsp")
    wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.close"))).click()

    # Jurisdicción Civil
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

    # Tipo de órgano Audiencia Provincial
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

    # Localización Cataluña
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
    # Click on Barcelona ciutat
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//label[.//input[@id='chkSEDE_BARCELONA']]"))).click()
    # Drop botton
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//button[@id='COMUNIDADmultiselec'])"))).click()

    # 50 busquedas x página
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "(//button[@data-id='frmBusquedajurisprudencia_recordsPerPage'])"
             ))).click()
    # Click on 50
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//span[contains(text(),50)])"))).click()

    # Fecha
    if fecha_state:
        fecha = driver.find_element_by_id(
            "frmBusquedajurisprudencia_FECHARESOLUCIONHASTA")
        fecha.send_keys(date)

    # Buscamos por la temática de interes
    search = driver.find_element_by_id("frmBusquedajurisprudencia_TEXT")
    search.send_keys(name)
    search.send_keys(Keys.RETURN)
    elements = list()

    for i in range(int(num_requests)):

        text = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "jurisprudenciaresults_searchresults")))

        links = text.find_elements_by_class_name('title')

        for link in links:
            n = link.get_attribute('innerHTML')
            m = get_src(urlopen(get_href(n)).read().decode("latin-1"))
            elements.append(root + m)

        main = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "gotopage")))

        # si esta a sa última pag que agafi fecha 50
        if i == 3:
            last_date = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "(//li[contains(text(),'Fecha')])[50]"
                     ))).get_attribute('innerHTML')

        main.clear()
        main.send_keys("{}".format(i + 2))
        main.send_keys(Keys.RETURN)

    driver.quit()
    # dict[name] = elements

    if i >= 3:
        return [last_date[10:-5], elements]

    else:
        return elements
