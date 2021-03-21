from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectMultipleField, DecimalField, IntegerField
from wtforms.validators import InputRequired, Length, NumberRange


class InputData(FlaskForm):
    pid = DecimalField('Patient ID', validators=[
                       InputRequired(), NumberRange(max=9999999999)])
    fname = StringField('First name', validators=[InputRequired(), ])
    lname = StringField('Last name', validators=[InputRequired()])
    age = IntegerField('Age(In years)', validators=[
                       InputRequired(), NumberRange(min=0, max=200)])
    spo2 = DecimalField('SP O2', validators=[
                        InputRequired(), NumberRange(max=100)])
    submit = SubmitField('Add')
