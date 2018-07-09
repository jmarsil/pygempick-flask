#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  9 18:49:45 2018

@author: joseph
"""
import pandas as pd
import numpy as np
import cv2
import scipy.misc as misc

#import pygempick module(s)
import pygempick.core as core

def gamma(a,b,r):
    
    ''' 
    a = width of image in pixels, b = height of the image in pixels, r is the 
    diatance of the donut from which correlation was calculated. Function taken from
    work by Philemonenko et al 2000 used as a window covariogram to correct Ripley's
    K function for boundary conditions.
    '''
    
    A = a*b
    return A - (2/np.pi)*(a+b)*r + (1/np.pi)*r**2

def pcf(r, N, p0, p1):
    
    '''
    r is the radius of the donut taken with bin width dr. N is the degree
    PCF (Pair Correlation Function) is the probability distribution of a CSR 
    related process that we will used to fit our normalized version of 
    Philmoneko's PCF diostributtion for calculating colocolization of immunogold
    particles on microgrpahs.
    
    '''
    
    return 1/misc.factorial(p1)*(p0**N)*(r**(p1))*np.exp(-p0*r)


def bin2csv(images):
    
    '''
    images is a set of images from folder using glob.glob() function,
    records the keypoint positions found in each image and outputs a csv with
    detected keypoint centers in (x,y) pixel coordinates.
    
    '''

    i = 0  #image counter
    j = 0
    #------------------------
       
    data = pd.DataFrame()
    #Change picking parameters per test set...
    #p = np.int(input('Center anchor of filter: '))
    minArea = np.int(input('Min Area to Detect: '))
    minCirc = np.float(input('Min Circularity: '))
    minCon = np.float(input('Min Concavity: '))
    minInert = np.float(input('Min Inertial Ratio: '))
    
    for image in images:
        
        orig_img = cv2.imread(image) ##reads specific test file
        gray_img = cv2.cvtColor(orig_img, cv2.COLOR_RGB2GRAY)
        #output = ef.IGEM_filter(p,orig_img, 'no') ##filters image
        keypoints = core.pick(gray_img, minArea, minCirc, minCon , minInert) ##picks the keypoints
                
        if len(keypoints) > 0:
            #append x and y coordinates of keypoint center pixels
            n = len(keypoints) #number of particles in image
            x = np.zeros(n)
            y = np.zeros(n)
        
                
        k = 0
                
        for keypoint in keypoints:
            ## save the x and y coordinates to a new array...
                    
            x[k] = keypoint.pt[0]
            y[k] = keypoint.pt[1]
                    
            k+=1
                
            df = pd.DataFrame({'x{}'.format(i): x, 'y{}'.format(i) : y})
            data = pd.concat([data,df], ignore_index=True, axis=1)
                
        j += k   
        i +=1
        
    # =============================================================================
    
    ## can use two different plots K at every r for each image on a scatter...
    print('Particles Detected in set : {}'.format(j))
    
    file = input("Name your file")
    
    data.to_csv('{}'.format(file),index=False)
    
    #returns total number of particles detected per binary image in set
    return data

def bin2df(images):
    
    '''
    images is a set of images from folder using glob.glob() function,
    records the keypoint positions found in each image and outputs a pandas
    df with detected keypoint centers in (x,y) pixel coordinates. 
    
    '''
    
    i = 0  #image counter
    j = 0 #total particles
    #------------------------
       
    data = pd.DataFrame()
    #Change picking parameters per test set...
    #p = np.int(input('Center anchor of filter: '))
    minArea = np.int(input('Min Area to Detect: '))
    minCirc = np.float(input('Min Circularity: '))
    minCon = np.float(input('Min Concavity: '))
    minInert = np.float(input('Min Inertial Ratio: '))
    
    for image in images:
        
        orig_img = cv2.imread(image) ##reads specific test file
        gray_img = cv2.cvtColor(orig_img, cv2.COLOR_RGB2GRAY)
        #output = ef.IGEM_filter(p,orig_img, 'no') ##filters image
        keypoints = core.pick(gray_img, minArea, minCirc, minCon , minInert) ##picks the keypoints
                
        if len(keypoints) > 0:
            #append x and y coordinates of keypoint center pixels
            n = len(keypoints) #number of particles in image
            x = np.zeros(n)
            y = np.zeros(n)
        
                
        k = 0 #particle counter
                
        for keypoint in keypoints:
            ## save the x and y coordinates to a new array...
                    
            x[k] = keypoint.pt[0]
            y[k] = keypoint.pt[1]
                    
            k+=1
            
             
            
            df = pd.DataFrame({'x{}'.format(i): x, 'y{}'.format(i) : y})
            data = pd.concat([data,df], ignore_index=True, axis=1)
        
        j += k
            
        i+=1

    return data, j #returns data as df and total particles accounted...

def csv2pcf(data, dr):
    
    '''
    Takes data from csv produced by bin2csv() and outputs non-normalized k 
    and pcf (pair-correlation) spatially invairenttime series for set of images...
    Analyzed by bin2csv. Example output provided in docs.
    
    dr is the donut width as defined by philmonenko et al, 2000
    
    '''
    
    N = int(input('How Many Processed Images in this set?'))
    ni = int(input('How many particles were detected?')) #nuber of particles counted in test set

    
    data1 = pd.read_csv(data, header=None, skiprows=1)
    data = pd.DataFrame(data1)
    
    a = 776 ## number of y pixels in image (height)
    b = 1018 ##number of x pixels in image (width)
    
    #explain why this function is required for statistical detection of immunogold clusters in the data...
    
    l = (1/N)*ni #average density of particles lables across this test set of images
    dni = 50*ni/1000. #false negatives missed by picker per 1000
    
    #correct the boundary effect of image by using the geometric covariogram of the
    # window - defined in Ripley 1988 -- this is given by the gamma function in A_correlation_test
    
    k = []
    dk = []
    pcf = []
    dpcf = []
    
    for r in range(0,100,dr): ##analyze the clustering in a given region between two circles. 
        
        kc = 0
        ki = 0
        
        for p in range(0,len(data),2):
            
            #x,y coordinates of detected immunogold keypoints occur in set of twos in the loaded csv file
            x = np.array(data[p][~np.isnan(data[p])])
            y = np.array(data[p+1][~np.isnan(data[p+1])])
            
            if len(x) > 0:
                
                for i in range(len(x)-1): ##ensure that there are no duplicates while comparing all keypoints
                
                    for j in range(i+1, len(x)):
                            
                        rad = np.sqrt((x[i]-x[j])**2 + (y[i] - y[j])**2)
                            
                        if r < rad <= r+dr: #if radius is less than this area b/w circles
                                
                            kc+= 1/gamma(a,b,rad) #classical K function
                            ki+= 1/(rad*gamma(a,b, rad)) #pair correlation function
                        
                        else:
                            kc+=0   
                            ki+=0
                            
                print(p)
                
        a = kc*(1/(N*l))
        da = a*(dni/ni)
        b = ki*(1/(N*l*2*np.pi))
        db = b*(dni/ni)
       
        k.append(a) #classical K function
        dk.append(da)
        pcf.append(b)
        dpcf.append(db)
        
        print(k,r) 
    
    return k, pcf , dk, dpcf

def keypoints2pcf(data_set, dr):
    
    '''
    Input folder with CSV files of keypoints for different tests
    Need to know Image number and average particles detected in each set
    
    data_set = glob.glob('/home/joseph/Documents/PHY479/Data/anto/*.csv')
    
    output: pcf-dr{}-error.csv - columns dr (sampling radius), pcf 
    (pair correlation coefficient), dpcf (propogated uncertainty in pcf)
    
    '''

    save = pd.DataFrame()
    
    for data in data_set:
        
        print(data)
        
        k, pcf, dk, dpcf = csv2pcf(data, dr)
        
        #plot the Classical K function 
        #Input name of specific data set recorded...
        
        name = input('Test set name:')      
        
        npcf = np.array(pcf)/sum(pcf)
        
        sumd = np.sqrt(sum(np.array(dpcf)**2))
        
        dnpcf = npcf*np.sqrt((np.array(dpcf)/pcf)**2 + (sumd/sum(pcf))**2)
        
        df = pd.DataFrame({'dr-{}'.format(name): np.linspace(1,101, len(pcf)), 'PCF-{}'.format(name): npcf, 'dpcf-{}'.format(name): dnpcf})
        
        save = pd.concat([save,df], ignore_index=False, axis=1)
        
        print(npcf,dnpcf)
    
    save.to_csv('pcf-dr{}-error.csv'.format(dr),index=False)
