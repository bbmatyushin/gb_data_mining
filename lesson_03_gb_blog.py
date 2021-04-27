import typing
import requests
import bs4
from urllib.parse import urljoin
from database.db import Database
import datetime as dt


class GbBlogParse:
    def __init__(self, start_url, database: Database):
        self.db = database
        self.start_url = start_url
        self.done_urls = set()
        self.tasks = [
            self.get_task(self.start_url, self.parse_feed),
        ]
        self.done_urls.add(self.start_url)

    def get_task(self, url, callback):
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)

        return task

    def _get_response(self, url):
        response = requests.get(url)
        return response

    def _get_soup(self, url):
        soup = bs4.BeautifulSoup(self._get_response(url).text, "lxml")
        return soup

    def get_date(self, date_str):
        # print(int(date_str[5:7]))
        date_dt = dt.datetime(
            year=int(date_str[:4]),
            month=int(date_str[5:7]),
            day=int(date_str[8:10]),
        )
        return date_dt

    def parse_post(self, url, soup):
        author_tag = soup.find("div", attrs={"itemprop": "author"})
        data = {
            "post_data": {
                "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
                "url": url,
                "id": soup.find("comments").attrs.get("commentable-id"),
                "img_url": soup.find("img").attrs.get("src"),
                "date": self.get_date(soup.find("time").attrs.get("datetime")),
            },
            "author_data": {
                "url": urljoin(url, author_tag.parent.attrs.get("href")),
                "name": author_tag.text,
            },
            "tags_data": [
                {"name": tag_a.text, "url": urljoin(url, tag_a.attrs.get("href"))}
                for tag_a in soup.find_all("a", attrs={"class": "small"})
            ],
            "comments_data": self._get_comments(soup.find("comments").attrs.get("commentable-id")),
        }
        return data

    def _get_comments(self, post_id):
        api_path = f"/api/v2/comments?commentable_type=Post&commentable_id={post_id}&order=desc"
        response = self._get_response(urljoin(self.start_url, api_path))
        data = response.json()
        return data

    def parse_feed(self, url, soup):
        ul = soup.find("ul", attrs={"class": "gb__pagination"})
        pag_urls = set(
            urljoin(url, href.attrs.get("href"))
            for href in ul.find_all("a")
            if href.attrs.get("href")
        )
        for pag_url in pag_urls:
            if pag_url not in self.done_urls:
                self.tasks.append(self.get_task(pag_url, self.parse_feed))

        post_items = soup.find("div", attrs={"class": "post-items-wrapper"})
        posts_urls = set(
            urljoin(url, href.attrs.get("href"))
            for href in post_items.find_all("a", attrs={"class": "post-item__title"})
            if href.attrs.get("href")
        )

        for post_url in posts_urls:
            if post_url not in self.done_urls:
                self.tasks.append(self.get_task(post_url, self.parse_post))

    def run(self):
        for task in self.tasks:
            task_result = task()
            if task_result:
                self.db.create_post(task_result)

    def save(self, data):
        print(2)
        self.db.create_post(data)


if __name__ == "__main__":
    database = Database("sqlite:///gb_blog.db")
    parser = GbBlogParse("https://geekbrains.ru/posts", database)
    parser.run()