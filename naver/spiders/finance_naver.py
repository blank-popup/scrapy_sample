import scrapy


class FinanceNaverSpider(scrapy.Spider):
    name = "finance_naver"
    allowed_domains = ["finance.naver.com"]
    start_urls = ["https://finance.naver.com/"]

    def parse(self, response):
        # 다음 2 줄 추가
        kospi = response.xpath('//*[@id="content"]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/a/span/span[1]/text()').get()
        self.logger.info(f"KOSPI: {kospi}")
        pass
