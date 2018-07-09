#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  9 17:01:04 2018

@author: joseph
"""

import numpy as np
import cv2
import random
import pandas as pd
import scipy.optimize as opt
import matplotlib.pyplot as plt

#import pygempick module(s)
import pygempick.core as core
import pygempick.spatialstats as spa
    
def draw(n, test_number, noise, images):
    
    '''
    n = particle number of real data set to make fake distribution, test_number:
    1 for only circles , 2 for both circles and ellipses, if noise == 'yes' 
    will add random gaussian noise to mu and sigma of distribution for gray 
    image intensities, images is the number of images you would like to produce
    in the modeled set of micrographs.
    '''
    
    row = 776  #image height
    col = 1018 #image width
    
    radrange = np.arange(4,8,1)
    
    
    mu = n/images #mean particle number across your images
    sigma = np.sqrt(mu) #standard deviation of the mean from your data
    
    ##creates a new normal distribution based on your data (particles,images)
    pick = np.random.normal(mu,sigma)
    
    #height = np.arange(26,750) ##array of possible particle heights
    #width = np.arange(26,992)   ##array of possible particle widths
    height = 750
    width =  990
    count = 0
    circles = 0
    elipses = 0
    #mu1 = .05
    #sig1 = .02
    
    image = 255*np.ones((row,col), np.float32)
    ##convert to BGR
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    if noise == 'yes':
        
        mu1 = input('Input mean of Gaussian Distributed Noise')
        sig1 = input('Input std of Gaussian Distributed Noise')
        
        ##adding random gaussian distributed noise to image...
        for q in range(row):
            for w in range(col):
                
                image[q][w] = np.float32(np.int(255*np.random.normal(mu1,sig1))) 
                ##change this value for high variability in background conditions..
        
    if test_number == 1:
        
        for j in range(np.int(pick)):
            
            count+=1
            
            ##picks a random particle radius between 4 and 8 pixels
            r = random.choice(radrange)
            
            ##chooses a random center position for the circle
            #h = random.choice(height)
            #w = random.choice(width)
            
            w = np.random.uniform(20,width)
            h = np.random.uniform(20,height)
            
            #w = np.int(col*np.random.rand()) #first method used to choose random width/height...
            
            ##ensure that no particles are drawn on the edges of the image
            ##figure out how to void borders...
                
            ##draw a black circle
            cv2.circle(image,(h,w), np.int(r), (0,0,0), -1)
        
        image = (image).astype('uint8')
        print('Complete')
        return image, count

    elif test_number == 2:
        
        q = np.int(pick)
        count = 0
        
        while count <= q:
            
            ##picks a random particle radius between 4 and 8 pixels
            axis = random.choice(radrange)
            #N = width * height / 4
            ##chooses a random center position for the circle
            w = np.int(np.random.uniform(20,width))
            h = np.int(np.random.uniform(20,height))
            
            
              ##bernouli trial to draw either circle or elippse...
            flip = np.random.rand()
            
            if flip < 0.5:
                #draw a circle
                cv2.circle(image,(h,w), np.int(axis), (0,0,0), -1)
                circles +=1
            
            else:
                #draw an elippse...
                elipses += 1
                cv2.ellipse(image,(h,w),(int(axis)*2,int(axis)),0,0,360,(0,0,0),-1)
            
            count += 1
        
        
        count = circles + elipses
        image = (image).astype('uint8')
        return image, int(circles), int(elipses)

def imgclass(inv_img):
    
    '''
    Uses a compressed grayscale image from cvt_color(RGB2GRAY) and returns 
    the intensity histogram and related bins position w/ im_class. 
    
    Can optimize this function to a greater extent.
    
    Recieves following input from:
        
        gray_img = cv2.cvtColor(orig_img, cv2.COLOR_RGB2GRAY)
    
    '''
    ##can edit to make a histogram from of the pixle image intensities of the image...
    
    hist, bins = np.histogram(inv_img.flatten(),256,[0,256])
    #bincenters = 0.5*(bins[1:]+bins[:-1])
    
     ##apending max histogram intensities into a list
    histx = np.argmax(hist)
        
    if histx < 110:
        
        im_class = 1
    
    elif 110 <= histx < 120:
        
        im_class = 2 
        
    elif 120 <= histx < 125:
        
        im_class = 3
        
    elif 125 <= histx < 130:
        
        im_class= 4
        
    elif 130 <= histx < 135:
        
        im_class= 5
    
    elif 135 <= histx < 140:
        
        im_class= 6
        
    elif 140 <= histx < 145:
        
        im_class= 7
        
    elif 145 <= histx < 150:
        
        im_class= 8
        
    elif 150 <= histx < 160:
        
        im_class= 9
    elif histx >= 160:
        
        im_class= 10
    
    return im_class, histx

def septest(p,image):
    
    '''
    let p be a range of integers ranging from [1, x], for the publication x
    is set to 31
    
    let image be a grayscale image produced after original image compression and 
    conversion to grayscale using OpenCv's function
    
    image = gray_img = cv2.cvtColor(orig_img, cv2.COLOR_RGB2GRAY)
    
    
    '''
    
    detected_bin = np.zeros(len(p))
    detected_lap = np.zeros(len(p))
    detected_dog = np.zeros(len(p))
    detected_log = np.zeros(len(p))
    
    #the background conditions of various image sets will varry - 
    #go back and plot 
    for i in range(len(p)): 
        
        #same scaling factor as used by SIFT on the simple scale
        output_bin, _ = core.bin_filt(p[i], image)
        output_lap = core.hclap_filt(p[i],image, 'no')
        output_dog = core.dog_filt(p[i],image) 
        output_log = core.hlog_filt(p[i], image, 'no')
        
        keypoints_bin = core.pick(output_bin, 31, .83, .61 , .61, 0)
        keypoints_lap = core.pick(output_lap, 31, .83, .61 , .61, 0)
        keypoints_dog = core.pick(output_dog, 31, .83, .61 , .61, 0)
        keypoints_log = core.pick(output_log, 31, .83, .61 , .61, 0)
        
        if len(keypoints_lap) > 0:
            detected_lap[i] = len(keypoints_lap)
        else:   
           detected_lap[i] = 0
            
        
        if len(keypoints_dog) > 0:
            detected_dog[i] = len(keypoints_dog)
        else: 
            detected_dog[i] = 0
            
        if len(keypoints_bin)>0:   
            detected_bin[i] = len(keypoints_bin)
        else: 
            detected_bin[i] = 0
            
        if len(keypoints_log)>0:   
            detected_log[i] = len(keypoints_log)
        else: 
            detected_log[i] = 0

    
    #returns an array of the number of particles detected per filtering method...
    #took out detected_dog for a more in depth test...
    return detected_bin, detected_lap, detected_dog, detected_log 

def septest2(p, image, hlogkey):
    
    count = np.zeros(len(p))
    duplicates = np.zeros(len(p))
    keypoints2 = hlogkey
    
    for i in range(len(p)): 
            
        output1 = core.hclap_filt(p[i], image, 'no')

        keypoints1 = core.pick(output1, 31, .83, .5, .5, 0) 

        keypoints1, dup = core.key_filt(keypoints1, keypoints2)
            
        if len(keypoints1) != 0 and len(keypoints2) ==0:
            count[i] = len(keypoints1)
            
        elif len(keypoints1) != 0 and len(keypoints2) !=0:
            count[i] = len(keypoints1) + len(keypoints2)
            
        elif len(keypoints1) == 0 and len(keypoints2) !=0:
            count[i] = len(keypoints2)
                
        else:
            count[i] = 0
            
        duplicates[i] = dup

    
    return count, duplicates

def fitpcf(data):
    
    '''
    data1 = pd.read_csv('/home/joseph/Documents/PHY479/pcf-dr5-error.csv', header=None, skiprows=1)
    Function initially created to plot graphs from V30M and CD1 positve controls ()
    please add modifications and change to suit your needs.
    
    **Note: pcf-dr5-error.csv is a file outputted from keypoints2pcf()
    look to that function to see how that output is formatted. 
    
    Output : built to produce one graph, with fitted curve for positive control(s).  
    Equation fitted to probability distribution for Complete Spatial Randomness of 
    the distribution of IGEM particles across EM micrographs.
    
    '''
   
    data = pd.DataFrame(data)
    data = data.fillna(0)

    #determine guess filtering parameters
    pcfp1 = np.array([100.,1.,1.])
    pcfp2 = np.array([10.,1., 1.])
    
    x = data[2].values
    y = data[0].values
    dy = data[1].values

    x1 = data[5].values
    y1 = data[3].values
    dy1 = data[4].values

    popt1, pcov1 = opt.curve_fit(spa.pcf , x, y,  p0 = pcfp1)
    popt2, pcov2 = opt.curve_fit(spa.pcf , x1, y1,  p0 = pcfp2)

    popt1 = np.around(popt1, decimals=2)
    popt2 = np.around(popt2, decimals=2)

    #The probability of locating the N t h {\displaystyle N^{\mathrm {th} }} 
    #N^{{{\mathrm {th}}}} neighbor of any given point, at some radial distance r 
    #{\displaystyle r} r is:
    
    plt.figure()
    plt.title('Probability of Gold Particle Colocolization on TTR micrographs' )
    #CSR of CD1 Micgrgrap set 
    plt.plot(x,y,'xr') #keypoints of CD1 micrographs
    plt.plot(np.arange(0,110,1), spa.pcf(np.arange(0,110,1), popt1[0], popt1[1], popt1[2]),
                       'r-', label='CD1 CSR, N = {} +/- {}, L = {} +/- {}'.format(popt1[0],
                                                 np.around(np.sqrt(pcov1[0,0]), decimals=3),
                                                 popt1[1], np.around(np.sqrt(pcov1[1,1]), decimals=3))) 
    plt.errorbar(x, y, yerr=dy, fmt='xr')
    plt.plot(x1,y1, 'og') ##keypoints of V30M micrographs
    plt.plot(np.arange(0,110,1), spa.pcf(np.arange(0,110,1), popt2[0], popt2[1], popt2[2]),
                       'g-', label='V30M CSR, N = {} +/- {}, L = {} +/- {}'.format(popt2[0], 
                                                  np.around(np.sqrt(pcov2[0,0]), decimals=3),
                                                  popt2[1], np.around(np.sqrt(pcov2[1,1]), decimals=3))) 
    plt.errorbar(x1, y1, yerr=dy1, fmt='og')
    plt.legend(loc='best')
    plt.grid(True)
    plt.xlabel('Radius (r)')
    #Probability Nth point at distance r 
    plt.ylabel('P(r)')


    