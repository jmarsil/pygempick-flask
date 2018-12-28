#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 16:55:34 2018

@author: joseph
"""
from dotenv import load_dotenv
import os

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):

    '''
    Configuration class for pygempick web application.

    '''
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

    #allows you to deploy web app on linux based cloud server
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #'mysql+pymysql://jmarsil:Revl*2018@localhost/pypick'

    # use the following code below to deploy on a virtual server on mac/linux...
    # 'sqlite:///' + os.path.join(basedir, 'app.db')

    '''
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/db_name'
    https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/miguelgrinberg/microblog/tree/v0.22/deployment
    https://stackoverflow.com/questions/27766794/switching-from-sqlite-to-mysql-with-flask-sqlalchemy
    '''
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    POSTS_PER_PAGE = 25
    DOWNLOADS_PER_PAGE = 10

    # sets Mail server settings of web application
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['joe@seoprophets.com']
    
    LANGUAGES = ['en', 'en-CA', 'fr']

    # sets the redis task manager for task processing
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
