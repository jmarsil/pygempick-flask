#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 16:34:10 2018

@author: joseph
"""

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User
import numpy as np
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app import photos, archives, db

##for most forms build a template form in html which you can render in another template...


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About Me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')
    
    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
    
    def validate_username(self,username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')

class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[
            DataRequired(), Length(min=1, max=360)])
    photo = FileField('Upload an Image', validators=[FileRequired(), FileAllowed(photos, 'Images only!')])
    submit = SubmitField('Submit')

class PubmedForm(FlaskForm):
    search = TextAreaField('Search for articles on pubmed..', validators=[
            DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')

class ZipForm(FlaskForm):
    
    archive = FileField('Upload an Zip Folder with TEM Images!', validators=[FileRequired(), FileAllowed(archives, 'Archives only!')])
    choice1 = BooleanField('Previously Compressed (jpg)?')
    submit = SubmitField('Next Step...')        
    
class FilterParams(FlaskForm):
    
    anchor1 = StringField('Anchor (HCLAP)', validators=[DataRequired()], default="11")
    anchor2 = StringField('Anchor (HLOG)', validators=[DataRequired()],default="18")
    minArea = StringField('Minimum Area', validators=[DataRequired()], default="37") 
    minCirc = StringField('Minimum Circularity', validators=[DataRequired()], default="79") 
    minConc = StringField('Minimum Covexity ', validators=[DataRequired()], default="50") 
    minIner = StringField('Minimum Inertia Ratio', validators=[DataRequired()], default="50")
    comments =TextAreaField('Any comments?', validators=[
            DataRequired(), Length(min=1, max=540)])
    submit = SubmitField('Process Images...')

    def validate_anchor1(self, anchor1):
        valid = User.is_number(anchor1.data)
        if valid is not True:
            raise ValidationError('Please use a number.')
            
        if valid is True and float(anchor1.data) not in np.arange(6, 41,1):
            raise ValidationError('Choose a filter anchor(1) picking parameter between 6 <--> 40')
    
    def validate_anchor2(self, anchor2):
        valid = User.is_number(anchor2.data)
        if valid is not True:
            raise ValidationError('Please use a number.')
            
        if valid is True and float(anchor2.data) not in np.arange(6, 41,1):
            raise ValidationError('Choose a filter anchor(2) picking parameter between 6 <--> 40')
    
    def validate_minArea(self, minArea):
        valid = User.is_number(minArea.data)
        
        if valid is not True:
            raise ValidationError('Please use a number.')
        
        if valid is True and float(minArea.data) not in np.arange(10, 41,1):
            raise ValidationError('Choose a minArea picking parameter between 10 <--> 40')
    
    def validate_minCirc(self, minCirc):
        valid = User.is_number(minCirc.data)
        if float(minCirc.data) in np.arange(50, 99,1):
            valid = True
        if valid is not True:
            raise ValidationError('Please use a number.')
        if valid is True and float(minCirc.data) not in np.arange(50, 99,1):
            raise ValidationError('Choose a minConc picking parameter between .50 <--> .99')

    def validate_minConc(self, minConc):
        valid = User.is_number(minConc.data)
        if valid is not True:
            raise ValidationError('Please use a number.')
        if valid is True and float(minConc.data) not in np.arange(50, 99,1):
            raise ValidationError('Choose a minConc picking parameter between .50 <--> .99')

    def validate6(self, minIner): 
        valid = User.is_number(minIner.data)
        if valid is not True:
            raise ValidationError('Please use a number.')
        
        if valid is True and float(minIner.data) not in np.arange(.5, 1,.01):
            raise ValidationError('Choose a minConc picking parameter between .50 <--> .99')
