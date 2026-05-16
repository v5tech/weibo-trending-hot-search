import os
import re
from datetime import datetime, timedelta

import requests
from lxml import etree
from requests.exceptions import RequestException

import daily_hot_news
from daily_hot_news import HotEntry

baseurl = 'https://s.weibo.com'


def _archive_path(date: str, ext: str) -> str:
    ym = date[:7].replace('-', '')
    return f"./archives/{ym}/{date}.{ext}"


def save(filename, content):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)


def fetch_weibo(url):
    try:
        headers = {
            "Cookie": "SUB=_2AkMWIuNSf8NxqwJRmP8dy2rhaoV2ygrEieKgfhKJJRMxHRl-yT9jqk86tRB6PaLNvQZR6zYUcYVT1zSjoSreQHidcUq7",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36 Edg/90.0.818.41"
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            print("抓取完毕...")
            return resp.content.decode("utf-8")
        return None
    except RequestException:
        return None


def parse_weibo(content) -> dict[str, HotEntry]:
    html = etree.HTML(content)
    xpath = '//*[@id="pl_top_realtimehot"]/table/tbody/tr[position()>1]/td[@class="td-02"]/a[not(contains(@href, "javascript:void(0);"))]'
    titles = html.xpath(f'{xpath}/text()')
    hrefs = html.xpath(f'{xpath}/@href')
    hots = html.xpath(f'{xpath}/../span/text()')
    titles = [title.strip() for title in titles]
    hrefs = [f"{baseurl}{href.strip()}" for href in hrefs]
    hots = [hot.strip() for hot in hots]
    hot_news = {}
    for i, title in enumerate(titles):
        hot_news[title] = {'url': f"{hrefs[i]}", 'hot': int(re.findall(r'\d+', hots[i])[0])}
    print("解析完毕...")
    return hot_news


def save_csv(date: str, sorted_news: dict[str, HotEntry]) -> None:
    row = f'{date},' + ",".join([k for k, v in sorted_news.items()])
    save(_archive_path(date, 'csv'), row)


def _render_md_list(news: dict[str, HotEntry]) -> str:
    line = '1. [{title}]({url}) {hot}'
    return '\n'.join(line.format(title=k, hot=v['hot'], url=v['url']) for k, v in news.items())


def update_readme(news: dict[str, HotEntry]) -> None:
    block = f'<!-- BEGIN --> \r\n最后更新时间 {datetime.now()} \r\n' + _render_md_list(news) + '\r\n<!-- END -->'
    with open('./README.md', 'r', encoding='utf-8') as f:
        readme = f.read()
    content = re.sub(r'<!-- BEGIN -->[\s\S]*<!-- END -->', block, readme)
    save('./README.md', content)
    print("更新README完毕...")


def save_archive(date: str, news: dict[str, HotEntry]) -> None:
    body = f'## {date}热门搜索 \r\n最后更新时间 {datetime.now()} \r\n' + _render_md_list(news) + '\r\n'
    save(_archive_path(date, 'md'), body)
    print("保存归档完毕...")


if __name__ == '__main__':
    bjtime = datetime.utcnow() + timedelta(hours=8)
    ymd = bjtime.strftime("%Y-%m-%d")
    url = f'{baseurl}/top/summary?cate=realtimehot'
    content = fetch_weibo(url)
    hot_news = parse_weibo(content)
    sorted_news = daily_hot_news.merge(ymd, hot_news)
    save_csv(ymd, sorted_news)
    update_readme(sorted_news)
    save_archive(ymd, sorted_news)
