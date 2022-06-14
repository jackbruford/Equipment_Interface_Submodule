import cv2

def test():
    cv2.namedWindow("preview")
    vc = cv2.VideoCapture(1)
    if vc.isOpened():
        rval, frame = vc.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    else:
        rval = False

    while rval:
        cv2.imshow("preview",frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rval, frame = vc.read()
        key = cv2.waitKey(20)
        if key == 27: # exit on ESC
            break

    cv2.destroyWindow("preview")
    vc.release()

class TestoIR:
    def __init__(self, cameraNum =1):
        self.vc = cv2.VideoCapture(cameraNum)
        if self.vc.isOpened():
            pass
        else:
            raise IOError("Could not connect to camera, try alternative camera input")
    def getFrame(self, imagetype = "gray"):
        """ imagetype can be rgb or grey"""
        rval, frame = self.vc.read()
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
    test()