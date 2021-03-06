import cv2
import numpy as np
import math
import win32api, win32con
import winsound

from mouse_commands import *
from random import randint


"""ENG_STATES = {
    0: "fist"
    1: "single finger"
    3: "three fingers"
    5: "open hand"
}"""

mouse = Mouse()
FINGER_THRESH = 2.0
DETECT_SIZE = 300


STATES_W_CLICK = { #mouse action will be instant, click cannot be held
    0: mouse.scroll,
    1: mouse.left_click,
    3: mouse.right_click,
    5: mouse.reset
}

STATES_W_DRAG = { #click will be held until reset
    0: mouse.scroll,
    1: mouse.left_press,
    # 2: lambda: mouse.left_unpress(), mouse.right_unpress(),
    3: mouse.right_press,
    5: mouse.reset
}

STATES = STATES_W_CLICK #can be changed to if/else for user input

# takes an image, grayscale, gaussian blur, then adjustable threshold (waitkey) for binary color
def threshold(img, binary_thresh):
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    value = (17,17)
    blurred = cv2.GaussianBlur(grey, value, cv2.BORDER_REPLICATE)
    _, threshholded = cv2.threshold(blurred, binary_thresh, 255, cv2.THRESH_BINARY)
    return threshholded

# useful to get rid of stuff that's not a hand
def touchingEdge(contour, dimensions):
    x, y, w, h = cv2.boundingRect(contour)
    if x <= 1 or y <= 1:
        return True
    if x + w + 1 >= dimensions[0] or y + h + 1 >= dimensions[1]:
        return True
    return False

# assume the hand is the biggest contour
def extractHandContour(contours):
    maxArea, index = 0, 0
    for i in xrange(len(contours)):
        area = cv2.contourArea(contours[i])
        if area > maxArea and not touchingEdge(contours[i], (DETECT_SIZE, DETECT_SIZE)):
            maxArea = area
            index = i
    realHandContour = contours[index]
    realHandLen = cv2.arcLength(realHandContour, True)
    handContour = cv2.approxPolyDP(realHandContour, 0.001 * realHandLen, True)

    return handContour

def centerWithReduction(handContour):
        scaleFactor = 0.3
        shrunk = np.array(handContour * scaleFactor, dtype=np.int32)
        tx, ty, w, h = cv2.boundingRect(shrunk)
        maxPoint = None
        maxRadius = 0
        for x in xrange(w):
            for y in xrange(h):
                # find the center of the circle by trying all x and y, iterally
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

# find center and radius of circle inscribed in hand
def findCircle(handContour):
    palmCenter = centerWithReduction(handContour)
    palmRadius = cv2.pointPolygonTest(handContour, tuple(palmCenter), True)
    return palmCenter, palmRadius

# draw circles inscribed in hand and threshold for finger detection
def drawCircles(drawing, palmCenter, palmRadius):
    cv2.circle(drawing, tuple(palmCenter), int(palmRadius), (0, 255, 0), 2)
    cv2.circle(drawing, tuple(palmCenter), int(FINGER_THRESH * palmRadius), (255, 0, 0), 2)

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


def drawFingers(points, drawing, width=8, color=(255,255,255)):
    for i in xrange(len(points)):
        if len(points) == 1:
            print(points[i])
        cv2.circle(drawing, (int(points[i][0]), int(points[i][1])), width, color, -1)

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
    return np.array(fingers)

def correctFingers(fingers, radius):
    try:
        i = 0
        while i < len(fingers) and len(fingers) > 1:
            if getR(fingers[i], fingers[i-1]) < radius:
                fingers = np.delete(fingers, i-1, 0)
                if not i:
                    i += 1
            else:
                i += 1
        return fingers

    except Exception as e:
        return fingers

# actually squared
def getR(point, center):
    return ((point[0] - center[0])**2 + (point[1] - center[1])**2)

def do_gesture(num):
    if num in STATES:
        STATES[num]()
