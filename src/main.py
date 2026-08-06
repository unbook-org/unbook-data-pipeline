from selenium import webdriver
from selenium.webdriver.common.by import By
import os
from dotenv import load_dotenv, dotenv_values
import time
import datetime


load_dotenv() 

class SeleniumScrapper():
    def __init__(self):
        options = webdriver.FirefoxOptions()
        self.driver = webdriver.Firefox(options=options)
        time.sleep(0.5)
        self.login()

    def login(self):
        self.driver.get("https://facebook.com")
        email_textbox = self.driver.find_element(by=By.XPATH, value='//*[@id="_R_1h6kqsqppb6amH1_"]')
        email_textbox.send_keys(os.getenv("FACEBOOK_USERNAME"))
        password_textbox = self.driver.find_element(by=By.XPATH, value='//*[@id="_R_1hmkqsqppb6amH1_"]')
        password_textbox.send_keys(os.getenv("FACEBOOK_PASSWORD"))
        login_button = self.driver.find_element(by=By.XPATH, value='/html/body/div[1]/div/div/div/div/div/div/div[1]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div/div/div[2]/form/div/div[1]/div/div[3]/div/div/div')
        login_button.click()
        
    def scroll(self, giradas):
        for e in range(giradas):
            self.driver.execute_script("window.scrollBy(0, 600);")  # scroll down 600px
            time.sleep(2)  # wait for content to load

    def save_page(self):
        source = self.driver.page_source
        nome = "pagina_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".html"
        with open("pages/"+nome, "w") as fp:
            fp.write(source)
        








