from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, ValidationError, Length, Regexp, Optional
import re

def code_check(form, field):
    """Enforce proper access code entry.
    6 numerical digits, nothing more and nothing less.   
    """
    good_code = re.search(r'^\d{6}$', field.data, flags=re.IGNORECASE)
    if not good_code:
        raise ValidationError("The Access Code must be 6 numerical digits.")

class CrewSettings(FlaskForm):
    name = StringField('Crew Name (optional)', validators=[])
    access_code = StringField('Access Code', validators=[code_check, Optional()])
    submit = SubmitField('Save')

class CrewDelete(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Delete Account')