# -*- coding: utf-8 -*-

import atexit
from datetime import datetime, time
import logging
import logging.handlers
import os
import queue
import sys
import threading

import colorlog
import yaml


class PreciseConsoleFormatter(colorlog.ColoredFormatter):
    """마이크로초까지 지원하는 커스텀 콘솔 포맷터"""
    def formatTime(self, record, datefmt=None):
        # record.created 값을 datetime 객체로 변환
        dt = datetime.fromtimestamp(record.created)
        if datefmt:
            # 사용자가 지정한 datefmt로 초까지 포맷팅 후 마이크로초 추가
            s = dt.strftime(datefmt)
            # %f는 마이크로초(6자리)를 의미함
            return f"{s}.{dt.strftime('%f')}"
        else:
            return dt.isoformat(sep=' ', timespec='microseconds')

class PreciseFileFormatter(logging.Formatter):
    """마이크로초까지 지원하는 커스텀 포맷터"""
    def formatTime(self, record, datefmt=None):
        # record.created 값을 datetime 객체로 변환
        dt = datetime.fromtimestamp(record.created)
        if datefmt:
            # 사용자가 지정한 datefmt로 초까지 포맷팅 후 마이크로초 추가
            s = dt.strftime(datefmt)
            # %f는 마이크로초(6자리)를 의미함
            return f"{s}.{dt.strftime('%f')}"
        else:
            return dt.isoformat(sep=' ', timespec='microseconds')

