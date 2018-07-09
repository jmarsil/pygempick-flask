#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 29 09:58:58 2018

@author: joseph
"""
import sys
import os
from app import create_app
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
import csv
#import time

from app.models import Task, User
from app import db


app = create_app()
app.app_context().push()

#first task to run is the image compression
#second task to run is the filtering - can do this all at one shot...
#Use values the user just inputted in the database (ie most recent variables)
#in calculation - we don't have to save them all!
#task can perform in the background and will send email when complete!
#see 22.2.2.4 in microblog - miguel flask pdf

#images is obtained from a glob.glob command
#this is from the most recent archive uploaded static/arch - file location can be accessed from database
# images is an archive file in zip format...

##process of particle picking 
## get the most rescent archive file location by timestamp...
## input that file into this function...
## get the most recent parameters from this user from the database...
## once task is created >> automatically save folder information to process 
## exanble bin folder loc , picked folder loc, data folder loc...
## when complete >> export those three folders into one final zip that will be 
## sent to the user at her/his email address!

def record_kp(i, keypoints, data):
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
    
    args = [anchor1, anchor2, minArea, minCirc, minConc, minIner]
    
    '''
    
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        
        
        i = 0 #image counter
        j = 0 #particle(s) detected counter
        dup = 0
        data = pd.DataFrame() #make empty data frame to hold keypoints
        
        #need the most recent uploaded archive
        ZIP = user.own_zips().first()
        
        archive_name = ZIP.archive_filename
        #need the most recent recorded parameters of user!
        PARAM = user.own_params().first()
        
        anchor1 = np.float(PARAM.anchor1)
        anchor2 = np.float(PARAM.anchor2)
        minArea = np.float(PARAM.minArea)
        minCirc = np.float(PARAM.minCirc)/100
        minConc = np.float(PARAM.minConc)/100
        minIner = np.float(PARAM.minIner)/100
        comments = PARAM.comments
        
        zips = glob.glob("app/static/to-download/*.zip")
        num_zips = len(zips)
        
        myzip = zipfile.ZipFile("app/static/to-download/myzip_{}.zip".format(num_zips), "w")
        #read the image file from most rescent archive location
        
        with zipfile.ZipFile('app/static/arch/{}'.format(archive_name)) as images: 
        #read the archive images as namelist
            img_names = images.namelist()
        
            img_number = []
            part_count = []
            
            for image in img_names[1:]:
                with images.open(image) as tif:
                    imgdata=Image.open(tif).convert('RGB')
                
                cv_image = np.array(imgdata) 
                cv_image = cv_image[:, :, ::-1].copy() 
                
                r = 1018/cv_image.shape[1] ##correct aspect ratio of image to prevent distortion
                dim = (1018, int(cv_image.shape[0]*r))
    
                gray_img = cv2.resize(cv_image, dim, interpolation = cv2.INTER_AREA)
    
                #gray_img = cv2.cvtColor(resized_img, cv2.COLOR_RGB2GRAY)
                ## orig_img = cv2.imread(image) ##reads specific test file image     
                #gray_img = py.compress(imgdata) #use pygempick to compress image...
        
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
                
                cv2.imwrite(os.path.join(app.config['IMG_PICKED'], '{}.jpg'.format(i)), picked)
                
                myzip.write('{}/{}.jpg'.format(app.config['IMG_PICKED'],i))
                
                # save the image with picked gold particles to memory folder 
                # >> static/picked/task_id
                #cv2.imwrite('!LOCATION!/<task_id>_picked_{}.jpg'.format(i),\ picked)
                
                data, k = record_kp(i,keypoints, data)

                dup += dup1
                j += k # total particles counted 
                i += 1 # total images
                #time.sleep(5)
                img_number.append(i)
                part_count.append(k)
                
                _set_description(i,j,dup)
                _set_task_progress(100 * i // len(img_names))
       
        part_count.append('Task Comments:')
        print(comments)
        img_number.append(comments)
        summary = pd.DataFrame({'Gold Count':part_count,'Image Number':img_number})
        summary.to_csv('app/static/to-download/{}_summary_{}-{}.csv'.format(user, j,i),index=False)
        data.to_csv('app/static/to-download/{}_keypoint_centers_{}-{}.csv'.format(user,j,i),index=False)
        
        
            
        myzip.close()
       
        _set_task_descriptor(user, i,j,dup, num_zips)
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
        a,b = 'output_{}-gold-picked_in-{}-images.csv'.format(j,i), 'myzip_{}.zip'.format(num_zips)
        
        return print('Images were sucessfully processed in files: ', a, b)
        #Response( data.to_csv(), mimetype='text/csv', 
        #                headers={'Content-Disposition': "attachment; filename=detected_particles.csv"}),\
        #                Response(myzip, mimetype='application/zip', \
        #                headers={'Content-Disposition': "attachment; filename=picked_imgs.zip"})
        
        #headers.set('Content-Type', 'text/csv')
        #resp.headers["Content-Disposition"] = "attachment; filename=detected_particles.csv
        #resp.headers["Content-Type"] = "text/csv"
        
        #could also save this to a detsination folder - but have to pre configure that folder.

#        send_email('Your IGEM images were sucessfully processed!',
#                   sender=app.config['ADMINS'][0], recipients=[user.email],
#                   text_body=render_template('email/picked_particles.txt', user=user),
#                   htmp_body=render_template('email/picked_particles.html', user=user),
#                   attatchments=[('detected_particles.csv', 'text/csv', resp)],
#                   sync=True)
        
        
        #send email with the saved CSV of recorded detected Gold particle centers
        #in email record how many particels were detected!

    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    
    # save dataframe to csv >> static/CSV/task_id ...
    # finally save.to_csv('enter_name.csv'.format(dr),index=False)
    # have to keep track of the final file location to put back into zip!
    # look into automatically deleting files >> concurrently removing their name
    # from the database 
    # allow users to choose from images they've previously uploaded!
    
#create wrapper function dedicated to update the task/progress being performed in the background!

def _set_task_progress(progress):
    
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
        
#create a wrapper function to update the tasks description. 
#only picking when done...
def _set_task_descriptor(user, i,j, dup, num_zip):
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
    Entrez.email = 'josephmarsilla@gmail.com'
    handle = Entrez.esearch(db='pubmed', 
                            sort='relevance', 
                            retmax='20',
                            retmode='xml', 
                            term=query)
    results = Entrez.read(handle)
    return results

def fetch_details(id_list):
    ids = ','.join(id_list)
    Entrez.email = 'josephmarsilla@gmail.com'
    handle = Entrez.efetch(db='pubmed',
                           retmode='xml',
                           id=ids)
    results = Entrez.read(handle)
    return results

def article_search(user_id):
    try:
        user = User.query.get(user_id)
        search_term = user.recent_searchs
        print(search_term)
        results = search(search_term)
        id_list = results['IdList']
        papers = fetch_details(id_list)
        
        paper_names = []
        for i, paper in enumerate(papers['PubmedArticle']): 
            paper_names.append("%d) %s" % (i+1, paper['MedlineCitation']['Article']['ArticleTitle']))
        
        results = open('app/static/to-download/pubmed_queries.txt', 'w')
        for item in paper_names:
            results.write("%s\n" % item)
        
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())