import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    ENV = os.environ.get('FLASK_ENV')
    APP_NAME = os.environ.get('APP_NAME') or "Rally Call"
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
    TWILIO_VOICE_SETTING = os.environ.get('TWILIO_VOICE_SETTING') or 'Polly.Matthew'
    TWILIO_RECORDING_MAXLENGTH = os.environ.get('TWILIO_RECORDING_MAXLENGTH') or 300
    TWILIO_INBOUND_NUMBER = os.environ.get('TWILIO_INBOUND_NUMBER')
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    POSTS_PER_PAGE = 30