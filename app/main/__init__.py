from flask import Blueprint

main = Blueprint('main', __name__)

from datetime import date
from . import views, errors