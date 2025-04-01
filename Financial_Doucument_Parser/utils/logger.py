import os
import socket
import logging
from logging.handlers import TimedRotatingFileHandler

SERVER_NAME = "Financial_Agent"
log_dir = './logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"{socket.gethostname()}.log")
open(log_file, 'a').close()

log_level = logging.DEBUG if os.getenv('ENV') == 'local' else logging.INFO
logger = logging.getLogger(SERVER_NAME)
logger.setLevel(log_level)

format = '%(asctime)s | [%(levelname)s] | [%(traceid)s] | %(message)s'

handler = TimedRotatingFileHandler(filename=log_file, when='D', interval=1, backupCount=15)
handler.suffix = "%Y-%m-%dT%H:%M:%S%z"
handler.setFormatter(logging.Formatter(format))
logger.addHandler(handler)

### 控制台显示日志
# sh_handler = logging.StreamHandler()
# console_handler.setLevel(level=logging.DEBUG)
# console_handler.setFormatter(logging.Formatter(format))
# logger.addHandler(console_handler)

class TraceFilter(logging.Filter):
    traceid = 'x1234567890x'

    def filter(self, record):
        record.traceid = self.traceid
        return True

filter = TraceFilter()
logger.addFilter(filter)

info_logger = logger
