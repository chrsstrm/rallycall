Rally Call
====    

Author: chris.sturm@gmail.com    
December 2020    

Rally Call is designed to be the absolute most basic fallback communication system in the event of an emergency and you or your family and friends are not able to use their cell phones to keep in contact.    

If you didn't have the ability to call someone in an emergency, how would you communicate with your loved ones? With no cell service (network down, no battery, lost/damaged phone, etc.) and no access to a trusted computer for email/messaging, your communication options are severely limited. With a little bit of preparation ahead of any emergency, Rally Call is a central repository of voice memos that can be listened to or created by members of your Crew. Think of it like an old-school message service or group voicemail box.    

A Crew Admin registers for the service and receives an Account PIN code - this is your "mailbox" identifier. Any person who calls the Rally Call main number and enters the Account PIN code will be able to listen to and create voice messages. Give the Account PIN code to anyone that you may want to keep in touch with in the event of an emergency. You can further protect your Crew's messages with an Access Code; think of it like the PIN on your ATM card. You can use a shared Access Code for all members of your Crew, or each Crew member can create their own personal Access Code (requires member registration).    

Since the only requirement to leave or listen to messages on the Rally Call service is a touch-tone phone, Crew members can call from their cell phone, a land line, a pay phone, or even a borrowed cell phone - literally any phone will work. Listen to all messages (in reverse chronological order) from other Crew members or leave your own - "Hi, this is Tom. I'm safe. I made it to a friend's house and will stay here until I hear from you" etc. Keep in touch by running all your emergency communications through one central pivot point, a rally point if you will - use Rally Call.        


FAQs    
====    
**Do all Crew members need to register on the site?**    
No, only one Crew Member (the Crew Admin) must register. The Crew account can be protected with a shared account Access Code. If Crew members wish to use a personal Access Code, then they must be invited to the Crew by a Crew Admin, and must complete their account registration online.    

**Are the voice memos encrypted?**    
No, messages are not stored in an encrypted state. This is not an encrypted message service and should not be treated as such. If enabled, a Crew account Access Code provides minimal protection of messages, but is not meant to be secure.    

**Can I choose my Crew's Account PIN (account identifier)?**    
No, the Account PIN is randomly assigned when the Crew is created.    

**Is this service only for use in emergencies?**    
No, Rally Call can be used in any scenario that makes sense. It was designed as a communications fallback in the event of an emergency, but other potential uses are limitless.    


Development
====    

This application is built on:    
- Python
- Flask
- PostgreSQL
- SQLAlchemy
- Twilio    

**A Twilio account is required. You may register and test this system without providing a payment method but buying an inbound number, inbound minutes, and recording minutes are paid features outside of your inital trial period.**    

Local development of this application requires an HTTPS URL which is reachable by Twilio - for this we recommend [ngrok](https:ngrok.com).    
When developing locally be sure to change the environment var `APP_BASE_URL` to your tunnel URL.    

ENV Vars    
====    

This project requires several env vars, including:    

```
FLASK_APP=rallycall.py
FLASK_ENV=
DATABASE_URL=
SECURITY_PASSWORD_SALT = 
BOOTSTRAP_ADMIN_PASS = 
BOOTSTRAP_ADMIN_EMAIL = 
APP_BASE_URL = 
APP_NAME = "Rally Call"
CREW_ACCOUNT_PIN_LENGTH = 6
TWILIO_VOICE_SETTING = 'Polly.Matthew'
TWILIO_RECORDING_MAXLENGTH = 300
TWILIO_INBOUND_NUMBER = 
TWILIO_ACCOUNT_SID = 
TWILIO_AUTH_TOKEN = 
```    

`FLASK_ENV` can be 'development' or 'production'    

`DATABASE_URL` should be the str for your PostgreSQL connection    

`SECURITY_PASSWORD_SALT` choose any sufficiently complex string to seed the SALT    

`BOOTSTRAP_ADMIN_PASS` the inital admin user password string    

`BOOTSTRAP_ADMIN_EMAIL` admin user email for login    

`APP_BASE_URL` the FQD domain URL for the app, no trailing slash    

`TWILIO_INBOUND_NUMBER` the Twilio inbound number in +12223334455 format (E.164)    

`TWILIO_ACCOUNT_SID` the Twilio account Identifier    

`FTWILIO_AUTH_TOKEN` Twilio API auth token    

