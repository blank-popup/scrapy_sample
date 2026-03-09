import scrapy

from naver.items import StockIndexItem


class FinanceNaverSpider(scrapy.Spider):
    name = "finance_naver"
    allowed_domains = ["finance.naver.com"]
    start_urls = ["https://finance.naver.com/"]

    def parse(self, response):
        self.logger.error("$$$$$ FinanceNaverSpider.parse called")
        kospi = response.xpath('//*[@id="content"]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/a/span/span[1]/text()').get()
        self.logger.error(f"$$$$$ KOSPI: {kospi}")
        if kospi:
            item = StockIndexItem()
            item['index_name'] = 'KOSPI'
            # '2,560.15' -> 2560.15 로 변환
            item['current_value'] = float(kospi.replace(',', ''))
            
            yield item
