from pathlib import Path
import requests
import json
import time


class Parse5ka:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0"}

    def __init__(self, start_url: str, save_path: Path):
        self.start_url = start_url
        self.save_path = save_path

    def _get_response(self, url):
        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response
            time.sleep(1)

    def run(self):
        print(f'parsing products from {self.start_url}')
        for product in self._parse(self.start_url):
            product_path = self.save_path.joinpath(f"{product['id']}.json")
            self._save(product, product_path)

    def _parse(self, url: str):
        while url:
            response = self._get_response(url)
            data: dict = response.json()
            url = data["next"]
            for product in data["results"]:
                yield product

    def _save(self, data: dict, file_path: Path):
        file_path.write_text(json.dumps(data, ensure_ascii=False))


class CategoriesParser(Parse5ka):
    def __init__(self, categories_url, *args, **kwargs):
        self.categories_url = categories_url
        super().__init__(*args, **kwargs)

    def run(self):
        print(f'parsing categories from {self.categories_url}')
        response = self._get_response(self.categories_url)
        data: dict = response.json()
        for category in data:
            category["products"] = []
            params = '?categories=' + str(category['parent_group_code'])
            url = str(self.start_url) + str(params)
            products = list(self._parse(url))
            category["products"].extend(products)
            cat_path = self.save_path.joinpath(f"{category['parent_group_code']}.json")
            self._save(category, cat_path)


def get_save_path(dir_name):
    save_path = Path(__file__).parent.joinpath(dir_name)
    if not save_path.exists():
        save_path.mkdir()
    return save_path


if __name__ == "__main__":
    print('START')
    url = "https://5ka.ru/api/v2/special_offers/"
    cat_url = "https://5ka.ru/api/v2/categories/"

    save_path_products = get_save_path("products")
    save_path_categories = get_save_path("categories")

    parser_products = Parse5ka(url, save_path_products)
    parser_categories = CategoriesParser(cat_url, url, save_path_categories)

    # parser_products.run()
    parser_categories.run()
    print('FINISH')
