
from tornado.web import RequestHandler
from .app import TunManApplication


class ServeStatusHandler(RequestHandler):
    app: TunManApplication = None
