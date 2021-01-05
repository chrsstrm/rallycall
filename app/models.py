from app import app
from app import db
from datetime import datetime
import uuid
import re
import random
from sqlalchemy import Enum
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin

user_status = ('created', 'invited', 'active', 'inactive', 'suspended', 'deleted')
user_status_enum = Enum(*user_status, name='user_status')
crew_status = ('created', 'active', 'inactive', 'suspended', 'deleted')
crew_status_enum = Enum(*crew_status, name='crew_status')
message_status = ('created', 'listened_to', 'deleted')
message_status_enum = Enum(*message_status, name='message_status')

roles_users = db.Table('roles_users',
    db.Column('user_id', db.String(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    """Authentication roles. 

    This class holds auth roles as set up by flask-security.
    """
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '<Role ID: {}'.format(self.name)

class Users(db.Model, UserMixin):
    """
    The User model consists of accounts with potentially 1 of 3 roles:
    1. System Admin - god mode to administer system
    2. Crew Admin - controls a Crew, can administer all Crew settings and data as well as add members. 
    3. Basic User - member of a crew, no real permissions other than create and listen to Messages. 

    For all intents and purposes, roles 2 & 3 will not use the interface very much, if at all. 
    Crew Admins are likely to log in when creating their account or when adding new members. Basic Users 
    are not at all required to log in - they really only need to exist if they desire to create their own 
    personal Access Code. 
    We might eventually expose messages in the browser when logged into the account, but roles 2 & 3 will use the 
    system almost exclusively through a voice phone line when creating and listening to Messages. 
    """
    id = db.Column(db.String(40), primary_key=True,  default=str(uuid.uuid1()))
    email = db.Column(db.String(120), index=True, unique=True)
    name = db.Column(db.String())
    created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(user_status_enum)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed = db.Column(db.DateTime())
    access_code = db.Column(db.String)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('user', lazy='dynamic'))
    crew_id = db.Column(db.String, db.ForeignKey('crews.id'))

    def __init__(self, **kwargs):
        app.logger.debug("Init User")
        super(Users, self).__init__(**kwargs)
        self.id = str(uuid.uuid1())
        self.created = datetime.utcnow()
        self.status = 'created'
    
    def __repr__(self):
        return("{} - {} - {} - {}".format(self.__class__.__name__, self.email, str(self.id), str(self.roles)))

    def to_dict(self):
        data = {
            'id': self.id,
            'email': self.email,
            'status': self.status,
            'active': self.active,
        }
        return data

    def from_dict(self, data, new_user=False):
        for field in ['id', 'status', 'email', 'active']:
            if field in data:
                setattr(self, field, data[field])

class Crews(db.Model):
    '''
    A Crew is a collection of users, lead by the user with 'crew_admin' role. 
    All Messages belong to a Crew, not its users. 
    Retrieving the Messages of a Crew will require the account_pin, which is the 
    identifier for said Messages. 
    If the Crew account is 'protected' then Messages will not be played unless unlocked 
    by the 'access_code' > 'user_access_code', in that order, should each exist. 
    The 'account_pin' is a randomly generated 6 digit pin code which is uniqued and indexed. 
    If the system expands beyond the need for 6 digit codes, 'account_pin' can be changed to 9 digits 
    by altering the app.Config['CREW_ACCOUNT_PIN_LENGTH'] env var. 

    _We're storing the PIN and access codes as strings. Why? It's easier to separate each digit 
    as a str and that's something that will happen quite often here._
    '''
    id = db.Column(db.String(40), primary_key=True,  default=str(uuid.uuid1()))
    name = db.Column(db.String())
    account_pin = db.Column(db.String)
    access_code = db.Column(db.String)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(crew_status_enum)
    members = db.relationship('Users', backref='crew', lazy='dynamic')
    messages = db.relationship('Messages', back_populates="crew", order_by="desc(Messages.created)", lazy='dynamic')

    def __init__(self, **kwargs):
        app.logger.debug("Init Crew")
        super(Crews, self).__init__(**kwargs)
        self.id = str(uuid.uuid1())
        self.created = datetime.utcnow()
        self.status = 'created'
        self.account_pin = self.generate_crew_pin()

    def generate_crew_pin(self):
        '''
        Pick a random account PIN that is the length of the config var CREW_ACCOUNT_PIN_LENGTH

        Generate a random sequence of digits, convert them to a str, search for existing account PIN. 
        Loop until we have a unique PIN, then return it. 
        '''
        str_set = ''
        satisfied = False
        while not satisfied:
            potential_set = random.choices([1,2,3,4,5,6,7,8,9,0], k=int(app.config['CREW_ACCOUNT_PIN_LENGTH']))
            str_set = ''.join(str(x) for x in potential_set)
            existing_crew = Crews.query.filter_by(account_pin=str_set).first()
            if existing_crew:
                continue
            else:
                satisfied = True
        return str_set
    
    def gather_access_codes(self):
        """
        Since a "protected" account can be accessed by either the Crew's global access code or 
        a Crew member's individual code, we're going to simply gather them all and return them 
        in a list. Then our verification routine will just look for provided_code in list. 
        """
        code_list = [str(self.access_code)]
        member_codes = Users.query.filter_by(crew_id=self.id).filter(Users.access_code.isnot(None)).all()

        if member_codes:
            for code in member_codes:
                code_list.append(code.access_code)
        return code_list

class Messages(db.Model):
    id = db.Column(db.String(40), primary_key=True,  default=str(uuid.uuid1()))
    url = db.Column(db.String)
    listen_count = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(message_status_enum)
    crew_id = db.Column(db.String, db.ForeignKey('crews.id'))
    crew = db.relationship("Crews", back_populates="messages")

    def __init__(self, **kwargs):
        app.logger.debug("Init Message")
        super(Messages, self).__init__(**kwargs)
        self.id = str(uuid.uuid1())
        self.created = datetime.utcnow()
        self.status = 'created'

    def increment_listen_count(self):
        old_count = self.listen_count
        self.listen_count = old_count + 1
        db.session.commit()
    
    def to_dict(self):
        data = {
            'id': self.id,
            'url': self.url,
            'status': self.status,
            'created': self.created,
        }
        return data
    
    @staticmethod
    def make_ordered_list(obj):
        """
        We want to convert a list of Message objects to a list of dicts that contain 
        each Message obj vars. 
        This is primarily so we can store this in a session. 
        """
        ordered_list = []
        for item in obj:
            ordered_list.append(item.to_dict())
        return ordered_list

class AppSafeConfig(object):
    """
    Instantiate an object of safe env vars we can use in templates. 
    """
    def __init__(self):
        self.app_name = app.config['APP_NAME']
        self.app_inbound_number = app.config['TWILIO_INBOUND_NUMBER']
        self.pretty_app_inbound_number = self.pretty_phone()
    
    def pretty_phone(self):
        fancy_num = re.search(r'^(?P<country>\+\d{1})(?P<area>\d{3})(?P<prefix>\d{3})(?P<subscriber>\d{4})$', self.app_inbound_number, flags=re.IGNORECASE)
        if fancy_num:
            normalized = f"{str(fancy_num.group('country'))} ({str(fancy_num.group('area'))}) {str(fancy_num.group('prefix'))}-{str(fancy_num.group('subscriber'))}"
            return normalized
        else:
            return self.app_inbound_number