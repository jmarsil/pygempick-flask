#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Tue Feb 27 15:12:39 2018

@author: joseph

Outlines formatting of table in mysql database for flask web application.
db.Column allows us to create fields in the database.
We access these tables through a msql query command.
Save values to table through db.session.commit()

Every time the database is modified a you must perform a database migration.
(ie when you update models.py you must also implement database migration)

** Note - After change, run flask db migrate in terminal to update database columns.
** These values can then be accessed by routes.py and passed to tasks.py and .htmls
"""

from datetime import datetime
from app import db, login
from flask import current_app
from werkzeug.security import generate_password_hash as gen_hash, check_password_hash as check_hash
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
import os
import redis 
import rq
import json

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

followers = db.Table('followers',
                         db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                         db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
                         )

class User(UserMixin, db.Model):

    '''

    :var User.id - Id of user
    :var User.username - Username of user
    :var User.email - Email of user
    :var User.password_hash - encrypted user's password
    :var User.posts - relationship to posts table in database
         (ie. the way to link a blog post to the user that authored it
         is to add a reference to the user's ID. This shows a one-to-many
         relationship since one user writes MANY posts)
    :var User.zips - relationship to Process table in database
    :var User.params - relationship to paramas table where all processing parameters
                       are saved for each task run. (from single_pick.html)
    :var User.tasks - relationships to tasks table where task summaries will be saved
    :var User.notifications - Table for user notifications (will show under navbar)
    :var User.about_me - Saves User's Bio
    :var User.last_seen - Saves User's most recent logon time

    '''

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique = True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    zips = db.relationship('Process', backref='author', lazy='dynamic' )
    params = db.relationship('Paramas', backref='author', lazy='dynamic' )
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user',lazy='dynamic')
    recent_searchs = db.Column(db.String(140))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed=db.relationship(
            'User', secondary=followers,
            primaryjoin=(followers.c.follower_id == id),
            secondaryjoin=(followers.c.followed_id == id),
            backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    
    def __repr__(self):
        
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        '''
        :param password: password taken from register.html
        :return: Encrypted version of password
        '''
        self.password_hash = gen_hash(password)
    
    def check_password(self, password):
        '''
        :param password: password taken from login.html
        :return: True or False, if false not permitted to login to account.
        '''
        return check_hash(self.password_hash, password)
    
    def avatar(self, size):
        '''

        :param size: Size of user's profile image in pixels.
                     (**Note: for users with no avatar, identicon is generated)
        :return: url of user's avatar scaled to requested size in pixels

        '''

        digest=md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
                digest, size)
        
    def get_email(self):
        '''
        :return: lower case version of User's email.
        '''
        my_email = self.email.lower()
        return my_email
    
    def follow(self,user):
        '''
        :param user: Checks if current user following selected user id
        :return: appends user id to follow table if not already folowing
        '''
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self,user):
        '''
        :param user: if current user.id is following selected user.id
        :return: removed selected user.id from followed column of current user.id
        '''
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self,user):

        '''
        :param user: Current user.id
        :return: Count of every user current(user.id) is following
        '''

        return self.followed.filter(
                followers.c.followed_id == user.id).count() > 0
    

    def followed_posts(self):

        '''
        :return: filters for post of followers
                 (ie ranks most recent posts including their own)
        '''

        followed = Post.query.join(
                followers, (followers.c.followed_id == Post.user_id)).filter(
                        followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())
    
    def all_posts(self):
        '''
        :return: All posts saves in Post table (ie all users)
        '''
        own=Post.query.order_by(Post.timestamp.desc())
        return own
        
    def own_posts(self):
        '''
        :return: Selects all of user's posts. Ranked from current to less current.
        '''
        own = Post.query.filter_by(user_id=self.id)
        return own.order_by(Post.timestamp.desc())
    
    def own_params(self):
        '''
        :return: Returns a query of all the users saved parameters before processing uploaded .zip of IGEM images
        '''
        own = Paramas.query.filter_by(user_id=self.id)
        return own.order_by(Paramas.timestamp.desc())
    
    def own_zips(self):
        '''
        :return: All the most recent paths of saved .zips. Only valid after first task is completed
        '''
        own = Process.query.filter_by(user_id=self.id)
        return own.order_by(Process.timestamp.desc())
    
    def get_uploads(self):
        '''
        :return: returns all paths of uploaded .zips
                 (for processing in tasks.py, uploaded .zip file deleted when complete)
        '''
        zips = Process.query.filter_by(user_id=self.id)
        choice = zips.order_by(Process.timestamp.desc()).first()
        return choice.archive_filename
    
    def is_number(s):
        '''
        :return: Boolean iff a number. True or False
        '''
        
        try:
            float(s)
            return True
        
        except ValueError:
            return False
    
    def launch_task(self, name, desciption, *args, **kwargs):
        '''
        :param name: Task name
        :param desciption: Task description
        :param args:
        :param kwargs:
        :return:
        '''
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, user=self)
        db.session.add(task)
    
    def get_tasks_in_progress(self):
        '''
        :return: Returns current tasks in progress
        '''
        return Task.query.filter_by(user=self, complete=False).all()
    
    def get_task_in_progress(self, name):
        '''
        :param name: Name of a specific, unfinished task.
        :return: Returns the task in progress filtered out by its name.
        '''
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()
    
    def get_completed_tasks(self):
        '''
        :return: Returns list of completed tasks.
        '''
        return Task.query.filter_by(user=self, complete=True).all()
    
    def add_notification(self, name, data):
        '''
        :param name: Notification id/name
        :param data: Notification description
        :return: new notification
        '''
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
                {'reset_password': self.id, 'exp': time() + expires_in},
                current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
        
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        
        except:
            return
        
        return User.query.get(id)


    
class Post(db.Model):
    '''
    Post class represents blog post written by users.
    Can be written from User's home page profile, user.html

    :var Post.id - post identifier
    :var timestamp - allows posts to be retrieved in chronological order
    :var user_id - db.relationship with current_user.id
    :image_filename - iff image uploaded, the name of the filename is saved.
    :image_url - iff image uploaded, the image path saved as a string.

    '''
    
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) #references id from user's tabel
    image_filename = db.Column(db.String(140), default=None, nullable=True)
    image_url = db.Column(db.String(256), default=None, nullable=True)
    def __repr__(self):
        return'<Post {}>'.format(self.body)

class Process(db.Model):

    '''
    Saved through form submission from pygempick.html

    :var Process.id - process identifier
    :var Process.timestamp - allows processes' (or tasks) to be retrieved in chronological order
    :var Process.user_id - db.relationship to current_user.id
    :var Process.archive_filename - Saves a string to path of uploaded .zip
    :var Process.img_state - True or False. Are images in uploaded .zip compressed?
    '''
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    archive_filename = db.Column(db.String(140), default=None, nullable=True)
    archive_url = db.Column(db.String(140), default=None, nullable=True)
    img_state = db.Column(db.Boolean, unique=False, default=True)
    
    def __repr__(self):
        return '<{} Sized Zip File!>'.format(os.stat(self.archive_url).st_size)


class Paramas(db.Model):

    '''

    Saved through followup form submission of single_pick.html

    :var Paramas.id - paramater set identifier
    :var Paramas.timestamp - allows paramater set(s) to be retrieved in chronological order
    :var Paramas.user_id - - db.relationship to current_user.id

    :var Paramas.anchor1: The anchor filter value for HCLAP filter (High Contrast Laplacian Filtering)
    :var Paramas.anchor2: The anchor filter value for HLOG filter (High-Contrast Laplace of Gaussian)
    :var Paramas.minArea: Minimum area threshold of detected gold particle (px^2)
    :var Paramas.minCirc: Circularity threshold, .78 is a square...
    :var Paramas.minConc: Concavity threshold allows us to filter out detected particles with 'gaps' in the volume.
    :var Paramas.minIner: Inertial ratio threshold, filters out elongated particles.

    '''
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    anchor1 = db.Column(db.String(4), default=None, nullable=True)
    anchor2 = db.Column(db.String(4), default=None, nullable=True)
    minArea = db.Column(db.String(4), default=None, nullable=True)
    minCirc = db.Column(db.String(4), default=None, nullable=True)
    minConc = db.Column(db.String(4), default=None, nullable=True)
    minIner = db.Column(db.String(4), default=None, nullable=True)
    comments = db.Column(db.String(140), default=None, nullable=True)
    
    def __repr__(self):
        return '<Processing ZIP {}!>'.format(self.timestamp)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)
    
    def get_data(self):
        return json.loads(str(self.payload_json))
    
class Task(db.Model):

    '''
    Values saved & updated in tasks.py

    An interesting difference between this db.model and the previous ones is that the id primary
    key field is a string, not an integer. This is because for this model, I’m not going to rely on
    the database’s own primary key generation and instead I’m going to use the job identifiers
    generated by RQ.

    :var Task.id - unique identifier for each task
    :var Task.name - unique name for each task (PubMed search or Image Processing?)
    :var Task.description - unique description for each task
         (Saves the summary of the results from each backround task)
    :var Task.complete - if Fasle task is in_progress.
    :var Task.csv_key - String of path to saved .csv of (x,y) keypoints from detected
         particles from most recent processed/uploaded Process.archive_filename
    :var Task.csv_sum - String of path to saved .csv of summary of particle counts per image.
    :var Task.zip_name - String of path to saved .zip of processe/compressed/picked images
    :var img_count - String of "total X particles counted in M images with N duplicates"

    '''

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(140), index=True)
    description = db.Column(db.String(140))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)
    csv_key = db.Column(db.String(254), default=None, nullable=True)
    csv_sum = db.Column(db.String(254), default=None, nullable=True)
    zip_name = db.Column(db.String(254), default=None, nullable=True)
    img_count = db.Column(db.String(140), default=None, nullable=True)
    
    def get_rq_job(self):
        
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job
    
    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('Picker Progress:', 0) if job is not None else 100