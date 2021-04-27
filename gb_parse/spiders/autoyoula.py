import pymongo
import scrapy
import re

"""Я вообще не понял откуда ничнается программа! Где старт? Что запускает скрипт?
В __init__ ничего такого нет. Отдельного модуля run нет.
Он запускается строкой super().__init__(*args, **kwargs), которая так делает внутри scrapy.Spider??!!
Он сам получает и сохраняет (а потом использует) response и callback?"""

class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"] # ограничивается доменная зона для процесса
    start_urls = ["https://auto.youla.ru/"]

    _css_selectors = {
        "brands": ".TransportMainFilters_brandsList__2tIkv "
        ".ColumnItemList_container__5gTrc "
        "a.blackLink",
        "pagination": "a.Paginator_button__u1e7D",
        "car": ".SerpSnippet_titleWrapper__38bZM a.SerpSnippet_name__3F7Yu",
    } # задаются селекторы css стиля для определения брендов, пагенации, машин. Где их найти понял, как определить
    # что именно эти и из этого места нужно взять - не понял.
    data_query = { # формируем шаблон данных, которые генерируеются lambda функциями из ответа (resp)
        "title": lambda resp: resp.css("div.AdvertCard_advertTitle__1S1Ak::text").get(), # из ответа по css находим
        # нужный элемент, и получаем текст
        "price": lambda resp: float(
            resp.css("div.AdvertCard_price__3dDCr::text").get().replace("\u2009", "")
        ), # из ответат как и раньше берём текст, но удаляем пробел
        "photos": lambda resp: [
            item.attrib.get("src") for item in resp.css("figure.PhotoGallery_photo__36e_r img")
        ], # генератор элементов ответат с указанным css, из которых вытаскивам аттрибут src
        "characteristics": lambda resp: [
            {
                "name": item.css(".AdvertSpecs_label__2JHnS::text").extract_first(),
                "value": item.css(".AdvertSpecs_data__xK2Qx::text").extract_first()
                or item.css(".AdvertSpecs_data__xK2Qx a::text").extract_first(),
            }
            for item in resp.css("div.AdvertCard_specs__2FEHc .AdvertSpecs_row__ljPcX")
        ], # генератор эл из ответа по css, из который тащим 2 значения (берём первые) в виде словаря
        "descriptions": lambda resp: resp.css(
            ".AdvertCard_descriptionInner__KnuRi::text"
        ).extract_first(), # просто по css тащим нужный текст
        "author": lambda resp: AutoyoulaSpider.get_author_id(resp), # в качестве данных будет результат функции
        # get_author_id от полученного ответа
    }

    @staticmethod # так и не выучил пока декораторы... не понимаю различий между ними.
    def get_author_id(resp):
        marker = "window.transitState = decodeURIComponent" # определили маячок того что в этом коде есть ИД автора, но
        # как мы этот маяк увидели в код вообще не понял...
        for script in resp.css("script"): # если в коде точно есть скрипт с нужными данными, то работает дальше
            try:
                if marker in script.css("::text").extract_first(): # если маяк есть в скрипте (почему-то первый)
                    re_pattern = re.compile(r"youlaId%22%2C%22([a-zA-Z|\d]+)%22%2C%22avatar") # жуткое регулярное
                    # выражение формата ИД автора в коде...
                    result = re.findall(re_pattern, script.css("::text").extract_first()) # не понял почему ищем все,
                    # а берём первое...
                    return (
                        resp.urljoin(f"/user/{result[0]}").replace("auto.", "", 1)
                        if result
                        else None
                    ) # возвращаем преобразованную ссылку на автора (с его ИД) если есть, или ничего не вернём
            except TypeError:
                pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_client = pymongo.MongoClient()

    def _get_follow(self, response, select_str, callback, **kwargs):
        for a in response.css(select_str):
            link = a.attrib.get("href") # вытаскиваем ссылку
            yield response.follow(link, callback=callback, cb_kwargs=kwargs) # возвращаем генератор последующих ссылок.
            # Про колбэки вообще не понял, что это и как работает. Про cb_kwargs понял, но зачем нам тут moto нет..

    def parse(self, response, *args, **kwargs):
        yield from self._get_follow(
            response, self._css_selectors["brands"], self.brand_parse, hello="moto"
        ) # не понял. Парсим бренды, где колбэк это генератор от brand_parse (в котором пагинация и машины),
        # почему-то с moto...

    def brand_parse(self, response, **kwargs):
        yield from self._get_follow(
            response, self._css_selectors["pagination"], self.brand_parse,
        ) # не понял. Это генератор всех ссылок пагинации по брендам, так?..
        yield from self._get_follow(
            response, self._css_selectors["car"], self.car_parse
        ) # не понял совсем. Два раза возвращаем ответ (yield/генератор) от этой функции?! сначала пагинацию, а потом
        # данные по самой машине?!

    def car_parse(self, response):
        data = {}
        for key, selector in self.data_query.items(): # форминуем данные по шаблону data_query
            try:
                data[key] = selector(response)
            except (ValueError, AttributeError):
                continue
        self.db_client["gb_parse_15_02_2021"][self.name].insert_one(data) # записываем в базу