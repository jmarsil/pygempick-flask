#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 23 10:40:54 2018

@author: joseph

Can edit this function for my purposes - send email when job is complete...
"""

from flask_mail import Message
from flask import current_app
from app import mail
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body,
               attachments=None, sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    
    else:
        Thread(target=send_async_email, 
               args=(current_app._get_current_object(), msg)).start()
