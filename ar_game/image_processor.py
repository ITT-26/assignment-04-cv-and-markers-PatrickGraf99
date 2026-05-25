from enum import Enum

import cv2
import cv2.aruco as aruco
import sys
import numpy as np
import mediapipe as mp

class StatusCode(Enum):
    SUCCESS = 0
    ARUCO_ERROR = 1
    NO_CURSOR = 2
    NO_CAM = 3

class ImageProcessor:

    def __init__(self, listener):

        self.listener = listener
        video_id = 0
        if len(sys.argv) > 1:
            video_id = int(sys.argv[1])

        # Define the ArUco dictionary, parameters, and detector
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
        aruco_params = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(aruco_dict, aruco_params)

        # Create a video capture object for the webcam
        self.cap = cv2.VideoCapture(video_id)
        ret, self.frame = self.cap.read()

        image_size = self.frame.shape[:2]
        listener.update_frame_size(image_size)

        self.contour_thresh = 100

        self.cursor_x = None
        self.cursor_y = None


    def update(self):
        # Capture a frame from the webcam
        ret, self.frame = self.cap.read()
        status = StatusCode.SUCCESS

        if not ret:
            print('Image Processor failed to capture camera footage')
            status = StatusCode.NO_CAM
            self.notify_frame_available(status)
            return

        # Convert the frame to grayscale
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)

        # Detect ArUco markers in the frame
        corners, ids, rejectedImgPoints = self.detector.detectMarkers(gray)

        # Check if marker is detected
        if ids is not None:
            # Draw lines along the sides of the marker
            aruco.drawDetectedMarkers(self.frame, corners)
            #for _id in ids:
            #    print(_id)

        #if corners is not None and len(corners) > 0:
        #    for corner in corners:
        #        print(corner[0])

        # Detection and extraction loop was written by chatGPT. It basically follows the same logic as part 1 of the
        # assignment
        if ids is not None and len(ids) == 4:
            #print('Found 4 markers, extracting image')
            marker_dict = {}

            for marker_id, corner in zip(ids.flatten(), corners):
                marker_dict[marker_id] = corner[0]

            required_ids = [0, 1, 2, 3]

            if all(i in marker_dict for i in required_ids):
                src_pts = np.float32([
                    marker_dict[0][2],  # TL marker inner corner
                    marker_dict[1][3],  # TR
                    marker_dict[2][0],  # BR
                    marker_dict[3][1],  # BL
                ])

                h, w = self.frame.shape[:2]

                dst_pts = np.float32([
                    [0, 0],
                    [w, 0],
                    [w, h],
                    [0, h]
                ])

                matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                self.frame = cv2.warpPerspective(self.frame, matrix, (w, h))

                #self.find_and_add_contours()
                if not self.colored_tip_contour():
                    status = StatusCode.NO_CURSOR
        else:
            status = StatusCode.ARUCO_ERROR

        # Display the frame
        #cv2.imshow('frame', self.frame)

        # Update listener here???
        print('Processed image, sending data to game')
        self.notify_frame_available(status)



    def find_and_add_contours(self):
        """
        MY take at trying to find contours manually
        """
        gray_scale_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(gray_scale_image, self.contour_thresh, 255, cv2.THRESH_BINARY)

        contours, hierachy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.frame = cv2.drawContours(self.frame, contours, -1, (255, 0, 0), 3)

    def colored_tip_contour(self):
        """
        Method was proposed by ChatGPT
        Use a colored object on finger (blue in this case, like wrap tape around the finger
        This method tracks a finger very reliably

        Notable advantages: No noise if compared to normal contouring using a threshold. Does not require the entire
        hand like google mediapipe would. Possible to build own 'Controller' by using a blue tape on a stick (or really
        any blue object)
        """
        hsv_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([100, 150, 50])
        upper_blue = np.array([140, 255, 255])

        mask = cv2.inRange(hsv_image, lower_blue, upper_blue)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)

            area = cv2.contourArea(largest)

            if area > 100:
                x, y, w, h = cv2.boundingRect(largest)

                # This will be our cursor coordinates
                center_x = x + w // 2
                center_y = y + h // 2
                self.cursor_x = center_x
                self.cursor_y = center_y

                cv2.circle(self.frame, (center_x, center_y), 10, (0, 255, 0), -1)

                return True

        return False


    def get_image(self):
        return self.frame

    def notify_frame_available(self, status):
        data = {
            'status': status,
            'frame': self.frame,
            'cursor': (self.cursor_x, self.cursor_y)
        }
        #print(status)
        self.listener.handle_frame_ready(data)

    def stop(self):
        self.cap.release()
        cv2.destroyAllWindows()

