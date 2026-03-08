# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class StockIndexItem(scrapy.Item):
    index_name = scrapy.Field()    # 'KOSPI'
    current_value = scrapy.Field() # 2560.15
    # 추가 필드가 필요하다면 아래에 정의
    # change_value = scrapy.Field()
    # change_rate = scrapy.Field()