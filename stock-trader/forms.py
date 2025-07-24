from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class TradeForm(FlaskForm):
    symbol = SelectField('Symbol', validators=[DataRequired()])
    trade_type = SelectField('Trade Type', choices=[('Buy', 'Buy'), ('Sell', 'Sell')], validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=1000000)])
    submit = SubmitField('Submit Trade')
