import logging


class MyHandler(logging.StreamHandler):

    def __init__(self, trail=False):
        logging.StreamHandler.__init__(self)
        if trail:  # Yennifer Bot
            fmt = '%(levelname)-5.5s| %(filename)-15s|%(lineno)-4d|%(asctime)s| %(message)s'
            fmt_date = "%H:%M:%S"  # '%Y-%m-%dT%T%Z'
            formatter = logging.Formatter(fmt, fmt_date)
            self.setFormatter(formatter)
        else:  # Violet Bot
            fmt = '%(filename)-15s|%(lineno)-4d| %(message)s'
            formatter = logging.Formatter(fmt)
            self.setFormatter(formatter)
            pass
