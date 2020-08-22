# coding:utf8
import re
import time
import json
import scrapy
import datetime
import requests
from scrapy_redis.spiders import RedisSpider


# class SinaSpider(RedisSpider):
class SinaSpider(scrapy.Spider):
    name = 'sina'
    allowed_domains = ['sina.com.cn']
    start_urls = ['http://mil.news.sina.com.cn/roll/index.d.html']

    def parse(self, response):
        # print("P"*30)  # xpath('a/text()').extract()
        data_item = {}
        tag_ul = response.xpath("//ul[@class='linkNews']/li")
        # print("======>>>", len(tag_ul))
        _now = datetime.datetime.now().minute
        for ul in tag_ul:
            # t = ul.extract()
            detail_url = ul.xpath("a/@href").get()
            # date = ul.xpath("span/text()").get()  # 18:02
            date_time = ul.xpath("span/text()").re_first(r'\d{1,2}:\d{1,2}')
            _t = int(date_time.split(":")[-1])
            # 根据近一些录入的缓存数据做对比判断是否是新的数据
            if _now <= _t:
                yield scrapy.Request(detail_url, self.detail_parse)
                # yield {"detail_url": detail_url}

        next_page = response.xpath("//a[@title='下一页']/@href").get()
        if next_page and int(next_page.split("=")[-1]) < 2:  # 控制在5页内
            # self.start_urls.append(next_page)
            time.sleep(2)
            yield scrapy.Request(next_page, self.parse)

    def detail_parse(self, response):
        """
        解析出内容详情以及动态的评论
        评论数量是动态加载进来的，与其使用ChromeDriver，这里使用加载评论列表 反向推算出来(品论响应接口中有总评论数)
        """
        _detail = {}  # text()').extract()
        title = response.xpath("//h1[@class='main-title']/text()").get()
        _datetime = response.xpath("//span[@class='date']/text()").get()
        _body = response.xpath("//div[@id='article']").get()   # 保留标签
        # 评论数量
        # https://mil.news.sina.com.cn/2020-08-20/doc-iivhuipn9778137.shtml
        _news_id = re.findall(r"\d{5,}", response.url)[0]

        _detail["title"] = title
        _detail["body"] = _body
        _detail["datetime"] = _datetime
        # _comment_count = int(_comment_count)
        comment_list = []
        # 评论每页最大显示200条数据
        # jsonp_1597765850280({"result": {"status": {"msg": "Catch exception :page_size must less 200!", "code": 4}
        page_count = 1
        page_size = 200
        # 评论的分页请求地址
        comment_url = "http://comment.sina.com.cn/page/info?version=1&format=json&channel=jc&newsid=" \
                      "comos-ivhuipn{}&group=0&compress=0&ie=utf-8&oe=utf-8&page={}&page_size={}"
        comment_list, _comment_count = self.comment_parse(comment_url.format(_news_id, page_count, page_size))

        # 有评论
        if _comment_count > 0:

            if _comment_count % page_size > 0:
                page_count = int(_comment_count / 200) + 1
            elif _comment_count % page_size == 0:
                page_count = int(_comment_count / 200)
            # 第一页已经在试探总评论数时获取
            if page_count > 1:
                for number in range(2, page_count+1):
                    page_uri = comment_url.format(_news_id, number, page_size)
                    tmp_list, tmp_count = self.comment_parse(page_uri)
                    comment_list.extend(tmp_list)

        _detail["comments"] = comment_list

        yield _detail

    def comment_parse(self, uri):
        # 可以提取出去
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'
        }
        datas = []
        response = json.loads(requests.get(uri, headers=headers).text)
        if not response.get("result"):
            return datas, 0
        elif not response.get("result").get("count"):
            return datas, 0
        page_count = response.get("result").get("count").get("show")

        # 没有数据
        if page_count < 1:
            return [], 0
        comment_list = response.get("result").get("cmntlist")
        # 省略返回状态判断
        for comment in comment_list:
            datas.append({
                "uid": comment.get("uid"),
                "area": comment.get("area"),
                "content": comment.get("content"),
                "nick": comment.get("nick"),
                "time": comment.get("time"),
                "parent_uid": comment.get("parent_uid"),
            })

        return datas, page_count

