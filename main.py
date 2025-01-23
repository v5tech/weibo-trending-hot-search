import json
import os
import os.path
import re
from datetime import datetime, timedelta

import imageio.v3 as imageio
import jieba
import requests
from lxml import etree
from matplotlib import pyplot as plt
from requests.exceptions import RequestException
from wordcloud import WordCloud
from wordcloud import ImageColorGenerator
import boto3

utctime = datetime.utcnow()
bjtime = utctime + timedelta(hours=8)
baseurl = 'https://s.weibo.com'
ym = bjtime.strftime("%Y%m")
ymd = bjtime.strftime("%Y-%m-%d")
archive_filepath = f"./archives/{ym}/{ymd}"
raw_filepath = f"./raw/{ym}/{ymd}"


# 加载文件
def load(filename):
    with open(filename, 'r', encoding="utf-8") as f:
        content = f.read()
    return content


# 保存文件
def save(filename, content):
    # 获取文件目录
    file_path = os.path.dirname(filename)
    # 判断目录是否存在
    if not os.path.exists(file_path):
        # 创建目录
        os.makedirs(file_path)
    with open(filename, 'w', encoding="utf-8") as f:
        if filename.endswith('.json') and isinstance(content, dict):
            json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            f.write(content)


# 获取内容
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


# xpath解析微博热搜数据
def parse_weibo(content):
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


# 更新榜单，与当天历史榜单对比去重，降序排列
def update_hot_news(hot_news):
    his_filename = raw_filepath + ".json"
    if not os.path.exists(his_filename):
        save(his_filename, {})
    # 读取当天历史榜单
    his_hot_news = json.loads(load(his_filename))
    for k, v in hot_news.items():
        # 若当天榜单和历史榜单有重复，取热度数值更大的这一个
        if k in his_hot_news:
            his_hot_news[k]['hot'] = max(int(his_hot_news[k]['hot']), int(hot_news[k]['hot']))
            # 若没有，则添加到榜单
        else:
            his_hot_news[k] = v
    # 将榜单按hot值排序
    sorted_news = {k: v for k, v in sorted(his_hot_news.items(), key=lambda item: int(item[1]['hot']), reverse=True)}
    save(his_filename, sorted_news)
    save_csv(sorted_news)
    return sorted_news


# 加载停用词
def stopwords():
    stopwords = [line.strip() for line in open('stopwords.txt', encoding='UTF-8').readlines()]
    return stopwords


# 保存csv
def save_csv(sorted_news):
    str = f'{ymd},' + ",".join([k for k, v in sorted_news.items()])
    save(f'{archive_filepath}.csv', str)


# 生成词云
def wordcloud(sorted_news):
    str = f'{ymd},' + ",".join([k for k, v in sorted_news.items()])
    sentence_seged = jieba.lcut(str)
    swords = stopwords()
    jieba_text = []
    for word in sentence_seged:
        if word not in swords:
            jieba_text.append(word)
    wd_join_text = " ".join(jieba_text)
    mask = imageio.imread("weibo.png")
    wc = WordCloud(font_path="msyh.ttf",
                   background_color="white",  # 背景颜色
                   max_words=1000,  # 词云显示的最大词数
                   max_font_size=100,  # 字体最大值
                   min_font_size=5,  # 字体最小值
                   random_state=42,  # 随机数
                   collocations=False,  # 避免重复单词
                   width=1200, height=970,
                   margin=2,
                   mask=mask)
    wc.generate_from_text(wd_join_text)
    # 调用wordcloud库中的ImageColorGenerator()函数，提取mask图片各部分的颜色
    image_colors = ImageColorGenerator(mask)
    wc.recolor(color_func=image_colors)
    plt.figure(dpi=150)  # 放大或缩小
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")  # 隐藏坐标
    wc_img_path = f"{archive_filepath}.png"
    wc.to_file(wc_img_path)
    print("生成词云完毕...")
    return wc_img_path


# 上传词云文件到s3存储桶
def upload_s3(wc_img_path, s3_config):
    s3 = boto3.resource(service_name='s3',
                        endpoint_url=s3_config.get('endpoint_url'),
                        aws_access_key_id=s3_config.get('aws_access_key_id'),
                        aws_secret_access_key=s3_config.get('aws_secret_access_key'))
    file_name = "{}/{}".format(bjtime.strftime('%Y%m%d'), os.path.basename(wc_img_path))
    with open(wc_img_path, 'rb') as f:
        obj = s3.Bucket(s3_config.get('bucket_name')) \
            .put_object(Key=file_name, Body=f, ContentType="image/png", ACL="public-read")
        response = {attr: getattr(obj, attr) for attr in ['e_tag', 'version_id']}
        upload_url = f'{s3_config.get("img_access_url")}/{file_name}?versionId={response["version_id"]}'
    print("上传词云完毕...")
    os.remove(wc_img_path)
    return upload_url


# 更新README
def update_readme(news, wc_img_upload_url):
    line = '1. [{title}]({url}) {hot}'
    lines = [line.format(title=k, hot=v['hot'], url=v['url']) for k, v in news.items()]
    lines = '\n'.join(lines)
    # lines = f'<!-- BEGIN --> \r\n最后更新时间 {datetime.now()} \r\n![{ymd}]({wc_img_upload_url}) \r\n' + lines + '\r\n<!-- END -->'
    lines = f'<!-- BEGIN --> \r\n最后更新时间 {datetime.now()} \r\n' + lines + '\r\n<!-- END -->'
    content = re.sub(r'<!-- BEGIN -->[\s\S]*<!-- END -->', lines, load('./README.md'))
    save('./README.md', content)
    print("更新README完毕...")


# 保存归档
def save_archive(news, wc_img_upload_url):
    line = '1. [{title}]({url}) {hot}'
    lines = [line.format(title=k, hot=v['hot'], url=v['url']) for k, v in news.items()]
    lines = '\n'.join(lines)
    # lines = f'## {ymd}热门搜索 \r\n最后更新时间 {datetime.now()} \r\n![{ymd}]({wc_img_upload_url}) \r\n' + lines + '\r\n'
    lines = f'## {ymd}热门搜索 \r\n最后更新时间 {datetime.now()} \r\n' + lines + '\r\n'
    save(f'{archive_filepath}.md', lines)
    print("保存归档完毕...")


# 检查s3存储桶环境变量
def s3_env_config():
    env_variables = [
        'ENDPOINT_URL',
        'IMG_ACCESS_URL',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'BUCKET_NAME'
    ]
    env_config = {}
    for variable in env_variables:
        env_value = os.environ.get(variable)
        if not env_value:
            print(f'请设置 {variable} 环境变量')
            return None
        env_config[variable.lower()] = env_value
    return env_config


if __name__ == '__main__':
    s3_config = s3_env_config()
    if not s3_config:
        exit(1)
    url = f'{baseurl}/top/summary?cate=realtimehot'
    content = fetch_weibo(url)
    hot_news = parse_weibo(content)
    sorted_news = update_hot_news(hot_news)
    # wc_img_path = wordcloud(sorted_news)
    # wc_img_upload_url = upload_s3(wc_img_path, s3_config)
    update_readme(sorted_news, "")
    save_archive(sorted_news, "")
