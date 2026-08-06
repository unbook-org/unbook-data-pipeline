from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv


class Bs4Parser():
    def __init__(self):
        self.posts = []

    def read_page(self, path_doc):
        with open(path_doc, "r") as file:
            return self.get_posts(file.read()) 
        

    def get_posts(self, doc):
        soup = BeautifulSoup(doc, 'html.parser')

        posts_data = []

        posts = soup.find_all("div", {"class": "x1n2onr6 x1ja2u2z"})


        for post in posts:
            try:
                message_elements = post.find_all("div", {"data-ad-preview": "message"})
                post_text = " ".join([msg.get_text(strip=True) for msg in message_elements])
                
                likes_element = post.select_one("span.xt0b8zv.x1jx94hy.xrbpyxo.xl423tq > span > span")
                likes = likes_element.get_text(strip=True) if likes_element else None
                
                comments_element = post.select("div > div > span > div > div > div > span > span.html-span ")
                comments = comments_element[0].text if comments_element else None
                
                shares_element = post.select("div > div > span > div > div > div > span > span.html-span ")
                shares = shares_element[1].text if shares_element else None

                timeelement = post.select_one("div.xu06os2.x1ok221b > span > div > span > span > a > span")
                post_time = timeelement.get_text(strip=True) if timeelement else None

                if any([post_text, likes, comments, shares, post_time]):
                    posts_data.append({
                        "post_text": post_text,
                        "likes": likes,
                        "comments": comments,
                        "shares": shares,
                        "post_time": post_time
                    })
            except Exception as e:
                print("Error extracting post data:", e)

        return posts_data
        

if __name__ =="__main__":
    load_dotenv() 
    obj = Bs4Parser()
    root = os.getenv("ROOT")
    path_pages = os.path.join(root, "pages")
    posts = []

    for nome_arquivo in os.listdir(path_pages):
        lista = obj.read_page(os.path.join(path_pages, nome_arquivo))
        posts = posts + lista.copy()



