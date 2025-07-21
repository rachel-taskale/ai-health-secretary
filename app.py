from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

from call_handler import setup_routes
setup_routes(app, sock)