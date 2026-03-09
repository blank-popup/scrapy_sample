# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import logging

from itemadapter import ItemAdapter
from twisted.enterprise import adbapi
import psycopg2.extras
import yaml


logger = logging.getLogger(__name__)

class NaverPipeline:
    def __init__(self, dbpool):
        logger.error(f"$$$$$ NaverPipeline __init__ called [{dbpool}]")
        self.dbpool = dbpool

    @classmethod
    def from_crawler(cls, crawler):
        logger.error(f"$$$$$ NaverPipeline from_crawler called [{crawler}]")
        # 1. settings에서 YAML 경로 가져오기
        yamlpath = crawler.settings.get('AHA_YAMLPATH')
        
        # 2. YAML 파일 로드
        with open(yamlpath, 'r', encoding='utf-8') as f:
            yarmfile = yaml.safe_load(f)
        
        # 3. YAML에서 DB 설정 추출
        db_settings = yarmfile.get('database', {}).get('postgres', {})
        logger.info(f"Loaded DB settings from YAML: {db_settings}")
        
        # 4. 커넥션 풀 설정 (기존 로직 유지)
        dbparams = dict(
            host=db_settings.get('host'),
            port=db_settings.get('port', 5432),
            database=db_settings.get('dbname'),
            user=db_settings.get('user'),
            password=db_settings.get('password'),
            cp_min=3,
            cp_max=10,
            cursor_factory=psycopg2.extras.DictCursor
        )
        
        # 5. 비동기 풀 생성 및 인스턴스 반환
        dbpool = adbapi.ConnectionPool('psycopg2', **dbparams)
        return cls(dbpool)

    def process_item(self, item, spider):
        logger.error(f"$$$$$ NaverPipeline process_item called [{item}]")
        # runInteraction을 통해 비동기적으로 DB 작업 수행
        query = self.dbpool.runInteraction(self.insert_db, item)
        query.addErrback(self.handle_error, item, spider)
        return item

    def insert_db(self, cursor, item):
        logger.error(f"$$$$$ NaverPipeline insert_db called [{item}]")
        # PostgreSQL 테이블 구조에 맞춘 SQL
        sql = """
            INSERT INTO stock_indices (index_name, current_value) 
            VALUES (%s, %s)
        """
        # (중요) item 객체에서 데이터를 튜플 형태로 추출
        cursor.execute(sql, (
            item.get('index_name'),
            item.get('current_value')
        ))

    def handle_error(self, failure, item, spider):
        logger.error(f"$$$$$ NaverPipeline handle_error called [{failure}] [{item}]")
        logger.error(f"DB Error: {failure}")
        logger.error(f"Failed to insert item: {item}")

    def close_spider(self, spider):
        logger.error(f"$$$$$ NaverPipeline close_spider called [{spider}]")
        self.dbpool.close()
