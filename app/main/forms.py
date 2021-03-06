# -*- coding:utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, FileField, PasswordField#, FileAllowed, FileRequired
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User


class CryptoForm(FlaskForm):
    password=StringField('Input a password', validators=[Required(),
            Length(1,64)])
    submit=SubmitField('Confirm')

class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')

class HomeworkForm(FlaskForm):
    project=FileField('HomeWork',validators=[Required()])
# FileAllowed(['.zip','.rar','.7z'],"Compressed files only")])
    times=SelectField('project_order',choices=[('2','2'),('1_late','1'),('3','3')])
    submit = SubmitField("Submit")

class EditProfileForm(FlaskForm):
    phone = StringField('phone', validators=[Length(11)])
    about_me = TextAreaField('about me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[Required(), Length(1, 64)])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    location = StringField('Province', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[Required()])
    submit = SubmitField('Submit')


class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[Required()])
    submit = SubmitField('Submit')
