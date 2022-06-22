import time

import cv2
import datetime
import scipy.io

def test(log=False, imagetype="gray", Speriod = 0, cameraNum =0):
    frames2log = []
    times2log = []

    cv2.namedWindow("preview")
    vc = cv2.VideoCapture(cameraNum)
    if vc.isOpened():
        rval, frame = vc.read()
        if imagetype == "gray":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif imagetype =="rgb":
            pass
        else:
            raise ValueError("imagetype is not a valid input")
        if log:
            frames2log.append(frame)
            times2log.append(time.time())


    else:
        rval = False

    t = time.time()
    while rval:
        cv2.imshow("preview", frame)
        rval, frame = vc.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if log and time.time()-t > Speriod:
            frames2log.append(frame)
            times2log.append(time.time())
            t = time.time()
        key = cv2.waitKey(20)
        if key == 27: # exit on ESC
            break
    if log:
        filename = 'IRframes_' + datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.mat'
        datadict = {"IRframes": frames2log,
                    "frameTimes": times2log}
        # save to mat file
        scipy.io.savemat(filename, datadict)
    cv2.destroyWindow("preview")
    vc.release()

class TestoIR:
    def __init__(self, cameraNum =0):
        self.vc = cv2.VideoCapture(cameraNum)
        if self.vc.isOpened():
            pass
        else:
            raise IOError("Could not connect to camera, try alternative camera input")
    def getFrame(self, imagetype = "gray"):
        """ imagetype can be rgb or grey"""
        if self.vc.isOpened():
            rval, frame = self.vc.read()
        else:
            rval = False
        if not rval:
            raise IOError("Could not get frame from camera")
        else:
            if imagetype == "gray":
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            elif imagetype == "rgb":
                pass
            else:
                raise ValueError("imagetype parameter must be 'rgb' or 'gray'")
            return frame

if __name__ == "__main__":
    test(log=True, Speriod= 10)