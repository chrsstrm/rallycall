from app import app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, or_, desc
from app import db
from flask import jsonify, request, render_template, url_for, redirect, flash, session, Response, send_file, send_from_directory
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, current_user, user_registered
from flask_security.utils import encrypt_password, verify_password, hash_password, login_user, send_mail
from flask_security.decorators import roles_required, roles_accepted
import os
from app.models import Users, Role, Crews

basedir = os.path.abspath(os.path.dirname(__file__))
user_datastore = SQLAlchemyUserDatastore(db, Users, Role)
security = Security(app, user_datastore)

@app.before_first_request
def bootstrap_app():
    """Bootstrap the Flask app.

    On first request we want to make sure our app is properly bootstrapped. 
    This involves setting up our user roles and pre-generating an admin user. 

    We have three roles: 
    1. System Admin - The super admin who controls the entire system - unlimited permissions. 
    2. Account Admin - The owner of a Crew. These permissions allow administering the Crew and its members. 
    3. Basic User - A member of a Crew, least priviledges. 

    *This func will only run when the first _request_ is made, not when the app starts*
    To properly bootstrap the app, start the app and then visit / or /login, then promptly use the Reset Password function 
    to change the System Admin password.  
    """
    db.create_all()
    app.logger.debug('doing bootstrap')
    bootstrap_email = app.config['BOOTSTRAP_ADMIN_EMAIL']
    #check for roles
    admin = user_datastore.find_role('admin')
    if not admin:
        user_datastore.create_role(name='admin', description='admin user role')
        db.session.commit()
        admin = user_datastore.find_role('admin')
    crew_admin = user_datastore.find_role('crew_admin')
    if not crew_admin:
        user_datastore.create_role(name='crew_admin', description='crew_admin user role')
        db.session.commit()
    basic_user = user_datastore.find_role('basic_user')
    if not basic_user:
        user_datastore.create_role(name='basic_user', description='basic user role')
        db.session.commit()
    #check for system admin user
    admin_user = user_datastore.find_user(email=bootstrap_email)
    if not admin_user:
        user_datastore.create_user(email=bootstrap_email, password=hash_password(app.config['BOOTSTRAP_ADMIN_PASS']))
        db.session.commit()
        admin_user = user_datastore.find_user(email=bootstrap_email)
        user_datastore.add_role_to_user(admin_user, admin)
        db.session.commit()

@app.context_processor
def inject_crew():
    """Make sure to include the crew object in each route 
    for use in the template. 
    """
    user = current_user
    if user.has_role('crew_admin') or user.has_role('basic_user'):
        return dict(crew=Crews.query.get(user.crew_id))
    else:
        return dict(crew=None)

@app.route('/')
def index_route():
    '''
    Our public homepage. 
    '''
    return render_template('root-index.html')

@user_registered.connect_via(app)
def user_registered_sighandler(sender, user, confirm_token):
    '''
    We're going to use the Flask-Security built in /register endpoint to register 
    a user, but we will also need to assign this user a role and bootstrap their 
    Crew (any user using /register will be a Crew admin, basic users do not need to register).
    Hook into the user_registered Signal to make these changes when someone registers.

    1. Set user's role to 'crew_admin'
    2. Bootstrap the Crew
    '''
    # this next piece should maybe be wrapped in a try block.
    # if the user role wasn't found or couldn't be added to the user, 
    # what would we do? delete the user and tell them to register again?
    # we wouldn't want a random user in the system with no role or crew. 
    
    crew_admin = user_datastore.find_role('crew_admin')
    user_datastore.add_role_to_user(user, crew_admin)
    db.session.commit()
    
    crew = Crews()
    user.crew_id = crew.id
    db.session.add(crew)
    db.session.commit()

@app.route('/home')
def home_route():
    return render_template('home.html')

@app.errorhandler(404)
def page_not_found(e):
    '''
    Handle any pages not found. 
    '''
    return render_template('404.html'), 404

@app.errorhandler(500)
def system_err(e):
    """
    Handling a 500 error is simply to prevent display of debugging info or a browser-generated 
    error. 
    You should attempt to alert the system admin if this endpoint is ever reached, but monitoring 
    and error collection is out of scope for this iteration of the project.   
    """
    return render_template('500.html'), 500
