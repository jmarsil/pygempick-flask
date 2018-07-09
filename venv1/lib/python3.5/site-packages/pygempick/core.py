"""
Created on Wed May  9 15:06:15 2018

@author: joseph
"""
import numpy as np
import cv2

def compress(orig_img):
    '''
    Takes a large image and compresses it 3.3 times in our case 
    images are outputed originally as large 9MB images...
    
    (That much reolution is unecessary when determining positioning of gold 
    particles. )
    '''
    
    r = 1018/orig_img.shape[1] ##correct aspect ratio of image to prevent distortion
    dim = (1018, int(orig_img.shape[0]*r))
    
    resized_img = cv2.resize(orig_img, dim, interpolation = cv2.INTER_AREA)
    
    gray_img = cv2.cvtColor(resized_img, cv2.COLOR_RGB2GRAY)
    
    return gray_img

def back_eq(image):
    '''
    background equalization
    taken from https://stackoverflow.com/questions/39231534/get-darker-lines-of-an-image-using-opencv
    
    To enable picking on images with little contrast.
    '''
    
    max_value = np.max(image)
    backgroundRemoved = image.astype(float)
    blur = cv2.GaussianBlur(backgroundRemoved, (151,151), 50)
    backgroundRemoved = backgroundRemoved/blur
    backgroundRemoved = (backgroundRemoved*max_value/np.max(backgroundRemoved)).astype(np.uint8)
    
    return backgroundRemoved



##define the filter of the scaled 3x3 laplacian kernel...(High Contract LPF)
def hclap_filt(p,image, noise):
    
    '''
    New High Contrast Laplace Filter. Takes odd scaling parameter p > 5, regular
    compressed image, if noise == 'yes' will add median blur after filter applied.
    
    '''
    
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    kernel = np.array([[0,-1,0], [-1,p,-1], [0,-1,0]])
    
    output = cv2.filter2D(image, -1, kernel)
    
    if noise == 'yes':
        
        output = cv2.medianBlur(output,9)
    
    return output

    
def hlog_filt(p, image, noise):
   
    gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    kernel = np.array([[0,0,-1,0,0],[0,-1,-2,-1,0],[-1,-2,p,-2,-1],[0,-1,-2,-1,0],[0,0,-1,0,0]])
    
    output = cv2.filter2D(gray_img, -1, kernel)
    
    if noise == 'yes':
        
        output = cv2.medianBlur(output,9)
    
    return output


##define difference of Gaussian Filter as used w/ SIFT method...(Lowe,2004)
def dog_filt(p,image):
    
    '''
    Difference of Gaussian Filter. Takes odd scaling parameter tau, regular
    compressed image, if noise == 'yes' will add median blur after filter applied.
    ''' 
    gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    p=p+2
       #run a 5x5 gaussian blur then a 3x3 gaussian blr
    blurp = cv2.GaussianBlur(gray_img,(p,p),0)
    blur3 = cv2.GaussianBlur(gray_img,(3,3),0)

    DoGim = blurp - blur3
    
    #returns the filtered binary image...
    return DoGim


def bin_filt(p, image):
    
    '''
    Smart Binary Filtering. Uses the average gray pixel intensity value to determing 
    the starting threshold position. Takes odd scaling parameter p, 
    image = regular compressed image
    ''' 
    
    gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    ##If Possible #Histogram Equilization of blurred image
    hist, _ = np.histogram(gray_img.flatten(),256,[0,256])
    #65 to 145 on the x is a good truncation #
    #after this there is a change in concavity...
    ##apending max histogram intensities into a list
    histx = np.argmax(hist)
    
    thresh = histx - np.int(60 + p*1.5)
    ##if there are truly no black dots on this image, this value will be true 
    ##- so set the threshold value to zero...
    
    if np.isnan(thresh) == True:
        thresh = 0
    
    _, thresh_img = cv2.threshold(image, int(thresh), 255, cv2.THRESH_BINARY)
     
    return thresh_img, np.array([thresh, histx])


    
def pick(image, minAREA, minCIRC, minCONV, minINER, minTHRESH):
    '''
    image = resulting binary image from filter, minArea = lowest area in pixels 
    of gold particle (20 px**2), lowest circularity of gold particle [.78 is square], 
    minConv = lowest convextivity parameter (is there a space between detected 
    particle - optimization with this parameter can help us differentiate between
    overlapping particles, minINER = minimum inertial ratio (filters particle
    based on their eliptical properties). 
    
    Detects immunogold particles on filtered binary image by optimizing picking
    across 4 main paramaters using OpenCv's simple blob detector. 
    
    Have to optimize for each set separately on a per class or per trial basis. 
    
    '''
    # Set up the SimpleBlobdetector with default parameters.
    params = cv2.SimpleBlobDetector_Params()
    
    if minAREA > 0: 
        # Filter by Area.
        params.filterByArea = True
        params.minArea = minAREA
    
    if minCIRC > 0: 
        # Filter by Circularity
        params.filterByCircularity = True
        params.minCircularity = minCIRC
    
    if minCONV > 0:
        # Filter by Convexity
        params.filterByConvexity = True
        params.minConvexity = minCONV
    
    if minINER > 0:
        #  Filter by Inertia - fix this by theory (what does gold particle look like?)
        params.filterByInertia =True
        params.minInertiaRatio = minINER
    
    if minTHRESH > 0:
        # Change thresholds
        params.minThreshold = 0;
        params.maxThreshold = minTHRESH;
    
    else:
         params.maxThreshold = 255;
     
    detector = cv2.SimpleBlobDetector_create(params)
    
    keypoints1 = detector.detect(image)
    
    return keypoints1

def key_filt(keypoints1,keypoints2):
    
    '''
    If there are any similar keypoints between two filtering methods used,
    This will find and remove duplicates in one list. 
    '''
    duplicates = 0 
    
    if len(keypoints1) != 0 and len(keypoints2) != 0:

        newk1 = keypoints1
        for k1 in keypoints1:
            for k2 in keypoints2:
                
                if int(k1.pt[0]) == int(k2.pt[0]) and int(k1.pt[1]) == int(k2.pt[1]):
                    #if condition is met then one duplicate is removed from 
                    #duplicated list above...
                    newk1.remove(k1)
                    duplicates += 1
    
        return newk1, duplicates
    
    else:
        
        return keypoints1, duplicates

def snapshots(folder, keypoints, gray_img, i):
    
    '''
    folder = folder location where snapshots will be saved, keypoints = output 
    from pick() , gray_img = compressed grayscale image, i = image number.
    
    Takes an compressed grayscale image and uses the detected keypoints as a marker
    to take a snapshot within a 100px radius of that gold particle's position. 
    
    '''
    
    if len(keypoints) > 0:

        #append x and y coordinates of keypoint center pixels
        ni = len(keypoints) #number of particles in image
        x = np.zeros(ni)
        y = np.zeros(ni)
        
        k = 0
        
        for keypoint in keypoints:
            ## save the x and y coordinates to a new array...
            
            x[k] = keypoint.pt[0]
            y[k] = keypoint.pt[1]
            
            k+=1
        
        j = 0 #index counter
        count = 0
        
        for points in x:
            
            xs = x[j]
            ys = y[j]
            k = int(xs) #sets the center point x value reference
            h = int(ys) #sets the center point y value reference
            
            ind = []
            
            for s in range(len(x)):
                
                rad = np.sqrt((k-int(x[s]))**2 + (h-int(y[s]))**2)
                
                
                if rad < 50: 
                    
                    ind.append(s)
            
            ## will delete the pair of points that had a radius less than the 
            ## snapshot that was taken...
            x = np.delete(x, ind)
            y = np.delete(y, ind)
            
            ##fix boundary conditions...
            
            refxmin = k - 50
            refxmax = k + 50
            refymin = h - 50
            refymax = h + 50
            
            if refxmin < 0:
                refxmin = 0
            
            if refymin < 0:
                refymin = 0
            
            if refxmax > np.shape(gray_img)[1]:
                refxmax = np.shape(gray_img)[1]
            
            if refymax > np.shape(gray_img)[0]:
                refymax = np.shape(gray_img)[0]
            
            
            ##take a snapshot of the aggregates w/in a 50px radius...
            a = gray_img[refymin:refymax,refxmin:refxmax]
            
            ##snapshot counter...
            count+=1
            
            #write snapshot to snapshot folder...
            cv2.imwrite('{}/im_{}_snap_{}.jpg'.format(folder, i,count), a)
            
            if j in ind:
                j = 0
                
            else:
                j+=1
            
            if len(x) == 0:
                
                break
    
    else:
        
        count = 0
    
    return count


def laplace_of_gaussian(image, sigma=1., kappa=0.75, pad=False):
    """
    Taken from: https://stackoverflow.com/questions/22050199/
    python-implementation-of-the-laplacian-of-gaussian-edge-detection
    
    #shows the regular laplace of gaussian...
    
    Applies Laplacian of Gaussians to grayscale image.

    :param gray_img: image to apply LoG to
    :param sigma:    Gauss sigma of Gaussian applied to image, <= 0. for none
    :param kappa:    difference threshold as factor to mean of image values, <= 0 for none
    :param pad:      flag to pad output w/ zero border, keeping input image size
    """
    gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    assert len(gray_img.shape) == 2
    img = cv2.GaussianBlur(gray_img, (0, 0), sigma) if 0. < sigma else gray_img
    img = cv2.Laplacian(img, cv2.CV_64F)
    rows, cols = img.shape[:2]
    # min/max of 3x3-neighbourhoods
    min_map = np.minimum.reduce(list(img[r:rows-2+r, c:cols-2+c]
                                     for r in range(3) for c in range(3)))
    max_map = np.maximum.reduce(list(img[r:rows-2+r, c:cols-2+c]
                                     for r in range(3) for c in range(3)))
    # bool matrix for image value positiv (w/out border pixels)
    pos_img = 0 < img[1:rows-1, 1:cols-1]
    # bool matrix for min < 0 and 0 < image pixel
    neg_min = min_map < 0
    neg_min[1 - pos_img] = 0
    # bool matrix for 0 < max and image pixel < 0
    pos_max = 0 < max_map
    pos_max[pos_img] = 0
    # sign change at pixel?
    zero_cross = neg_min + pos_max
    # values: max - min, scaled to 0--255; set to 0 for no sign change
    value_scale = 255. / max(1., img.max() - img.min())
    values = value_scale * (max_map - min_map)
    values[1 - zero_cross] = 0.
    # optional thresholding
    if 0. <= kappa:
        thresh = float(np.absolute(img).mean()) * kappa
        values[values < thresh] = 0.
    log_img = values.astype(np.uint8)
    if pad:
        log_img = np.pad(log_img, pad_width=1, mode='constant', constant_values=0)
    return log_img