def rps():
    n=0
    lst=[]
    BINARY_THRESH = 30
    cap = cv2.VideoCapture(0)
    _, img = cap.read()
    # cv2.imshow('Gesture', img)
    height, width = img.shape[:2]
    final_image = np.zeros((height, width*2, 3), np.uint8)

    recording_mouse = True

    last_num_fingers = 0
    last2_num_fingers = 0
    last3_num_fingers = 0

    while True:
        ret, img = cap.read()

        # box in which we're gonna be looking for the hand
        cv2.rectangle(img,(100 + DETECT_SIZE,100 + DETECT_SIZE),(99,99),(0,255,0),0)
        crop_img = img[100:100 + DETECT_SIZE, 100:100 + DETECT_SIZE]

        # convert to binary color via thresholding
        thresh1 = threshold(crop_img, BINARY_THRESH)

        try:
            image, contours, hierarchy = cv2.findContours(thresh1.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

            handContour = extractHandContour(contours)
            palmCenter, palmRadius = findCircle(handContour)
            drawing = np.zeros(crop_img.shape,np.uint8)
            fingers = getFingers(handContour, palmCenter, (palmRadius * FINGER_THRESH)**2)

            fingers = correctFingers(fingers, (palmRadius * 0.2) ** 2)

            num_fingers = len(fingers)
            if num_fingers > 5:
                num_fingers = 5
        except Exception as e:
            num_fingers = last2_num_fingers

        if len(fingers) != last_num_fingers and last2_num_fingers == last3_num_fingers and len(fingers) == last2_num_fingers:
            last_num_fingers = len(fingers)


        last3_num_fingers = last2_num_fingers
        last2_num_fingers = len(fingers)

        # find all that shit and mark it

        try:
            hullPoints, defects = findHullAndDefects(handContour)
            drawFingers(fingers, drawing, 10, (255, 255, 0))
            drawCircles(drawing, palmCenter, palmRadius)
            cv2.drawContours(drawing, [handContour], 0, (0, 255, 0), 1)
            cv2.drawContours(drawing, [hullPoints], 0, (0, 0, 255), 2)
        except Exception as e:
            pass


        drawing = cv2.flip(drawing, 1)
        img = cv2.flip(img, 1)
        thresh1 = cv2.flip(thresh1, 1)

        final_image[:height, :width] = img
        final_image[:DETECT_SIZE, width:width+DETECT_SIZE] = drawing
        thresh1 = cv2.resize(thresh1, (DETECT_SIZE, DETECT_SIZE))
        thresh1 = cv2.cvtColor(thresh1,cv2.COLOR_GRAY2RGB)

        cv2.putText(final_image, str(num_fingers) + " fingers", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)


        cv2.imshow('FINAL', final_image)
        cv2.imshow('Thresholded', thresh1)


        # Key press
        k = cv2.waitKey(10)
        if k == 27:
            break
        elif k == 43: # PLUS
            BINARY_THRESH += 2
            if BINARY_THRESH > 255:
                BINARY_THRESH = 255
            print(BINARY_THRESH)
        elif k == 45: # MINUS
            BINARY_THRESH -= 2
            if BINARY_THRESH < 0:
                BINARY_THRESH = 0
            print(BINARY_THRESH)
        else:
            pass

    while n<3:

        ret, img = cap.read()

        # box in which we're gonna be looking for the hand
        cv2.rectangle(img,(100 + DETECT_SIZE,100 + DETECT_SIZE),(99,99),(0,255,0),0)
        crop_img = img[100:100 + DETECT_SIZE, 100:100 + DETECT_SIZE]

        # convert to binary color via thresholding
        thresh1 = threshold(crop_img, BINARY_THRESH)

        try:
            image, contours, hierarchy = cv2.findContours(thresh1.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

            handContour = extractHandContour(contours)
            palmCenter, palmRadius = findCircle(handContour)
            drawing = np.zeros(crop_img.shape,np.uint8)
            fingers = getFingers(handContour, palmCenter, (palmRadius * FINGER_THRESH)**2)

            fingers = correctFingers(fingers, (palmRadius * 0.2) ** 2)

            num_fingers = len(fingers)
            if num_fingers > 5:
                num_fingers = 5
            # print(num_fingers)
        except Exception as e:
            num_fingers = last2_num_fingers

        if len(fingers) != last_num_fingers and last2_num_fingers == last3_num_fingers and len(fingers) == last2_num_fingers:
            lst.append(len(fingers))
            last_num_fingers = len(fingers)


        last3_num_fingers = last2_num_fingers
        last2_num_fingers = len(fingers)

        # find all that shit and mark it

        try:
            hullPoints, defects = findHullAndDefects(handContour)
            drawFingers(fingers, drawing, 10, (255, 255, 0))
            drawCircles(drawing, palmCenter, palmRadius)
            cv2.drawContours(drawing, [handContour], 0, (0, 255, 0), 1)
            cv2.drawContours(drawing, [hullPoints], 0, (0, 0, 255), 2)
        except Exception as e:
            pass




        drawing = cv2.flip(drawing, 1)
        img = cv2.flip(img, 1)
        thresh1 = cv2.flip(thresh1, 1)

        final_image[:height, :width] = img
        final_image[:DETECT_SIZE, width:width+DETECT_SIZE] = drawing
        thresh1 = cv2.resize(thresh1, (DETECT_SIZE, DETECT_SIZE))
        thresh1 = cv2.cvtColor(thresh1,cv2.COLOR_GRAY2RGB)

        cv2.putText(final_image, str(num_fingers) + " fingers", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)


        cv2.imshow('FINAL', final_image)
        cv2.imshow('Thresholded', thresh1)


        # Key press
        k = cv2.waitKey(10)
        if k == 27:
            break
        else:
            pass
        n+=1
    return lst


def main():
    BINARY_THRESH = 30
    cap = cv2.VideoCapture(0)
    _, img = cap.read()
    # cv2.imshow('Gesture', img)
    height, width = img.shape[:2]
    final_image = np.zeros((height, width*2, 3), np.uint8)

    recording_mouse = True


    last_num_fingers = 0
    last2_num_fingers = 0
    last3_num_fingers = 0


    while True:

        ret, img = cap.read()

        # box in which we're gonna be looking for the hand
        cv2.rectangle(img,(100 + DETECT_SIZE,100 + DETECT_SIZE),(99,99),(0,255,0),0)
        crop_img = img[100:100 + DETECT_SIZE, 100:100 + DETECT_SIZE]

        # convert to binary color via thresholding
        thresh1 = threshold(crop_img, BINARY_THRESH)

        try:
            image, contours, hierarchy = cv2.findContours(thresh1.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

            handContour = extractHandContour(contours)
            palmCenter, palmRadius = findCircle(handContour)
            drawing = np.zeros(crop_img.shape,np.uint8)
            fingers = getFingers(handContour, palmCenter, (palmRadius * FINGER_THRESH)**2)

            fingers = correctFingers(fingers, (palmRadius * 0.2) ** 2)

            num_fingers = len(fingers)
            if num_fingers > 5:
                num_fingers = 5
            # print(num_fingers)
        except Exception as e:
            num_fingers = last2_num_fingers
            print(e)

        if len(fingers) != last_num_fingers and last2_num_fingers == last3_num_fingers and len(fingers) == last2_num_fingers:
            print("fingers: ", len(fingers))
            # winsound.PlaySound("pop.wav", winsound.SND_ASYNC)
            last_num_fingers = len(fingers)


        last3_num_fingers = last2_num_fingers
        last2_num_fingers = len(fingers)

        # find all that shit and mark it

        try:
            hullPoints, defects = findHullAndDefects(handContour)
            drawFingers(fingers, drawing, 10, (255, 255, 0))
            drawCircles(drawing, palmCenter, palmRadius)
            cv2.drawContours(drawing, [handContour], 0, (0, 255, 0), 1)
            cv2.drawContours(drawing, [hullPoints], 0, (0, 0, 255), 2)
        except Exception as e:
            # print("This is a draw error")
            # print(e)
            pass


        # move the mouse
        if recording_mouse:
            x = palmCenter[0]
            y = palmCenter[1]
            mouse.set_pos(x, y)

        # do_gesture(num_fingers)




        drawing = cv2.flip(drawing, 1)
        img = cv2.flip(img, 1)
        thresh1 = cv2.flip(thresh1, 1)

        final_image[:height, :width] = img
        final_image[:DETECT_SIZE, width:width+DETECT_SIZE] = drawing
        thresh1 = cv2.resize(thresh1, (DETECT_SIZE, DETECT_SIZE))
        thresh1 = cv2.cvtColor(thresh1,cv2.COLOR_GRAY2RGB)
        # final_image[DETECT_SIZE:DETECT_SIZE*2, width:width+DETECT_SIZE] = thresh1

        cv2.putText(final_image, str(num_fingers) + " fingers", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)


        cv2.imshow('FINAL', final_image)
        # cv2.imshow('drawing', drawing)
        cv2.imshow('Thresholded', thresh1)


        # Key press
        k = cv2.waitKey(10)
        if k == 27:
            break
        elif k == -1:
            continue
        elif k == 43: # PLUS
            BINARY_THRESH += 2
            if BINARY_THRESH > 255:
                BINARY_THRESH = 255
            print(BINARY_THRESH)
        elif k == 45: # MINUS
            BINARY_THRESH -= 2
            if BINARY_THRESH < 0:
                BINARY_THRESH = 0
            print(BINARY_THRESH)
        elif k == 114:
            recording_mouse = not recording_mouse
        else:
            print k

if __name__ == '__main__':
    main()
