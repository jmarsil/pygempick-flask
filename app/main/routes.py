from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, send_from_directory
from app import db, photos, archives
from datetime import datetime
from flask_login import current_user, login_required
from app.main.forms import EditProfileForm, PostForm, ZipForm, FilterParams, PubmedForm
from app.models import User, Post, Paramas, Process, Notification, Task
from app.main import bp
from Bio import Entrez
import time
import pandas as pd
from plotly.offline import plot
import plotly.graph_objs as go
import jinja2 as j2
import numpy as np
import os

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        filename = photos.save(request.files['photo'])
        url = photos.url(filename)
        
        post = Post(body=form.post.data, author=current_user, image_filename=filename,\
                    image_url=url )
        
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    posts = current_user.all_posts().paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    
    parameters = current_user.own_params()
    tasks = Task.query.all()
    my_tasks = current_user.get_completed_tasks()
        
    imgs_count = 0
    
    if len(tasks)==0:
        imgs_count = 0
    else:
        for task in tasks:
            imgs_count += np.float(task.img_count)
            
    return render_template('index.html', title='Home Page', form=form, posts=posts.items,\
                           imgs_count=imgs_count, my_tasks=my_tasks, params=parameters,\
                           length=range(len(my_tasks[-2:])), next_url=next_url, prev_url=prev_url)

@bp.route('/pygempick/download-files', methods=['GET', 'POST'])
@login_required
def download():
    
    tasks = current_user.get_completed_tasks()
    a = list(reversed(tasks))
    parameters = current_user.own_params()
    
    if len(tasks)==0:
        return redirect(url_for('main.pygempick'))
    
    return render_template('download.html', title='Download Picked Image Data',\
                           tasks=a, parameters=parameters, length=range(len(tasks)))

@bp.route('/pygempick/download-files/<filename>', methods=['GET', 'POST'])
@login_required
def complete_download(filename):
    
    root_dir = os.path.dirname(os.getcwd())
    directory= os.path.join(root_dir,'pygempick-flask','static','to-download')
    print(root_dir)
    return send_from_directory(directory=directory, filename=filename,\
                               as_attachment=True)

@bp.route('/pygempick/graphing/<filename>', methods=['GET', 'POST'])
@login_required
def graph_total(filename):
    
    data = pd.read_csv('static/to-download/{}'.format(filename),\
                    header=None, skiprows=1,skipfooter=1, engine='python')
    xdata = data[1].tolist() #image number
    ydata = data[0].tolist() #gold particle count
    total = sum(ydata)
    my_plot_div = plot({
            "data":[go.Scatter(x=xdata, y=ydata)],
            "layout": go.Layout( title= 'Total Particle Count',
                                          hovermode= 'closest',
                                          xaxis= dict(title= 'Archive Image Number',
                                                      ticklen= 5,
                                                      zeroline= False,
                                                      gridwidth= 2,), 
                                          yaxis=dict(title= 'Gold Particles Detected',
                                                     ticklen= 5,
                                                     gridwidth= 2,),
                                                     showlegend= False)},
                        output_type='div')
                                          
    return render_template('graphing.html', div_placeholder=j2.Markup(my_plot_div), total=total)

'''

The above two routes - take the completed tasks from the user, and pushes the
filename of the selected saved output to the complete download route bellow!

https://stackoverflow.com/questions/24577349/flask-download-a-file

'''
    

@bp.route('/explore-pubmed', methods=['GET', 'POST'])
@login_required
def pubmed_search():
    form = PubmedForm()
    
    if request.method == "POST":
        current_user.recent_searchs = form.search.data
        
        db.session.commit()
        
        query = request.form['search']
        return redirect(url_for('main.pubmed_results', query=query, self=current_user.username))
    
    with open("static/to-download/pubmed_queries.txt") as f:
            values = f.readlines()
    
    with open("static/to-download/pubmed_abstracts.txt") as r:
            abstracts = r.readlines()
    
    return render_template('pubmed.html', title='Pubmed Search', values=values, abstracts=abstracts, lengths=range(len(values)), form=form)

@bp.route('/explore-pubmed/results?query=<query>', methods=['GET', 'POST'])
@login_required
def pubmed_results(query):
    
    if current_user.get_task_in_progress('article_search'):
        flash('A pubmed search is already under way!')
    
    else:
        current_user.launch_task('article_search', 'Pubmed Searcher Activated...')
    
    time.sleep(4)
    
    return redirect(url_for('main.pubmed_search', username=current_user.username))

@bp.route('/pygempick', methods=['GET','POST'])
@login_required
def pygempick():
    
    form = ZipForm()
    
    if form.validate_on_submit():
        filename = archives.save(request.files['archive'])
        url = archives.url(filename)
        Zip = Process(author=current_user, archive_filename=filename, archive_url=url,
                      img_state=form.choice1.data)
        db.session.add(Zip)
        db.session.commit()
        
        if request.method == "POST":
            #is_checked = request.form.get('hclap')
            #is_true = request.form.get('hlog')
            #if is_checked == is_true:
                
            return redirect(url_for('main.double_picker'))
            
            #elif is_checked == True and is_true == False:
             #   method = 'hclap'
              #  return redirect(url_for('single_picker', method = method))
            
           # elif is_checked == False and is_true == True:
            #    method = 'hlog'
             #   return redirect(url_for('single_picker', method = method))
            
            #else:
             #   return redirect(url_for('single_picker'))
        
        
        
    return render_template('pygempick.html', title='pyGemPick 1.1.3', form=form )

   
@bp.route('/pygempick/double-picker/', methods=['GET','POST'])
@login_required
def double_picker():
    
    form = FilterParams()
    if form.validate_on_submit():
        
        #Check parameters - make sure they're all numbers. 
        
        params = Paramas(author=current_user, anchor1=float(form.anchor1.data), \
                         anchor2=float(form.anchor2.data), minArea=float(form.minArea.data),\
                         minCirc=float(form.minCirc.data), minConc=float(form.minConc.data),\
                         minIner=float(form.minIner.data),  comments=form.comments.data)
        
        db.session.add(params)
        db.session.commit()
        
        flash('Particle Picker Activated!')
        
        if request.method == "POST":
            return redirect(url_for('main.picking_main'))
    
    return render_template('single_pick.html', title='pyGemPick - Dual Picker', form=form )

@bp.route('/pygempick/double_picker/picking_main')
@login_required
def picking_main():
    
    if current_user.get_task_in_progress('picking_main'):
        flash('A particle picking operation is already underway!')
    
    else:
        current_user.launch_task('picking_main', 'Particle Picking Activated...')
        db.session.commit()
    
    return redirect(url_for('main.pygempick', username=current_user.username))

@bp.route('/user/<username>') #has a dynamic component in it 
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = current_user.followed_posts().all()
    
    return render_template('user.html', user=user, posts=posts)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form=EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('main.user', username=username))

@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('main.user', username=username))


@bp.route('/notifications')
@login_required
def notifications():
    
    since = request.args.get('since',0.0, type=float)
    notifications = current_user.notifications.filter(
            Notification.timestamp > since).order_by(Notification.timestamp.asc())
    
    return jsonify([{
            'name':n.name,
            'data':n.get_data(),
            'timestamp':n.timestamp
            } for n in notifications])
