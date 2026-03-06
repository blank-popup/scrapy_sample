@echo off
:: 프로젝트 폴더로 이동
cd /d "D:\WorkSpace\Scrap"
:: 가상환경의 파이썬으로 스크립트 실행 (인자값 포함)
"D:\WorkSpace\Scrap\.venv\Scripts\python.exe" main.py --logpath "./logs/BOT_kospi.log" --yamlpath "./scrapy_me.yaml"
