#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 15:12:39 2018

@author: joseph
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
    
    #db.Column allows you to create fields in your database which you can reapply
    # to templates...
    
    #everytime the database is modified a you must perform a database migration...
    # then you can add these feilds to the html template(s) of your chouice
    
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique = True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    zips = db.relationship('Process', backref='author', lazy='dynamic' )
    params = db.relationship('Paramas', backref='author', lazy='dynamic' )
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user',lazy='dynamic')
    recent_searchs =db.Column(db.String(140))
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
        self.password_hash = gen_hash(password)
    
    def check_password(self, password):
        return check_hash(self.password_hash, password)
    
    def avatar(self, size): 
        
        #returns url of user's avatar scaled to requested size in pixels
        #for users with no avatar, identicon is generated...
        
        digest=md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
                digest, size)
        
    def get_email(self):
        my_email = self.email.lower()
        return my_email
    
    def follow(self,user):
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self,user):
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self,user):
        return self.followed.filter(
                followers.c.followed_id == user.id).count() > 0
    
    #filters for post of followers
    #filters for their most recent posts
    #combines them
    def followed_posts(self):
        followed = Post.query.join(
                followers, (followers.c.followed_id == Post.user_id)).filter(
                        followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())
    
    def all_posts(self):
        own=Post.query.order_by(Post.timestamp.desc())
        return own
        
    def own_posts(self):
        own = Post.query.filter_by(user_id=self.id)
        return own.order_by(Post.timestamp.desc())
    
    def own_params(self):
        own = Paramas.query.filter_by(user_id=self.id)
        return own.order_by(Paramas.timestamp.desc())
    
    def own_zips(self):
        own = Process.query.filter_by(user_id=self.id)
        return own.order_by(Process.timestamp.desc())
    
    def get_uploads(self):
        zips = Process.query.filter_by(user_id=self.id)
        choice = zips.order_by(Process.timestamp.desc()).first()
        return choice.archive_filename
    
    def is_number(s):
        
        try:
            float(s)
            return True
        
        except ValueError:
            return False
    
    def launch_task(self, name, desciption, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, user=self)
        db.session.add(task)
    
    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()
    
    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()
    
    def get_completed_tasks(self):
        return Task.query.filter_by(user=self, complete=True).all()
    
    def add_notification(self, name, data):
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
    
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) #references id from user's tabel
    image_filename = db.Column(db.String(140), default=None, nullable=True)
    image_url = db.Column(db.String(256), default=None, nullable=True)
    def __repr__(self):
        return'<Post {}>'.format(self.body)

class Process(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    archive_filename = db.Column(db.String(140), default=None, nullable=True)
    archive_url = db.Column(db.String(140), default=None, nullable=True)
    img_state = db.Column(db.Boolean, unique=False, default=True)
    
    def __repr__(self):
        return '<{} Sized Zip File!>'.format(os.stat(self.archive_url).st_size)


class Paramas(db.Model):
    
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
    
    id = db.Column(db.String(36), primary_key=True)
    '''
    An interesting difference between this model and the previous ones is that the id primary
    key field is a string, not an integer. This is because for this model, I’m not going to rely on
    the database’s own primary key generation and instead I’m going to use the job identifiers
    generated by RQ.
    '''
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
 
#as the database grows the structure must change, Alembic in Flask-Migrate will
## make these schema easier

#the way to link a blog post to the user that authoured it is to add a reference to the user's ID..
##one-to-many relationship since one user writes many posts...
        
## Post class represents blog post written by users...
##timestamp field is indexed which is useful if posts are to be retrieved in chronological order

##when update models.py you must also implement database migration...
