from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse.spiders.autoyoula import AutoyoulaSpider

if __name__ == "__main__":
    print('lesson # 4. Scrapy')
    crawler_settings = Settings()  # содаЄтс€ объект настроек на базе scrapy-settings
    crawler_settings.setmodule("gb_parse.settings") # примен€ютс€ настройки, указанные в пакете gb_parse модуле(файле) settings
    crawler_proc = CrawlerProcess(settings=crawler_settings) # создаЄтс€ объект (процесс) паука с ранее определЄнными настройками
    crawler_proc.crawl(AutoyoulaSpider) # указываетс€ какой паук (код) будет использоватьс€ в процессе
    crawler_proc.start() # запускаетс€ процесс
