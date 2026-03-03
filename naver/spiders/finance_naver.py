import scrapy


class FinanceNaverSpider(scrapy.Spider):
    name = "finance_naver"
    allowed_domains = ["finance.naver.com"]
    start_urls = ["https://finance.naver.com/"]

    def parse(self, response):
        pass
