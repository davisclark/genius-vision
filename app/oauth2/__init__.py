from flask import Blueprint

oauth2 = Blueprint('oauth2', __name__)

from . import genius