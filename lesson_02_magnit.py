import datetime as dt
from pathlib import Path
from urllib.parse import urljoin
import requests
import bs4
import pymongo


MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}


class MagnitParse:
    def __init__(self, start_url, db_client):
        self.start_url = start_url
        self.db = db_client["gb_data_mining_15_02_2021"]
        self.collection = self.db["magnit_products"]

    def _get_response(self, url):
        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response
            time.sleep(1)
        
    def _get_soup(self, url):
        response = self._get_response(url).text
        return bs4.BeautifulSoup(response, "lxml")

    def run(self):
        soup = self._get_soup(self.start_url)
        catalog = soup.find("div", attrs={"class": "сatalogue__main"})
        for prod_a in catalog.find_all("a", recursive=False):
            product_data = self._parse(prod_a)
            self._save(product_data)

    def get_template(self):
        return {
            "product_name": lambda a: a.find("div", attrs={"class": "card-sale__title"}).text,
            "url": lambda a: urljoin(self.start_url, a.attrs.get("href", "")),
            "promo_name": lambda a: a.find("div", attrs={"class": "card-sale__name"}).text,
            "old_price": lambda a: float(
                ".".join(
                    itm for itm in a.find("div", attrs={"class": "label__price_old"}).text.split()
                )
            ),
            "new_price": lambda a: float(
                ".".join(
                    itm for itm in a.find("div", attrs={"class": "label__price_new"}).text.split()
                )
            ),
            "image_url": lambda a: urljoin(self.start_url, a.find("img").attrs.get("data-src")),
            "date_from": lambda a: self.__get_date(
                a.find("div", attrs={"class": "card-sale__date"}).text
            )[0],
            "date_to": lambda a: self.__get_date(
                a.find("div", attrs={"class": "card-sale__date"}).text
            )[1],
        }

    def __get_date(self, date_string) -> list:
        date_list = date_string.replace("с ", "", 1).replace("\n", "").split("до")
        result = []
        for date in date_list:
            temp_date = date.split()
            
            # Не понял по поводу проблемы с обработкой даты при смене года...
            result_date = dt.datetime(
                year = dt.datetime.now().year, 
                month = MONTHS[temp_date[1][:3]],
                day = int(temp_date[0]),
                )
            
            result.append(result_date)
        # FIXME: Сделать корректную обработку смены года
        return result

    def _parse(self, product_a) -> dict:
        data = {}
        for key, func in self.get_template().items():
            try:
                data[key] = func(product_a)
            except (AttributeError, ValueError):
                print('Ошибка')
                pass
        return data

    def _save(self, data: dict):
        self.collection.insert_one(data)


def get_save_path(dir_name):
    dir_path = Path(__file__).parent.joinpath(dir_name)
    if not dir_path.exists():
        dir_path.mkdir()
    return dir_path


if __name__ == "__main__":
    url = "https://magnit.ru/promo/"
    save_path = get_save_path("magnit_product")
    db_client = pymongo.MongoClient("mongodb://localhost:27017")
    parser = MagnitParse(url, db_client)
    parser.run()