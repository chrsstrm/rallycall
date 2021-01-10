from app import app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, or_, desc
from app import db
from flask import jsonify, request, render_template, url_for, redirect, flash, session, Response, send_file, send_from_directory
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, current_user, user_registered
from flask_security.utils import encrypt_password, verify_password, hash_password, login_user, send_mail, logout_user
from flask_security.decorators import roles_required, roles_accepted, login_required
import os
from app.models import Users, Role, Crews, Messages, AppSafeConfig
from app.forms import CrewSettings, CrewDelete
from twilio.twiml.voice_response import VoiceResponse, Say, Gather, Record, Play, Hangup
from twilio.rest import Client
import arrow

basedir = os.path.abspath(os.path.dirname(__file__))
user_datastore = SQLAlchemyUserDatastore(db, Users, Role)
security = Security(app, user_datastore)

@app.before_first_request
def bootstrap_app():
    """Bootstrap the Flask app.

    On first request we want to make sure our app is properly bootstrapped. 
    This involves setting up our user roles and pre-generating an admin user. 
    We also want to make sure our Twilio inbound number webhook is properly set (you will have 
    to set up your Twilio account and buy a number prior to booting this app.)

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
    # Update our Twilio account to make sure the inbound number we're using for this app 
    # has a proper webhook setting. 
    number_sid = ''
    try:
        client = Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])
        incoming_phone_numbers = client.incoming_phone_numbers.list(phone_number=app.config['TWILIO_INBOUND_NUMBER'], limit=1)
        for record in incoming_phone_numbers:
            number_sid = record.sid
    except Exception as _:
        app.logger.debug("Attempt to find given Twilio number failed. Check account credentials and Twilio Inbound Number and try again.")
    
    try:
        # Set the webhook for our inbound number to the 'account_lookup_route' entrypoint for our inbound calls. 
        # This block will make sure that our Twilio account is always up to date in terms of what the fqd 
        # endpoint is. This makes it easy to port this app from dev to prod and even to new domains without 
        # having to log into Twilio and make changes manually. 
        # The SMS URL is deliberately set to the empty string to reject any SMS sent to the number. 
        _ = client \
            .incoming_phone_numbers(number_sid) \
            .update(
                sms_url='',
                voice_method='POST',
                voice_url=url_for('account_lookup_route', _external=True, _scheme='https')
            )
    except Exception as _:
        app.logger.debug("Could not update Twilio inbound number properties")

def friendly_date(timestamp):
    """
    Define a template filter to display the Message creation date 
    in a more human-friendly form. 
    Then make sure to register the new filter. 
    """
    c_date = arrow.get(timestamp)
    return c_date.humanize()

def utc_date(timestamp):
    """
    Define a template filter to display UTC dates 
    """
    c_date = arrow.get(timestamp)
    return c_date.format(arrow.FORMAT_COOKIE)

app.add_template_filter(friendly_date)
app.add_template_filter(utc_date)

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

@app.context_processor
def inject_config():
    """Make sure to include the global configs in each route 
    for use in the template. 
    """
    config = AppSafeConfig()
    return dict(config=config)

@app.route('/')
def index_route():
    '''
    The public homepage. 
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
    user.crew_admin = True
    db.session.add(crew)
    db.session.commit()
    login_user(user)

@app.route('/home')
@login_required
@roles_accepted('crew_admin', 'basic_user', 'admin')
def home_route():
    return render_template('home.html')

@app.route('/home/messages', methods=['GET'])
@login_required
@roles_accepted('crew_admin', 'basic_user')
def home_messages_route():
    """
    Display all Messages for the Crew that are not deleted. 
    """
    crew = Crews.query.get(current_user.crew_id)
    page = request.args.get("page", 1, type=int)
    messages = Messages.\
        query.\
        filter_by(crew_id=crew.id).\
        filter(~Messages.status.in_(['deleted'])).\
        order_by(Messages.created.desc()).\
        paginate(page, app.config['POSTS_PER_PAGE'], True)
    
    next_url = url_for('home_messages_route', page=messages.next_num) if messages.has_next else None
    prev_url = url_for('home_messages_route', page=messages.prev_num) if messages.has_prev else None
    
    return render_template('home_messages.html', messages=messages.items, next=next_url, prev=prev_url)

@app.route('/home/messages/<id>', methods=['DELETE'])
@login_required
@roles_accepted('crew_admin')
def home_del_message_route(id):
    """
    Route just for deleting Messages. 
    We don't actually do a physical delete though, just set status to 'deleted'
    This route does not return a view, it redirects to the messages route. 
    """
    try:
        message = Messages.query.get(id)
        if message:
            message.status = 'deleted'
            db.session.commit()
            flash('Your message was deleted.', category='success')
        else:
            flash('This message does not exist.', category='error')
    except Exception as _:
        flash('This message could not be deleted.', category='error')
    
    return jsonify(success=True), 200, {'ContentType':'application/json'} 

@app.route('/home/settings', methods=['GET', 'POST'])
@login_required
@roles_accepted('crew_admin')
def home_settings_route():
    """
    Option for the Crew Admin to add a Crew Name and 
    'protect' the account by adding an Access Code.
    Can also delete the Crew from this view. 
    """
    crew = Crews.query.get(current_user.crew_id)
    form = CrewSettings(obj=crew)
    del_form = CrewDelete()
    
    if form.validate_on_submit():
        try:
            crew.name = form.name.data
            if form.access_code.data == '':
                crew.access_code = None
            else:    
                crew.access_code = form.access_code.data
            db.session.commit()
            flash('Your crew settings have been saved.', category='success')
            
        except Exception as _:
            flash('Your settings were not saved, an error ocurred.', category='error')
    
    return render_template('home_settings.html', form=form, del_form=del_form)

@app.route('/home/crews', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def home_admin_crews_route():
    """
    System Admin route for viewing all Crews in the system. 
    """
    page = request.args.get("page", 1, type=int)
    crews = Crews.query.paginate(page, app.config['POSTS_PER_PAGE'], True)
    next_url = url_for('home_admin_crews_route', page=crews.next_num) if crews.has_next else None
    prev_url = url_for('home_admin_crews_route', page=crews.prev_num) if crews.has_prev else None
    return render_template('home_crews.html', crews=crews.items)

@app.route('/home/crews/<id>', methods=['GET','POST', 'DELETE'])
@login_required
@roles_accepted('admin')
def home_admin_crew_route(id):
    """
    System Admin route for viewing details of a single Crew. 
    Can delete or suspend Crew from this view.
    """
    try:
        crew = Crews.query.get(id)
        if not crew:
            raise Exception('No crew found.')
    except Exception as _:
        flash('Could not access this Crew.', category='error')
        return redirect(url_for('home_admin_crews_route'))

    if request.method == 'DELETE':
        """
        System admin handler for 'deleting' a Crew. 

        TODO: This can be refactored along with the crew-admin delete endpoint by 
        adding Crew methods for deleting users and the Crew itself instead of 
        repeating code in multiple endpoint handlers. 
        """
        try:
            """
            Deactivate all Crew users and change their status. 
            active=False will not allow them to log in. 
            """
            users = Users.query.filter_by(crew_id=id).all()
            for user in users:
                user.active = False
                user.status = 'deleted'
            db.session.commit()
        except Exception as _:
            flash('Could not remove Crew members, please try again.', category='error')
            return redirect(url_for('home_admin_crew_route', id=id))
        
        try:
            """
            Change the Crew status to deleted
            """
            crew.status = 'deleted'
            db.session.commit()
        except Exception as _:
            flash('Could not remove Crew, please try again.', category='error')
            return redirect(url_for('home_admin_crew_route', id=id))

        flash('Crew deleted.', category='success')
        return redirect(url_for('home_admin_crews_route'))

    if request.method == 'POST':
        """
        This handler will look for the 'action' param to determine 
        whether we are going to restore or suspend the account.
        """
        if 'action' in request.args:
            if request.args.get('action') == 'suspend':
                """
                Set status of the Crew to suspended.
                This will not prevent the admin or users from 
                logging in, but they cannot listen to or record messages.
                """
                crew.status = 'suspended'
                db.session.commit()
                flash('Crew suspended.', category='success')
                return redirect(url_for('home_admin_crew_route', id=id))
            if request.args.get('action') == 'restore':
                """
                Restore a Crew.
                This will change the status of the Crew and restore login 
                access for all users. 
                This could conflict with a user that was previously removed from 
                a Crew, but I'm not sure how to solve this given the structure we 
                currently have. YOLO. 
                """
                crew.status = 'active'
                db.session.commit()
                users = Users.query.filter_by(crew_id=id).all()
                for user in users:
                    user.active = True
                    user.status = 'active'
                db.session.commit()
                flash('Crew restored.', category='success')
                return redirect(url_for('home_admin_crew_route', id=id))
        else:
            flash('Invalid request.', category='error')
            return redirect(url_for('home_admin_crew_route', id=id))

    admins = crew.members.filter_by(crew_admin = True).all()
    return render_template('home_crew.html', crew=crew, admins=admins)

@app.route('/crews', methods=['POST'])
@login_required
@roles_accepted('crew_admin')
def crew_delete_route():
    """
    Crews route that is currently strictly for deleting the entire 
    account. 
    Will prompt for the admin's password and then:
    - deactivate all members
    - deactivate the admin
    - set the status of the Crew to deleted
    """
    form = CrewDelete()
    crew = Crews.query.get(current_user.crew_id)
    
    if form.validate_on_submit():
        try:
            if verify_password(form.password.data, current_user.password):
                """
                Request the admin's password before we destroy the account
                """
                pass
            else:
                flash('Your password was not correct.', category='error')
                return redirect(url_for('home_settings_route'))
            
        except Exception as _:
            flash('There was an error deleting this account.', category='error')
            return redirect(url_for('home_settings_route'))

        try:
            """
            Deactivate all Crew users and change their status. 
            active=False will not allow them to log in. 
            """
            users = Users.query.filter_by(crew_id=crew.id).all()
            for user in users:
                user.active = False
                user.status = 'deleted'
            db.session.commit()
        except Exception as _:
            flash('Could not remove Crew members, please try again.', category='error')
            return redirect(url_for('home_settings_route'))
        
        try:
            """
            Change the Crew status to deleted
            """
            crew.status = 'deleted'
            db.session.commit()
        except Exception as _:
            flash('Could not remove Crew, please try again.', category='error')
            return redirect(url_for('home_settings_route'))

        # finally, log out the user
        logout_user()
        
    return redirect(url_for('index_route'))

@app.route('/account-lookup', methods=["POST"])
def account_lookup_route():
    '''
    This is the Twilio entrypoint for all incoming new calls. 
    This endpoint will play a welcome message and then gather the Account PIN to identify the account. 

    We will set a session var and allow 4 tries to get the Account PIN correct, otherwise we end the call (just 
    basic brute force protection). 

    If this request contains the 'Digits' var, then we have collected the Account PIN from the user and must verify it. 
    Successful verification will send the call to the 'main_menu_route' to offer the user the main menu. 

    If the Crew account contains an Access Code that is not None, we must send the call to the 'check_pin_route' endpoint. 
    Our check for whether or not this step is required will be determined by setting a session var 'Protected_Session'. This var 
    will be instantiated to False when created and must be changed to True in order to allow playing or recording of Messages. 
    '''
    resp = VoiceResponse()

    # if the request contains 'Digits' we know this is the result of a Gather and must check for the account pin
    if 'Digits' in request.values:
        provided_pin = str(request.values['Digits'])
        crew = Crews.query.filter_by(account_pin=provided_pin).first()
        
        # basic pin brute force protection that limits tries to 4
        if 'account_pin_tries' in session and session['account_pin_tries'] == 5:
            return redirect(url_for('hangup_route'), code=307)
        
        if crew is None:
            # crew not found or bad pin
            if not 'account_pin_tries' in session:
                session['account_pin_tries'] = 1
            else:
                session['account_pin_tries'] += 1
            gather = Gather(action=app.config['APP_BASE_URL'] + url_for('account_lookup_route'), method='POST', input="dtmf", timeout=3, finishOnKey='#')
            gather.say(f"Your input was not correct. Please input your account pin and then press the pound key.", voice=app.config['TWILIO_VOICE_SETTING'])
            resp.append(gather)
            return str(resp)
        elif crew.status in ['suspended', 'deleted']:
            # crew is deleted or deactivated by an admin, kill call
            resp.say(f"This account is deactivated. Goodbye.", voice=app.config['TWILIO_VOICE_SETTING'])
            hangup = Hangup()
            resp.append(hangup)
            return str(resp)
        elif crew.access_code is not None:
            # crew is using an access code, send to the check pin route
            session['sessionCrewId'] = crew.id
            return redirect(url_for('check_pin_route'), code=307)
        else:
            # crew exists and is in good standing, proceed
            session['sessionCrewId'] = crew.id
            return redirect(url_for('main_menu_route'), code=307)

    # this block will be run during the very first POST to this route, signaling a new incoming call
    gather = Gather(action=app.config['APP_BASE_URL'] + url_for('account_lookup_route'), method='POST', input="dtmf", timeout=3, finishOnKey='#')
    gather.say(f"You have reached { app.config['APP_NAME'] }. Please enter your account pin and then press the pound key.", voice=app.config['TWILIO_VOICE_SETTING'])
    resp.append(gather)
    return str(resp)

@app.route('/check-pin', methods=['GET', 'POST'])
def check_pin_route():
    '''
    If the Crew account is "protected" then we must direct to this endpoint for collection of the account Access Code.  
    Since the user may use either the Crew acccess code or their individual access code, we have a Crews func that will 
    gather up all possible codes and load them in a list. We just check the list to see if what the user input matches any 
    of the entries. Again, not super secure, this is just a best intentions effort to protect messages. 
    This endpoint contains a basic brute force protection which will only allow 4 attempts before ending the call.  
    '''
    resp = VoiceResponse()

    if not 'sessionCrewId' in session:
        return redirect(url_for('hangup_route'), code=307)
    else:
        crew = Crews.query.get(session['sessionCrewId'])
        codes_list = crew.gather_access_codes()
    
    if 'Digits' in request.values:
        # basic pin brute force protection that limits tries to 4
        if 'access_code_tries' in session and session['access_code_tries'] == 5:
            return redirect(url_for('hangup_route'), code=307)
        
        provided_code = str(request.values['Digits'])
        if provided_code in codes_list:
            # all is good, send to the menu
            return redirect(url_for('main_menu_route'), code=307)
        else:
            if not 'access_code_tries' in session:
                session['access_code_tries'] = 1
            else:
                session['access_code_tries'] += 1
            gather = Gather(action=app.config['APP_BASE_URL'] + url_for('check_pin_route'), method='POST', input="dtmf", timeout=3, finishOnKey='#')
            gather.say(f"Your input was not correct. Please input your access code and then press the pound key.", voice=app.config['TWILIO_VOICE_SETTING'])
            resp.append(gather)
            return str(resp)

    gather = Gather(action=app.config['APP_BASE_URL'] + url_for('check_pin_route'), method='POST', input="dtmf", timeout=3, finishOnKey='#')
    gather.say("This account is protected. Please enter the access code, followed by the pound sign.", voice=app.config['TWILIO_VOICE_SETTING'])
    resp.append(gather)
    return str(resp)

@app.route('/main-menu', methods=['GET', 'POST'])
def main_menu_route():
    '''
    The primary route for our Twilio voice menu. 
    Hitting this route with no request params means we are starting fresh with a new call. 
    At this stage we should provide a Message count and offer to play Messages or record a new Message. 

    We will use 1 to listen to Messages and 2 to record a Message. 
    The presence of 'Digits' in our request vars will indicate which route we will redirect to: 
    1 - redirect to the 'play_route'
    2 - redirect to the 'record_route' 
    '''
    message_count = 0
    session['messages'] = None
    # at this point sessionCrew should be set, if not, kill
    if session['sessionCrewId'] is None:
        return redirect(url_for('hangup_route'), code=307)
    else:
        crew = Crews.query.get(session['sessionCrewId'])
        # need to adjust this to exclude 'deleted' status messages
        message_count = Messages.query.filter_by(crew_id=crew.id).count()
        # grab all Messages and put them in the session
        # we will do this every time as this can change each time the user hits this endpoint
        messages = Messages.query.filter_by(crew_id=session['sessionCrewId']).order_by(Messages.created.desc()).all()
        session['messages'] = Messages.make_ordered_list(messages)
    resp = VoiceResponse()

    # if the request contains 'Digits' we know this is the result of a Gather and must check for the account pin
    if 'Digits' in request.values:
        choice = str(request.values['Digits'])
        if choice == '1':
            # user wants to listen, redirect to play route
            return redirect(url_for('play_route'), code=307)
        elif choice == '2':
            # user wants to record, redirect to record route
            return redirect(url_for('record_route'), code=307)
        elif choice == '3':
            # catching a return to main menu
            pass
        else:
            # invalid choice, try again
            gather = Gather(action=app.config['APP_BASE_URL'] + url_for('main_menu_route'), method='POST', input="dtmf", num_digits=1, timeout=4)
            gather.say(f"That was not a valid selection. To listen to messages, press 1. To record a message, press 2.", voice=app.config['TWILIO_VOICE_SETTING'])
            resp.append(gather)
            return str(resp)

    # this block will be run during the very first POST to this route, signaling a new incoming call
    gather = Gather(action=app.config['APP_BASE_URL'] + url_for('main_menu_route'), method='POST', input="dtmf", num_digits=1, timeout=3, finishOnKey='#')
    gather.say(f"Main menu. You have {message_count} messages. To listen to messages, press 1. To record a message, press 2. If you are finished, you may hang up.", voice=app.config['TWILIO_VOICE_SETTING'])
    resp.append(gather)
    return str(resp)

@app.route('/record', methods=['GET', 'POST'])
def record_route():
    '''
    The route responsible for handling recording a new Message. 
    From a fresh state we simply prompt a Record action. 

    If the 'RecordingSid' and 'RecordingUrl' and 'RecordingStatus' vars are present, we are returning to this 
    menu directly after recording a Message (so handle creating a new Message).
    After the new Message has been created and committed, we then redirect back to the 'main_menu_route'
    '''
    resp = VoiceResponse()

    if 'RecordingSid' and 'RecordingUrl' in request.values:
        # we have a recording from Twilio, create a new Message and save it. Redirect to main menu.
        url = request.values['RecordingUrl']
        message = Messages(crew_id=session['sessionCrewId'], url=url)
        db.session.add(message)
        # if someone is recording messages, we can assume this is an active crew
        crew = Crews.query.get(session['sessionCrewId'])
        crew.status = 'active'
        db.session.add(crew)
        db.session.commit()
        return redirect(url_for('main_menu_route'), code=307)
    
    record = Record(action=app.config['APP_BASE_URL'] + url_for('record_route'), method='POST', maxLength=app.config['TWILIO_RECORDING_MAXLENGTH'], playBeep=True, timeout=3, finishOnKey='#')
    say = Say(f"Record your message after the beep. Press the pound key when you are finished.", voice=app.config['TWILIO_VOICE_SETTING'])
    resp.append(say)
    resp.append(record)
    return str(resp)

@app.route('/play', methods=['GET', 'POST'])
def play_route():
    '''
    This route is responsible for playing existing Messages. 
    We want to list Messages in reverse chronological order, so newest Message plays first. 
    As we will allow the user to skip through to the next Message at any time by hitting 1, we will want 
    to keep the Message list in a session; this list will contain the UUID of the Messages available. 
    Instead of trying to keep a cursor for our position in the list, we will pop off each Message as it is 
    played. This of course means we cannot go backwards in our list - we will just prompt the user to go back 
    to the main menu and start again.  
    '''
    resp = VoiceResponse()
    message_list = session['messages']
    if not message_list:
        # no messages to play, send back to main menu
        gather = Gather(action=app.config['APP_BASE_URL'] + url_for('main_menu_route'), method='POST', input="dtmf", num_digits=1, timeout=3)
        gather.say(f"There are no more messages. Press three to return to the main menu, or simply hang up.", voice=app.config['TWILIO_VOICE_SETTING'])
        resp.append(gather)
        return str(resp)
    if 'Digits' in request.values:
        """
        We really only need to look for a prompt for the main menu. 
        If the user wants to skip, this endpoint gets reloaded and the session will pop off 
        the next message automatically. 
        """
        choice = str(request.values['Digits'])
        if choice == '3':
            # user wants to go to main menu
            return redirect(url_for('main_menu_route'), code=307)
    
    message_list = session['messages']
    message_to_play = message_list.pop(0)

    gather = Gather(action=app.config['APP_BASE_URL'] + url_for('play_route'), method='POST', input="dtmf", num_digits=1)
    gather.say(f"Playing message. To skip to the next message, press 1. To go back to the main menu, press 3", voice=app.config['TWILIO_VOICE_SETTING'])
    
    gather.play(f"{ message_to_play['url']}.mp3")
    resp.append(gather)
    return str(resp)

@app.route('/hangup', methods=['GET', 'POST'])
def hangup_route():
    '''
    We don't need a hangup route, but having one would be nice so we can clean up 
    the sessions and end the call properly.   
    '''
    session.clear()

    resp = VoiceResponse()
    hangup = Hangup()
    resp.append(hangup)
    return str(resp)

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

'''
TODO items

TODO - build out crew members dashboard
TODO - change crew status to active after any message activity
TODO - fix dashboard mobile nav
TODO - fix messages mobile nav
TODO - the JS location.assign after message del is losing the flash success message. 
TODO - crew invitation system 
'''