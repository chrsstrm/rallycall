import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    ENV = os.environ.get('FLASK_ENV')
    APP_BASE_URL = os.environ.get('APP_BASE_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'meet me at the rally point'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    BOOTSTRAP_ADMIN_PASS = os.environ.get('BOOTSTRAP_ADMIN_PASS')
    BOOTSTRAP_ADMIN_EMAIL = os.environ.get('BOOTSTRAP_ADMIN_EMAIL')
    SECURITY_POST_LOGIN_VIEW = '/home'
    SECURITY_REGISTERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_SEND_PASSWORD_RESET_NOTICE_EMAIL = False
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
    SECURITY_SEND_REGISTER_EMAIL = False #temp change before prod
    CREW_ACCOUNT_PIN_LENGTH = os.environ.get('CREW_ACCOUNT_PIN_LENGTH') or 6