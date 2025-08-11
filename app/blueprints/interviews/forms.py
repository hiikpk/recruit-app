from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeLocalField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileField

class InterviewForm(FlaskForm):
    candidate_id = StringField("候補者ID", validators=[DataRequired()])
    scheduled_start = DateTimeLocalField("日時", format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    location = StringField("場所")
    meeting_url = StringField("URL")
    file = FileField("録音ファイル", validators=[Optional()])
    step = SelectField("選考ステップ", choices=[("document","書類選考"),("first","一次面接"),("second","二次面接"),("final","最終面接")])
    rank = SelectField("ランク", choices=[("","—"),("S","S"),("A","A"),("B","B"),("C","C")])
    decision = SelectField("合否", choices=[("","—"),("pass","合格"),("fail","不合格"),("pending","保留")])
    comment = TextAreaField("評価コメント", render_kw={"rows":3})
    interviewer = StringField("選考実施担当者")
    submit = SubmitField("作成")