from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, DateField, DateTimeLocalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, Email

class CandidateForm(FlaskForm):
    name = StringField("氏名", validators=[DataRequired()])
    email = StringField("Email", validators=[Optional(), Email()])
    birthdate = DateField("生年月日", format="%Y-%m-%d", validators=[Optional()])
    applied_at = DateTimeLocalField("応募日", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    school = StringField("学校")
    grad_year = IntegerField("卒年", validators=[Optional()])
    qualifications = TextAreaField("資格", render_kw={"rows":3})
    skills = TextAreaField("スキルセット", render_kw={"rows":3})
    languages = TextAreaField("語学", render_kw={"rows":3})

class ApplicationStageForm(FlaskForm):
    stage = SelectField(
        "選考ステップ",
        choices=[("document","①書類選考"),("first","②一次面接"),
                 ("second","③二次面接"),("final","④最終面接")],
    )
    status = SelectField(
        "状態",
        choices=[("screening","選考中"),("offered","内定"),("rejected","不採用"),("hired","入社")],
    )
    submit = SubmitField("更新")