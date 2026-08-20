from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver import ActionChains
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
        
    def scroll(self, giradas=1): 
        for e in range(giradas):
            self.driver.execute_script("window.scrollBy(0, 600);")  # scroll down 600px
            time.sleep(2)  # wait for content to load

    def scrollTo(self, element, extra=1000):
        ActionChains(self.driver).scroll_to_element(element).perform()
        self.driver.execute_script(f"window.scrollBy(0, {extra});")

    def get_comentario(self, post, wait=2):
        try:
            
            # Tenta expandir comentários clicando em "Ver mais respostas" / "Ver X respostas"
            botao_comentar = post.find_element(
                By.CSS_SELECTOR,
                '[data-ad-rendering-role="comment_button"]'
            ).find_element(By.XPATH, "./ancestor::div[@role='button']")
            botao_comentar.click()
            time.sleep(wait)
            
        
            feed = obj.driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
            texto = feed.find_element(By.CSS_SELECTOR, "div[data-ad-rendering-role='story_message']").text

            retorno = {
                "texto": texto,
                "comentarios": feed.get_attribute("innerHTML")
            }

            botao_fechar = self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='Fechar']")
            botao_fechar.click()
            time.sleep(wait)
            return retorno

            
            
        except Exception as e: 
            print("Erro num post:", e)
            time.sleep(wait)

    def save_page(self):
        source = self.driver.page_source
        nome = "pagina_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".html"
        with open("pages/"+nome, "w") as fp:
            fp.write(source)

    def save_feed_comentario(self, comentarios):
        
        nome = "pagina_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".html"

        with open(os.getenv("COMENTARIOS_CSV") , "a") as fp:
            linha = "'"+comentarios["texto"]+"';'"+nome+"';\n"
            fp.write(linha)
        with open(os.path.join(os.getenv('ROOT'),"pages", nome), "w") as fp:
            fp.write(comentarios["comentarios"])


if __name__ == "__main__":
    obj = SeleniumScrapper()
    input("faça o captcha e entre na página do grupo do facebook.\nDE ENTER AO FAZER ISSO")
    print("ctrl+c para parar")

    while True:
        posts = obj.driver.find_elements(By.CSS_SELECTOR, "div[aria-posinset]")
        for p in posts:
            comentario = obj.get_comentario(p)
            if comentario is not None:
                obj.save_feed_comentario(comentario)
            else:
                print(f'ERRO: NO POST {p.find_element(By.CSS_SELECTOR, "div[data-ad-comet-preview='message']").text}')
            print("-="*25)
            # para = input()
            # if para != '':
            #     break
        obj.scrollTo(posts[-1])
        posts = []
        time.sleep(1)
    # resultados = []

    # for post in posts:
    #     comentarios = obj.get_comentario(post)
    #     resultados.append(comentarios.copy())
    #     input()
    # while True:
    # obj.save_page()
    # obj.scroll()
    # time.sleep(0.5)







