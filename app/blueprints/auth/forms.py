from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class SignupForm(FlaskForm):
    org_name = StringField("企業名", validators=[DataRequired(), Length(max=120)])
    email = StringField("管理者メール", validators=[DataRequired(), Email()])
    password = PasswordField("パスワード", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("パスワード(確認)", validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("管理者を作成")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")