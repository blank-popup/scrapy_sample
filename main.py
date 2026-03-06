import click
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from logit.config import setup_logging
from naver.spiders.finance_naver import FinanceNaverSpider


def main():
    print("Hello from scrap!")

@click.command()
@click.option('--logpath', default='logs/scrapy.log', help='Log file path')
@click.option('--yamlpath', default='scrapy.yaml', help='YAML config path')
def run_spider(logpath, yamlpath):
    # 1. Scrapy 설정 로드 및 커스텀 설정 적용
    settings = get_project_settings()
    settings.set('LOG_ENABLED', False) # 직접 만든 로깅을 쓰므로 Scrapy 기본 로깅은 끔

    # 2. 기존에 만든 로깅 설정 호출
    setup_logging(logpath=logpath, yamlpath=yamlpath)

    # 3. 프로세스 생성 및 스파이더 실행
    process = CrawlerProcess(settings)
    process.crawl(FinanceNaverSpider)
    process.start() # 이 줄에서 크롤링이 시작되고 완료될 때까지 블로킹됩니다.

if __name__ == "__main__":
    run_spider()
