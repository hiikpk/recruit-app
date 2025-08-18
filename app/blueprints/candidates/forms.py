from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, DateField, DateTimeLocalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, Email

class CandidateForm(FlaskForm):
    name = StringField("氏名", validators=[DataRequired()])
    name_yomi = StringField("氏名（ふりがな）")
    email = StringField("Email", validators=[Optional(), Email()])
    phonenumber = StringField("電話番号")
    birthdate = DateField("生年月日", format="%Y-%m-%d", validators=[Optional()])
    applied_at = DateField("応募日", format="%Y-%m-%d", validators=[Optional()])
    school = StringField("学校")
    grad_year = IntegerField("卒年", validators=[Optional()])
    applying_position = StringField("選考ポジション")
    nationality = StringField("国籍")
    current_job = StringField("現職")
    resume_file_id = StringField("履歴書ファイルID")  # ファイルアップロードは別途実装
    status = SelectField("選考ステータス", choices=[("applied","新着応募"),("screening","選考中"),("offer","内定"),("hired","入社"),("rejected","不採用"),("withdrawn","辞退")], default="applied")
    # offer_date = DateField("オファー日", format="%Y-%m-%d", validators=[Optional()])
    # acceptance_date = DateField("内定承諾日", format="%Y-%m-%d", validators=[Optional()])
    # join_date = DateField("入社日", format="%Y-%m-%d", validators=[Optional()])
    # decline_date = DateField("辞退日", format="%Y-%m-%d", validators=[Optional()])
    channel = StringField("応募チャネル")
    channel_detail = StringField("チャネル詳細")
    qualifications = TextAreaField("資格", render_kw={"rows":3})
    skills = TextAreaField("スキルセット", render_kw={"rows":3})
    languages = TextAreaField("語学", render_kw={"rows":3})
    memo = TextAreaField("メモ", render_kw={"rows":3})

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