class HTMLSMTPHandler(logging.handlers.SMTPHandler):
    def emit(self, record):
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # 메일 메시지 구성
            port = self.mailport or smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            
            msg = MIMEMultipart("alternative")
            msg['From'] = self.fromaddr
            msg['To'] = ",".join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)

            # HTML 양식 작성
            timestamp = datetime.fromtimestamp(record.created).isoformat(sep=' ', timespec='microseconds')
            html_body = f"""
            <html>
            <body>
                <h2 style="color: red;">[Critical System Error]</h2>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px;">시간</th><td>{timestamp}</td>
                    </tr>
                    <tr>
                        <th style="padding: 8px;">레벨</th><td style="color: red;"><b>{record.levelname}</b></td>
                    </tr>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px;">메시지</th><td>{record.getMessage()}</td>
                    </tr>
                </table>
                <p>발생 위치: {record.pathname} (Line: {record.lineno})</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            if self.username:
                if self.secure is not None:
                    smtp.starttls()
                smtp.login(self.username, self.password)
            
            smtp.sendmail(self.fromaddr, self.toaddrs, msg.as_string())
            smtp.quit()
        except Exception:
            self.handleError(record)

def handle_exception(exc_type, exc_value, exc_traceback):
    # KeyboardInterrupt(Ctrl+C)는 무시하고 정상 종료되도록 처리
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 로그에 기록 (파일 및 설정된 핸들러로 전달)
    # exc_info 인자에 예외 정보를 넘겨주면 Traceback이 자동으로 포함됩니다.
    logging.critical("처리되지 않은 예외 발생 (Unhandled Exception)", exc_info=(exc_type, exc_value, exc_traceback))

def handle_thread_exception(args):
    logging.critical(f"스레드 예외 발생: {args.exc_type}", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

def setup_sync_logging(
        logpath=os.path.join(os.path.abspath(os.path.curdir), "logs", "app.log"),
        yamlpath=os.path.join(os.path.abspath(os.path.curdir), "app.yaml")):
    setCommonLogging(logpath)

    # 1. 공통 포맷 설정
    log_file_format, log_console_format, log_basic_format, date_format = getFormats()

    # 핸들러
    console_handler = getConsoleHandler(log_console_format, date_format)
    file_handler = getFileHandler(log_file_format, date_format, logpath)
    mail_handler = getEmailHandler(log_file_format, date_format, yamlpath)

    # 2. 루트 로거에 핸들러를 '직접' 추가 (동기식 핵심)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 기존에 등록된 핸들러가 있다면 제거 (중복 방지)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 핸들러들을 루트 로거에 연결
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(mail_handler)

    # 비동기 관련 코드(Queue, QueueListener, atexit)는 모두 제거됨

    return root_logger

def setup_async_logging(
        logpath=os.path.join(os.path.abspath(os.path.curdir), "logs", "app.log"),
        yamlpath=os.path.join(os.path.abspath(os.path.curdir), "app.yaml")):
    setCommonLogging(logpath)

    # 1. 로그 메시지를 담을 큐 생성 (비동기 핵심)
    log_queue = queue.Queue(-1)

    # 2. 공통 포맷 설정
    log_file_format, log_console_format, log_basic_format, date_format = getFormats()

    # 핸들러
    console_handler = getConsoleHandler(log_console_format, date_format)
    file_handler = getFileHandler(log_file_format, date_format, logpath)
    mail_handler = getEmailHandler(log_file_format, date_format, yamlpath)

    # 3. QueueListener 설정 (큐에서 로그를 꺼내 위 핸들러들로 전달)
    # 이 리스너가 백그라운드 스레드에서 실제 I/O 작업을 수행합니다.
    listener = logging.handlers.QueueListener(
        log_queue, console_handler, file_handler, mail_handler, respect_handler_level=True
    )
    listener.start()

    # 4. 루트 로거 설정 (사용자가 호출하는 인터페이스)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 중요: 루트 로거에는 오직 QueueHandler만 등록합니다.
    queue_handler = logging.handlers.QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)

    # 5. 프로그램 종료 시 안전하게 리스너를 멈추도록 등록
    atexit.register(listener.stop)

    return root_logger

def setCommonLogging(logpath=os.path.join(os.path.abspath(os.path.curdir), "logs", "app.log")):
    # 로그 파일 생성을 위한 디렉토리 체크 및 생성
    if os.path.exists(os.path.dirname(logpath)) == False:
        os.makedirs(os.path.dirname(logpath))

    # 전역 예외 처리기로 등록
    sys.excepthook = handle_exception
    # 스레드 전역 예외 처리기로 등록
    threading.excepthook = handle_thread_exception

def getFormats():
   # %(pathname)s            경로  로그를 호출한 소스 파일의 전체 경로
    # %(filename)s            파일명  파일명만 출력 (예: main.py)
    # %(module)s              모듈명  모듈 이름 (파일명에서 확장자 제외)
    # %(funcName)s            함수/메서드명  로그를 호출한 함수 또는 메서드의 이름
    # %(lineno)d              라인 번호  로그가 호출된 소스 코드의 줄 번호
    # %(thread)d              스레드 ID  현재 스레드 ID (숫자)
    # %(threadName)s          스레드 이름  현재 스레드 이름 (기본값: MainThread)
    # %(process)d             프로세스 ID  현재 프로세스 ID (PID)
    # %(relativeCreated)d     상대적 시간  로깅 모듈이 로드된 시점 기준 경과 시간(ms)
    log_file_format = "[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s.%(funcName)s:%(lineno)d] - %(message)s"
    log_console_format = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    log_basic_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    return log_file_format, log_console_format, log_basic_format, date_format

def getConsoleHandler(log_console_format, date_format):
    console_formatter = PreciseConsoleFormatter(
        "%(log_color)s" + log_console_format,
        datefmt=date_format,
        log_colors={
            'DEBUG': 'cyan',
            # 'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red,bg_white',
        }
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    return console_handler

def getFileHandler(log_file_format, date_format, logpath):
    # TimedRotatingFileHandler는 자정마다 파일을 교체합니다.
    file_formatter = PreciseFileFormatter(log_file_format, datefmt=date_format)
    # file_handler = logging.handlers.RotatingFileHandler(
    #     filename=filepath,
    #     maxBytes=10485760,          # 10MB (10 * 1024 * 1024 bytes)
    #     backupCount=9,              # 백업 파일은 최대 9개까지 유지
    #     encoding="utf-8"
    # )
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=logpath,
        when="D",                   # 'D'는 일 단위
        interval=1,                 # 1일차로 로테이션
        atTime=time(2, 0, 0),       # 새벽 2시 0분 0초에 실행
        backupCount=180,
        encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)

    return file_handler

def getEmailHandler(log_file_format, date_format, yamlpath):

    with open(yamlpath, 'r', encoding='utf-8') as f:
        yamlfile = yaml.full_load(f)

    # (C) SMTP 이메일 핸들러 (Critical 전용)
    email_config = yamlfile['logging']['email']
    mail_handler = HTMLSMTPHandler(
        mailhost=tuple(email_config['mailhost']),
        fromaddr=email_config['fromaddr'],
        toaddrs=email_config['toaddrs'],
        subject="[System Critical] Alert",
        credentials=tuple(email_config['credentials']),
        secure=()
    )    
    mail_handler.setLevel(logging.CRITICAL)
    mail_formatter = PreciseFileFormatter(log_file_format, datefmt=date_format)
    mail_handler.setFormatter(mail_formatter)

    return mail_handler
