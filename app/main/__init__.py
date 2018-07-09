#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  5 17:10:38 2018

@author: joseph
"""

from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes