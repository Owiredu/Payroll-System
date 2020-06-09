import cv2
import socket
import os
import sys
import time
import pickle
import numpy
import math
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import pyqtSignal, QThread, QDir
from PyQt5.QtMultimedia import QCameraInfo
from utils import resource_path
from mtcnn.mtcnn import MTCNN


class FaceRegistrationThread(QThread):
    """
    This is the thread that faces and writes them appropriately
    """

    change_pixmap = pyqtSignal(QPixmap, name='change_pixmap')

    # argument types: String, String or int, Function
    def __init__(self, subject_id, camera_id):
        super().__init__()
        self.video_playing = False
        self.subject_id = subject_id
        self.camera_id = camera_id
        self.icons_base_dir = 'src\\..//icons'
        self.training_data_dir = 'src\\..//training_data'
        self.max_capture_count = 20
        # load the label-id map if it exists
        self.label_id_dic = dict()
        self.load_label_id_dict()
        # create the face detector
        self.detector = MTCNN()

    def prep_video_capture(self, fps=60, buffer_size=10):  # argument types: int, int
        """
        This method prepares the video capture
        """
        # open video stream from selected camera
        self.vid_capture = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        # set the frame rate
        self.vid_capture.set(cv2.CAP_PROP_FPS, fps)
        # set the buffersize
        self.vid_capture.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
        # get the frame width
        self.frame_width = int(self.vid_capture.get(3))
        # set the zero matrix to be used as the black background for the time in the frame
        if self.frame_width > 400:
            self.frame_width = 400
        self.black_surface_colored = numpy.zeros(
            (30, self.frame_width, 3), numpy.uint8)

    def start_capture(self):
        """
        This method starts the video capture
        """
        self.video_playing = True

    def stop_capture(self):
        """
        This method stops the video capture
        """
        self.video_playing = False

    def convertToRGB(self, frame):  # argument types: Mat
        """
        This method converts bgr image to rgb
        """
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def convertToGRAY(self, frame):  # argument types: Mat
        """
        This method converts bgr image to grayscale
        """
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def store_label_id_dict(self, label):  # argument types: String
        """
        This method stores a dictionary of the mapping of the label to the id to a pickle file
        """
        label_id_file = open(resource_path(
            self.training_data_dir + os.sep + 'label_id_map.pkl'), 'wb')
        self.label_id_dic.__setitem__(label, self.subject_id)
        dic_pkl = pickle.dumps(self.label_id_dic)
        label_id_file.write(dic_pkl)
        label_id_file.flush()
        label_id_file.close()

    def load_label_id_dict(self):
        """
        This method loads the map between the label and id
        """
        try:
            label_id_file = open(resource_path(
                self.training_data_dir + os.sep + 'label_id_map.pkl'), 'rb')
            label_id_data = label_id_file.read()
            self.label_id_dic = pickle.loads(label_id_data)
            label_id_file.close()
        except FileNotFoundError:
            pass

    def get_label(self):
        """
        This method returns the next label
        """
        return str(0)

    def detect_face(self, frame):
        """
        Detects faces using Multi-Task Cascaded Convolutional Neural Network
        """
        # make a copy of the frame
        img_copy = frame.copy()
        # detect the faces
        faces_results = self.detector.detect_faces(frame)
        QApplication.processEvents()
        # return nothing if no face is detected
        if len(faces_results) == 0:
            return None, None
        # get the dimensions for the first face. NB: only one face is expected to be present for registration purposes
        (x, y, w, h) = faces_results[0]['box']
        # draw a rectangle around the face
        cv2.rectangle(img_copy, (x, y), (x+w, y+h),
                      (0, 255, 0), 2, cv2.LINE_AA)
        # return frame with detected face and the cropped face
        return img_copy, frame[y:y+h, x:x+w]

    # argument types: String, Mat, int
    def write_image_to_training_folder(self, folder_name, gray_face_img, count):
        """
        This method writes the cropped face image into the respective folder
        """
        if count == 0:
            dir_path = resource_path(
                self.training_data_dir + os.sep + folder_name)
            os.makedirs(dir_path, exist_ok=True)
        file_path = resource_path(
            self.training_data_dir + os.sep + folder_name + os.sep + str(count) + '.jpg')
        cv2.imwrite(file_path, cv2.resize(gray_face_img, (200, 200)))

    def run(self):
        """
        This method runs all the processes
        """
        try:
            # initialize pose text to regular pose and the initial time for the time countdown
            # and the notification text
            registering_text = 'Registering...'
            starting_in_text = 'Starting in '
            pose_regular_text = 'Pose: Regular'
            pose_smile_text = 'Pose: Smile'
            pose_laugh_text = 'Pose: Laugh'
            pose_frown_text = 'Pose: Frown'
            pose_bend_head_left_text = 'Pose: Bend Head Left'
            pose_bend_head_right_text = 'Pose: Bend Head Right'
            pose_head_up_text = 'Pose: Head Up'
            pose_head_down_text = 'Pose: Head Down'
            pose_turn_head_left_text = 'Pose: Turn Head Left'
            pose_turn_head_right_text = 'Pose: Turn Head Right'
            stage_not_text = registering_text
            pose = 'Pose: Regular'
            init_pose_time = 0
            # initialize initial time for time interval before capture begins and the duration
            init_reg_time = time.time()
            wait_time_duration = 10      # in seconds
            # initialize the count for the number training data and folder name
            capture_count = 0
            # set the label
            label = self.get_label()
            for key in self.label_id_dic.keys():
                if self.label_id_dic[key] == self.subject_id:
                    label = key
            subject_folder_name = 's' + label
            # set the frame count for url stream sources
            self.frame_from_url_source = None
            # set loading image
            self.change_pixmap.emit(
                QPixmap(resource_path(self.icons_base_dir + os.sep + 'loading_vid.jpg')))
            # prepare video capture
            self.prep_video_capture()
            # run video capture loop
            while self.video_playing:
                # get the frames
                ret, frame = self.vid_capture.read()
                # if a valid frame was returned ...
                if ret:
                    # resize the frame is it is larger that 400 in width
                    if frame.shape[1] > 400:
                        frame = cv2.resize(frame, (400, 300))

                    #########
                    # get time difference
                    init_time_diff = math.floor(time.time() - init_reg_time)
                    if init_time_diff > wait_time_duration:
                        # create the black background at the botton left corner
                        frame[frame.shape[0]-30:frame.shape[0],
                              0:self.frame_width] = self.black_surface_colored
                        # show the notification text
                        cv2.putText(frame, stage_not_text, (10, frame.shape[0]-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                        # show the pose label as regular
                        cv2.putText(frame, pose, (math.floor(frame.shape[1] / 2), math.floor(frame.shape[0]-10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                        # get the data after the face is detected
                        detected_face_frame, cropped_face = self.detect_face(
                            frame)
                        if detected_face_frame is not None:
                            # convert the full frame with the rectangle around the face to rgb for display
                            detected_face_rgb = self.convertToRGB(
                                detected_face_frame)
                            # convert the bgr image into a pyqt image
                            qimage = QImage(
                                detected_face_rgb.data, detected_face_rgb.shape[1], detected_face_rgb.shape[0], QImage.Format_RGB888)
                            # create the QPixmap from the QImage
                            qpixmap = QPixmap.fromImage(qimage)
                            # send the pixmap as a signal to the caller (the label in the mdi sub window)
                            self.change_pixmap.emit(qpixmap)
                            # write image to training folder for 20 images
                            # regular face: 4; smile: 2; frown: 2; bend head left: 2; bend head right: 2; head up: 2; head down: 2; turn head left: 2; turn head down: 2;
                            if capture_count < self.max_capture_count:
                                # regular face: 4
                                if capture_count < 2:
                                    if pose != pose_regular_text:
                                        pose = pose_regular_text
                                    self.write_image_to_training_folder(
                                        subject_folder_name, cropped_face, capture_count)
                                    capture_count += 1
                                # smile: 2
                                elif capture_count < 4:
                                    if pose != pose_smile_text:
                                        pose = pose_smile_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # laugh: 2
                                elif capture_count < 6:
                                    if pose != pose_laugh_text:
                                        pose = pose_laugh_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # frown: 2
                                elif capture_count < 8:
                                    if pose != pose_frown_text:
                                        pose = pose_frown_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # bend head left: 2
                                elif capture_count < 10:
                                    if pose != pose_bend_head_left_text:
                                        pose = pose_bend_head_left_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # bend head right: 2
                                elif capture_count < 12:
                                    if pose != pose_bend_head_right_text:
                                        pose = pose_bend_head_right_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # head up: 2
                                elif capture_count < 14:
                                    if pose != pose_head_up_text:
                                        pose = pose_head_up_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # head down: 2
                                elif capture_count < 16:
                                    if pose != pose_head_down_text:
                                        pose = pose_head_down_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # turn head left: 2
                                elif capture_count < 18:
                                    if pose != pose_turn_head_left_text:
                                        pose = pose_turn_head_left_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                                # turn head right: 2
                                elif capture_count < 20:
                                    if pose != pose_turn_head_right_text:
                                        pose = pose_turn_head_right_text
                                        # set the initial time for the countdown
                                        init_pose_time = time.time()
                                    # find the difference between the current time and the initial
                                    pose_time_diff = math.floor(
                                        time.time() - init_pose_time)
                                    if pose_time_diff > wait_time_duration:
                                        # set the notification text to registering
                                        stage_not_text = registering_text
                                        # write the image
                                        self.write_image_to_training_folder(
                                            subject_folder_name, cropped_face, capture_count)
                                        capture_count += 1
                                    else:
                                        # set the notification text to the countdown
                                        if pose_time_diff >= wait_time_duration:
                                            stage_not_text = registering_text
                                        else:
                                            stage_not_text = starting_in_text + \
                                                str(wait_time_duration -
                                                    pose_time_diff)
                            else:
                                # store label and id map
                                self.store_label_id_dict(label)
                                # end the capture
                                self.video_playing = False
                        else:
                            # convert the full frame with the rectangle around the face to rgb for display
                            rgb_image = self.convertToRGB(frame)
                            # convert the bgr image into a pyqt image
                            qimage = QImage(
                                rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QImage.Format_RGB888)
                            # create the QPixmap from the QImage
                            qpixmap = QPixmap.fromImage(qimage)
                            # send the pixmap as a signal to the caller (the label in the mdi sub window)
                            self.change_pixmap.emit(qpixmap)
                    else:
                        # create the black background at the botton left corner
                        frame[frame.shape[0]-30:frame.shape[0],
                              0:self.frame_width] = self.black_surface_colored
                        # show the countdown
                        cv2.putText(frame, starting_in_text + str(wait_time_duration - init_time_diff + 1), (10, frame.shape[0]-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                        # show the pose label as regular
                        cv2.putText(frame, pose_regular_text, (math.floor(frame.shape[1] / 2), math.floor(frame.shape[0]-10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                        # convert the full frame with the rectangle around the face to rgb for display
                        rgb_image = self.convertToRGB(frame)
                        # convert the bgr image into a pyqt image
                        qimage = QImage(
                            rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QImage.Format_RGB888)
                        # create the QPixmap from the QImage
                        qpixmap = QPixmap.fromImage(qimage)
                        # send the pixmap as a signal to the caller (the label in the mdi sub window)
                        self.change_pixmap.emit(qpixmap)
                else:
                    # set restart image after video from camera or local file is done playing or stopped by user
                    self.change_pixmap.emit(QPixmap(resource_path(
                        self.icons_base_dir + os.sep + 'default_camera_view.jpg')))
                    # stop other running processes
                    self.stop_capture()

            # set restart image
            self.change_pixmap.emit(QPixmap(resource_path(
                self.icons_base_dir + os.sep + 'default_camera_view.jpg')))
            # when the video stream is stopped, release the camera and its related resources
            self.vid_capture.release()
        except:
            raise Exception("Camera not accessible")
