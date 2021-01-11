"""
Rally Call 

This app is designed to be a backup communication hub which allows persons to call in and 
either leave a voice memo or listen to voice memos from other members of their group. 

Copyright 2021 Chris Sturm <chris.sturm@gmail.com>

This application is licensed under the terms of BSD-3.
Please refer to LICENSE in the project repository for details.
"""
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes