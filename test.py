import cv2
import numpy as np
import math
import win32api, win32con
from mouse_commands import *


SCROLL_INVERSE_GAIN = 5


def threshold(img):
    grey = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    value = (17,17)
    blurred = cv2.GaussianBlur(grey, value, 0)
    _, threshholded = cv2.threshold(blurred, 120, 255,
                               cv2.THRESH_BINARY)
    return threshholded

def extractHandContour(contours):
    maxArea, index = 0, 0
    for i in xrange(len(contours)):
        area = cv2.contourArea(contours[i])
        if area > maxArea:
            maxArea = area
            index = i
    realHandContour = contours[index]
    realHandLen = cv2.arcLength(realHandContour, True)
    handContour = cv2.approxPolyDP(realHandContour,
                                        0.001 * realHandLen, True)
    return handContour

def centerWithReduction(handContour):
        scaleFactor = 0.3
        shrunk = np.array(handContour * scaleFactor, dtype=np.int32)
        tx, ty, w, h = cv2.boundingRect(shrunk)
        maxPoint = None
        maxRadius = 0
        for x in xrange(w):
            for y in xrange(h):
                rad = cv2.pointPolygonTest(shrunk, (tx + x, ty + y), True)
                if rad > maxRadius:
                    maxPoint = (tx + x, ty + y)
                    maxRadius = rad
        try:
            realCenter = np.array(np.array(maxPoint) / scaleFactor,
                                      dtype=np.int32)
            error = int((1 / scaleFactor) * 1.5)
            maxPoint = None
            maxRadius = 0
            for x in xrange(realCenter[0] - error, realCenter[0] + error):
                for y in xrange(realCenter[1] - error, realCenter[1] + error):
                    rad = cv2.pointPolygonTest(handContour, (x, y), True)
                    if rad > maxRadius:
                        maxPoint = (x, y)
                        maxRadius = rad
        except :
            maxPoint = None

        return np.array(maxPoint)

def findCircle(handContour):
    palmCenter = centerWithReduction(handContour)
    palmRadius = cv2.pointPolygonTest(handContour, tuple(palmCenter), True)
    return palmCenter, palmRadius

def findHullAndDefects(handContour):
    hullHandContour = cv2.convexHull(handContour, returnPoints = False)
    hullPoints = [handContour[i[0]] for i in hullHandContour]
    hullPoints = np.array(hullPoints, dtype = np.int32)
    defects = cv2.convexityDefects(handContour, hullHandContour)
    return hullPoints, defects

def drawVertices(points, drawing, width=2, color=(255,255,255)):
    for i in xrange(len(points)):
            for j in xrange(len(points[i])):
                cv2.circle(drawing, (points[i][j][0], points[i][j][1]), width, color)

# list the fucking fingers
def getFingers(points, center, thresh):
    fingers = []
    last_r = getR(points[0, 0], center)
    last_last_r = getR(points[-1, 0], center)
    for i in xrange(1, len(points) + 1):
        this_r = getR(points[i % len(points), 0], center)
        if this_r <= last_r and last_r > last_last_r and last_r > thresh:
            fingers.append(points[i-1, 0])
        last_last_r = last_r
        last_r = this_r
    return fingers

# actually squared
def getR(point, center):
    return ((point[0] - center[0])**2 + (point[1] - center[1])**2)


cap = cv2.VideoCapture(0)

while(cap.isOpened()):

    # ugliest workaround. joe: "*frown"
    try:
        ret, img = cap.read()
        cv2.rectangle(img,(300,300),(100,100),(0,255,0),0)
        crop_img = img[100:300, 100:300]
        # crop_img = img

        thresh1 = threshold(crop_img)
        cv2.imshow('Thresholded', thresh1)

        image, contours, hierarchy = cv2.findContours(thresh1.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)


        handContour = extractHandContour(contours)
        palmCenter, palmRadius = findCircle(handContour)

        drawing = np.zeros(crop_img.shape,np.uint8)

        fingers = getFingers(handContour, palmCenter, (palmRadius * 1.6)**2)
        num_fingers = len(fingers)
        drawVertices([fingers], drawing, 10, (255, 255, 0))
        print(num_fingers)

        minX, minY, handWidth, handHeight = cv2.boundingRect(handContour)

        x = 1920 -  palmCenter[0] * 1920//200
        y = palmCenter[1] * 1080//200

        win32api.SetCursorPos((x, y))


        # find all that shit
        hullPoints, defects = findHullAndDefects(handContour)





        # cnt = max(contours, key = lambda x: cv2.contourArea(x))
        #
        # x,y,w,h = cv2.boundingRect(cnt)
        # cv2.rectangle(crop_img,(x,y),(x+w,y+h),(0,0,255),0)


        win32api.SetCursorPos((x, y))
        mouse.x, mouse.y = win32api.GetCursorPos()


        # hull = cv2.convexHull(cnt)

        drawing = np.zeros(crop_img.shape,np.uint8)
        # cv2.drawContours(drawing,[cnt],0,(0,255,0),0)
        # cv2.drawContours(drawing,[hull],0,(0,0,255),0)

        # draw the circle
        cv2.circle(drawing, tuple(palmCenter), int(palmRadius), (0, 255, 0), 10)
        cv2.circle(drawing, tuple(palmCenter),
                       10, (255, 0, 0), -2)
        # hull = cv2.convexHull(cnt)


        # draw hand contour
        cv2.drawContours(drawing, [handContour], 0, (0, 255, 0), 1)
        # drawVertices(handContour, drawing)

        # = draw hull contour
        cv2.drawContours(drawing, [hullPoints], 0, (0, 0, 255), 2)
        drawVertices(hullPoints, drawing)


        cv2.imshow('drawing', drawing)

        cv2.imshow('Gesture', img)
        all_img = np.hstack((drawing, crop_img))

        k = cv2.waitKey(10)
        if k == 27:
            break
    except:
        pass
