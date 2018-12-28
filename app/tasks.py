#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 29 09:58:58 2018

@author: joseph
"""
from flask import render_template
import sys
import os
from app import create_app
from app.email import send_email
#from app.email import send_email
import pygempick.core as py
from rq import get_current_job
from Bio import Entrez
from PIL import Image
import numpy as np
import pandas as pd
import cv2
import zipfile
import glob
#import time

from app.models import Task, User
from app import db

'''
First task to run is the image compression
Second task to run is the filtering - can do this all at one shot...

Use values the user just inputted in the database (ie most recent variables) in calculation.
We don't have to save them all! task can perform in the background and will send email when complete!
(see 22.2.2.4 in microblog - miguel flask pdf)

Images var obtained from a glob.glob command this is from the most recent archive uploaded static/arch
file location can be accessed from database images is an archive file in zip format...

Process of particle picking 

1. Get the most recent archive file location by timestamp.
2. Input that file into this function...
3. Get the most recent parameters from this user from the database...
4. Once task is created >> automatically save folder information to process
   (ie bin folder loc , picked folder loc, data folder loc ect.)
5. When complete, export those three folders into one final zip that will be 
   linked on Downloads page of user in routes.py

'''

app = create_app()
app.app_context().push()

def record_kp(i, keypoints, data):
    '''
    :param i: Index of selected image from uploaded .zip
    :param keypoints: This is the tuple of keypoints. See pygempick.core.pick
    :param data: Data is the dataframe where the outputted (x,y) coordinates will be concatenated to.
                 (Note: Can Be empty).
    :return: Returns the concatenated dataframe with two new rows that contain the (x,y) coordinates
             of the new coordinates the number of keypoints that were detected.
    '''
    if len(keypoints) > 0:
        #append x and y coordinates of keypoint center pixels
        #make sure that recording still occurs iff no keypoints detected!
        n = len(keypoints) #number of particles in image
        x = np.zeros(n)
        y = np.zeros(n)
            
        k = 0 #k is the keypoint counter 
        
        print(n)
        
        for keypoint in keypoints:
    ## save the x and y coordinates to a new array...
    
            x[k] = np.float(keypoint.pt[0])
            y[k] = np.float(keypoint.pt[1])
                            
            k+=1

        df = pd.DataFrame({'{}-x'.format(i): x, '{}-y'.format(i) : y})
        data = pd.concat([data,df], ignore_index=False, axis=1)
        return data, k
    
    else:
        return data, 0


def picking_main(user_id):

    '''
    :param user_id: This is the database ID of the user. Taken from routes.py
    :return: 1. path of saved .csv of keypoints summary
             2. list of path to saved .zip of processed images.

    :var anchor1: The anchor filter value for HCLAP filter (High Contrast Laplacian Filtering)
    :var anchor2: The anchor filter value for HLOG filter (High-Contrast Laplace of Gaussian)
    :var minArea: Minimum area threshold of detected gold particle (px^2)
    :var minCirc: Circularity threshold, .78 is a square...
    :var minConc: Concavity threshold allows us to filter out detected particles with 'gaps' in the volume.
    :var minIner: Inertial ratio threshold, filters out elongated particles.
    
    '''
    
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)

        # image counter
        i = 0
        # particle(s) detected counter
        j = 0
        dup = 0
        # make empty data frame to hold keypoints
        data = pd.DataFrame()
        
        #need the most recent uploaded archive
        ZIP = user.own_zips().first()
        #import archive name 
        archive_name = ZIP.archive_filename
        #import img_state (compressed or not!)
        img_state = ZIP.img_state
        #need the most recent recorded parameters of user!
        PARAM = user.own_params().first()
        
        anchor1 = np.float(PARAM.anchor1)
        anchor2 = np.float(PARAM.anchor2)
        minArea = np.float(PARAM.minArea)
        minCirc = np.float(PARAM.minCirc)/100
        minConc = np.float(PARAM.minConc)/100
        minIner = np.float(PARAM.minIner)/100
        comments = PARAM.comments
        
        file_path3 = os.path.join('static/to-download/','*.zip')
        zips = glob.glob(file_path3)
        num_zips = len(zips)
        
        #read the amount of .zip archives saved...
        file_path2 = os.path.join('static/to-download/','myzip_{}.zip'.format(num_zips))
        myzip = zipfile.ZipFile(file_path2, "w")
        
        #read the image file from most rescent archive location
        file_path1 = os.path.join('static/arch/','{}'.format(archive_name))
        with zipfile.ZipFile(file_path1) as images: 
        #read the archive images as namelist
            img_names = images.namelist()
        
            img_number = []
            part_count = []
            
            for image in img_names[1:]:
                with images.open(image) as tif:
                    imgdata=Image.open(tif).convert('RGB')
                
                cv_image = np.array(imgdata) 
                cv_image = cv_image[:, :, ::-1].copy() 
                #False = NOT compressed (images in .tiff format)
                if img_state == False:
                    r = 1018/cv_image.shape[1] ##correct aspect ratio of image to prevent distortion
                    dim = (1018, int(cv_image.shape[0]*r))
                    gray_img = cv2.resize(cv_image, dim, interpolation = cv2.INTER_AREA)
                else: 
                    gray_img=cv_image
                # gray_img = cv2.cvtColor(resized_img, cv2.COLOR_RGB2GRAY)
                # orig_img = cv2.imread(image) ##reads specific test file image
                # gray_img = py.compress(imgdata) #use pygempick to compress image...
        
                output1 = py.hclap_filt(int(anchor1), gray_img, 'no') #filter image
                output2 = py.hlog_filt(int(anchor2), gray_img, 'no')  #filter image
                
                # save the binary(s) to a memory foler >> static/bin/task_id
                # cv2.imwrite('!LOCATION!/<task_id>_hclap_<anchor1>_{}.jpg'.format(i),\ picked)
                # cv2.imwrite('!LOCATION!/<task_id>_hlog_<anchor2>_{}.jpg'.format(i),\ picked)
                
                keypoints1 = py.pick(output1, minArea, minCirc, minConc , minIner, 0) 
                keypoints2 = py.pick(output2, minArea, minCirc, minConc , minIner, 0)
                
                # filter the keypoints, remove duplicates
                keypoints1, dup1 = py.key_filt(keypoints1, keypoints2)
                
                #concatenate keypoints list from both methods
                keypoints = keypoints1 + keypoints2
                
                # Draws detected blobs using opencv's draw keypoints 
                picked = cv2.drawKeypoints(gray_img, keypoints, np.array([]), (0,255,0),\
                                     cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                
                cv2.imwrite(os.path.join(app.config['IMG_PICKED'], '{}.jpg'.format(tif)), picked)
                
                myzip.write('{}/{}.jpg'.format(app.config['IMG_PICKED'],i))
                
                # save the image with picked gold particles to memory folder 
                # >> static/picked/task_id
                #cv2.imwrite('!LOCATION!/<task_id>_picked_{}.jpg'.format(i),\ picked)
                
                data, k = record_kp(i,keypoints, data)

                dup += dup1
                # total particles counted
                j += k
                # total images
                i += 1
                #time.sleep(5)
                img_number.append(i)
                part_count.append(k)
                
                _set_description(i,j,dup)
                _set_task_progress(100 * i // len(img_names))
       
        part_count.append('Task Comments:')
        print(comments)
        img_number.append(comments)
        summary = pd.DataFrame({'Gold Count':part_count,'Image Number':img_number})
        file_path = os.path.join('static/to-download/','{}_summary_{}-{}.csv'.format(user, j,i))
        file_path2 = os.path.join('static/to-download/','{}_keypoint_centers_{}-{}.csv'.format(user,j,i))
        summary.to_csv(file_path ,index=False)
        data.to_csv(file_path2 ,index=False)
        
        myzip.close()
        
        _delete_file(archive_name)
       
        _set_task_descriptor(user, i,j,dup, num_zips)

        a,b = 'output_{}-gold-picked_in-{}-images.csv'.format(j,i), 'myzip_{}.zip'.format(num_zips)
        
        return print('Images were sucessfully processed in files: ', a, b)

    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

        # Learn how to implement this feature....!!!
        #        with open('app/static/to-download/{}_summary_{}-{}.csv'.format(user, j,i)) as csvDataFile:
        #
        #            send_email('[Microblog] Your blog posts',
        #                sender=app.config['ADMINS'][0], recipients=[user.email],
        #                text_body=render_template('email/export_posts.txt', user=user),
        #                html_body=render_template('email/export_posts.html', user=user),
        #                attachments=[('summary.csv', 'text/csv',csvDataFile)],
        #                sync=True)
        #
        #        csvDataFile.close()

        #        responsecsv = make_response(data.to_csv())
        #        responsezip = make_response(myzip)
        #
        #        cd1 = 'attachment; filename=detected_particles.csv'
        #        cd2 = 'attachment;  filename=picked_imgs.zip'
        #
        #        responsecsv.headers['Content-Disposition'] = cd1
        #        responsezip.headers['Content-Disposition'] = cd2
        #        responsecsv.mimetype='text/csv'
        #        responsezip.mimetype='application/zip'

        # Response( data.to_csv(), mimetype='text/csv',
        #                headers={'Content-Disposition': "attachment; filename=detected_particles.csv"}),\
        #                Response(myzip, mimetype='application/zip', \
        #                headers={'Content-Disposition': "attachment; filename=picked_imgs.zip"})

        # headers.set('Content-Type', 'text/csv')
        # resp.headers["Content-Disposition"] = "attachment; filename=detected_particles.csv
        # resp.headers["Content-Type"] = "text/csv"

        # could also save this to a destination folder - but have to pre configure that folder.

        #        send_email('Your IGEM images were successfully processed!',
        #                   sender=app.config['ADMINS'][0], recipients=[user.email],
        #                   text_body=render_template('email/picked_particles.txt', user=user),
        #                   htmp_body=render_template('email/picked_particles.html', user=user),
        #                   attachments=[('detected_particles.csv', 'text/csv', resp)],
        #                   sync=True)

        # send email with the saved CSV of recorded detected Gold particle centers
        # in email record how many particles were detected!

        # save data frame to csv >> static/CSV/task_id ...
        # finally save.to_csv('enter_name.csv'.format(dr),index=False)
        # have to keep track of the final file location to put back into zip!
        # look into automatically deleting files >> concurrently removing their name
        # from the database
        # allow users to choose from images they've previously uploaded!

        # create wrapper function dedicated to update the task/progress being performed in the background!

def _delete_file(archive_name):
    
    file_path = os.path.join('static/arch/','{}'.format(archive_name))
    os.remove(file_path)
    
    print('{} Successfuly Deleted'.format(archive_name))

def _set_task_progress(progress):

    '''
    :param progress: Updates the progress :var of the task
    :return:  When progress == 100, redis task is completed
    '''

    job = get_current_job()
    if job:
        job.meta['Picker Progress:'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress':progress})
        if progress >= 100:
            task.complete = True
            
        db.session.commit()
        
# create a wrapper function to update the tasks description.
# only picking when done...

def _set_task_descriptor(user, i,j, dup, num_zip):

    '''
    :param user: User name/id
    :param i: Total images counted
    :param j: Total particles counted
    :param dup: The total duplicates counted...
    :param num_zip: The value of the .zip folder...

    :return: db.session.commit() saves paths of processed files to Tasks column in database.
             Paths will be accessed by routes.py and pushed to downloads.html
    '''
    job = get_current_job()
    if job:
        task = Task.query.get(job.get_id())
        task.complete = True
        task.description = '{} gold particles were detected in {} images with {} duplicates found.'.format(j,i, dup)
        task.csv_key = '{}_keypoint_centers_{}-{}.csv'.format(user,j,i)
        task.csv_sum = '{}_summary_{}-{}.csv'.format(user, j,i)
        task.zip_name = 'myzip_{}.zip'.format(num_zip)
        task.img_count = i
        db.session.commit()
        
def _set_description(i,j,dup):

    '''
    :param i: Total images counted
    :param j: Total particles counted
    :param dup: The total duplicates counted...
    :return: db.session.commit() saves progress to Tasks column in database.
    '''
    
    job = get_current_job()
    if job:
        descript = '{} gold particles were detected in {} images with {} duplicates found.'.format(j,i, dup)
        job.meta['Description'] = descript
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'description':descript})
        db.session.commit()

def search(query):
    '''
    :param query: From pubmed.html form to search database.
    :return: Returns dictionary with pubmed search results
    '''
    Entrez.email = 'josephmarsilla@gmail.com'
    handle = Entrez.esearch(db='pubmed', 
                            sort='relevance', 
                            retmax='20',
                            retmode='xml', 
                            term=query)
    results = Entrez.read(handle)
    return results

def fetch_details(id_list):
    '''
    :param id_list: Id's of (and up to) the first 10 articles
    :return: Returns modified dictionary with PubMed search results
    '''
    ids = ','.join(id_list)
    Entrez.email = 'josephmarsilla@gmail.com'
    handle = Entrez.efetch(db='pubmed',
                           retmode='xml',
                           id=ids)
    results = Entrez.read(handle)
    return results

def article_search(user_id):
    '''
    :param user_id: User name/id to get database column
    :return: Saves PubMed selected queries (article titles) & abstracts in .txt to access by routes.py
    '''
    try:
        user = User.query.get(user_id)
        search_term = user.recent_searchs
        print(search_term)
        results = search(search_term)
        id_list = results['IdList']
        papers = fetch_details(id_list)
        
        paper_names = []
        paper_abstracts = []
        
        for i, paper in enumerate(papers['PubmedArticle']): 
            paper_names.append("%d) %s" % (i+1, paper['MedlineCitation']['Article']['ArticleTitle']))
            paper_abstracts.append("%d) %s" % (i+1, paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0]))
        
        file = os.path.join('static/to-download/', 'pubmed_queries.txt')
        results = open(file, 'w')
        for item in paper_names:
            results.write("%s\n" % item)
        results.close()
        
        file = os.path.join('static/to-download/','pubmed_abstracts.txt')
        results2 = open(file, 'w')
        for item in paper_abstracts:
            results2.write("%s\n" % item)
        results2.close()
        
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
