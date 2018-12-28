import cv2
import time
import glob
import numpy as np
import pandas as pd
import pygempick as py
import pygempick.spatialstats as spa
import matplotlib.pyplot as plt

# for the test examined by the web application:
# 3.7x10_-6 , HCLAP:27, HLOG:18, MA:31, MCirc:79, MCONV:59, MINER:59, Part A

# import test image:
orig_img = cv2.imread('/Users/josephmarsilla/PycharmProjects/pygempick-flask/static/img/Set1_AL09_-6_0000.tif')
print(orig_img.shape) #original image shape is (2444, 3744, 3)
# compress it to a value of r, corrects aspect ratio of image to prevent distortion
r = 1018/orig_img.shape[1] #use this value to correct all x coordinates
r2 = 644/orig_img.shape[0]   #use this value to correct all y coordinates

dim = (1018, int(orig_img.shape[0] * r))

whole_truth = '/Users/josephmarsilla/PycharmProjects/pygempick-flask/static/Data/A_Joe_WholeTruth_10-6_Full.csv'
picked_full = '/Users/josephmarsilla/PycharmProjects/pygempick-flask/static/Data/<User jmarsil>_keypoint_centers_4894-100.csv'

#turn .csv's into pandas dataframes...
data_true = pd.DataFrame(pd.read_csv(whole_truth))
data_picked = pd.DataFrame(pd.read_csv(picked_full))

FN_all = []
FP_all = []
TP_all = []

for p in range(0, 200,2):

    # x,y coordinates of manually detected immunogold particles
    x_wt = np.array(data_true.iloc[:, p])*r
    x_wt = x_wt[~np.isnan(x_wt)]

    y_wt = np.array(data_true.iloc[:, p + 1])*r2
    y_wt = y_wt[~np.isnan(y_wt)]

    #x, y coordinated of pygempick detected immunogold particles on TEM images
    x = np.array(data_picked.iloc[:, p])
    x = x[~np.isnan(x)]
    y = np.array(data_picked.iloc[:, p + 1])
    y = y[~np.isnan(y)]

    TP = 0
    FP = 0
    FN = 0
    for i in range(len(x_wt)):
        for q in range(len(x)):

            distance = np.sqrt((x_wt[i] - x[q])**2 + (y_wt[i] - y[q])**2)
            #print(distance)

            if distance < 20: #(allowing 4px variation between x and y directions )
                # count all correct pairings
                # when it finds a pair within this distance it breaks out of the loop
                TP += 1
                break

    FP = len(x) - TP
    FN = len(x_wt) - TP

    FN_all.append(FN)
    FP_all.append(FP)
    TP_all.append(TP)

print('TP:',sum(TP_all), '/n FP:', sum(FP_all), '/n FN:', sum(FN_all))

#length of x_wt final is the amount of false negatives
#length of x at the end is the amount of false positives


# If the radius between the points is less that 1, consider it a TRUE POSITIVE.
# If (x_wt[i], y_wt) is NOT in (x,y) consider FALSE NEGATIVE
# Present a table with manual counts...
# When plotting, have a range of error, on the lowest end - threshold of 15 - highest end 17
# Plot precision/recall = precision is the ratio TP/(TP+FP) : Recall is the ratio TP/(TP+Fn)
# see how this changes when other parameters are varried by picking.
# altering the distance parameter will change this ratio (I believe this is independent to parameters chosen)






