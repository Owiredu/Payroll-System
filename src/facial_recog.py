import os
import time
import cv2
import numpy
import pickle
from threading import Thread
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QImage
from db_conn import DbConnection
from utils import resource_path
from mtcnn.mtcnn import MTCNN


class FacialRecognitionThread(QThread):
    """
    This is the thread that captures and processes the video stream in the login window
    """

    change_pixmap = pyqtSignal(QPixmap, name='change_pixmap')
    recognized_id = pyqtSignal(str, name='recognized_id')

    # argument types: String or int, String, Function
    def __init__(self, camera_id):
        super().__init__()
        self.video_playing = False
        self.camera_id = camera_id
        self.icons_base_dir = 'src\\..//icons'
        self.training_data_dir = 'src\\..//training_data'
        # set default values for settings values in case there is error loading the settings
        self.face_recog_conf_thresh = 80
        self.face_recog_sleep_duration = 1
        # create the face recognizer and load the model
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        # check whether model has not been trained
        self.is_model_trained = False
        # initialize the label-id dictionary
        self.label_id_dic = dict()
        # frame jumping variables
        self.frame_counter = 0
        self.frames_to_jump = 1
        self.prev_faces = None
        self.prev_faces_dims = []
        self.prev_confidences = []
        self.prev_predicted_ids = []
        # create the face detector
        self.detector = MTCNN()

    def prep_video_capture(self, buffer_size=10):  # argument types: int, int
        """
        This method prepares the video capture
        """
        # open video stream from selected camera
        self.vid_capture = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        # set the buffersize
        self.vid_capture.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
        # get the resolution
        self.frame_res = int(self.vid_capture.get(3)), int(
            self.vid_capture.get(4))

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

    def rectangle(self, img, rect):  # argument types: Mat, list
        """
        This method draws a rectangle around the detected face
        """
        (x, y, w, h) = rect
        cv2.rectangle(img, (x-10, y-10), (x+w+10, y+h+10),
                      (0, 255, 0), 2, cv2.LINE_AA)

    def putText(self, img, subject_id, rect):  # argument types: Mat, String, list
        """
        This method writes the id of the recognized person with the rectangle about the face
        """
        (x, y, w, h) = rect
        cv2.putText(img, str(subject_id), (x-10, y-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)

    def detect_faces(self, frame):
        """
        Detects faces using Multi-Task Cascaded Convolutional Neural Network
        """
        # detect the faces
        faces_results = self.detector.detect_faces(frame)
        QApplication.processEvents()
        # return nothing if no face is detected
        if len(faces_results) == 0:
            return None, None
        # draw rectangles around the faces
        cropped_faces = []
        faces_dimensions = []
        for result in faces_results:
            (x, y, w, h) = result['box']
            faces_dimensions.append((x, y, w, h))
            cropped_faces.append(frame[y:y+h, x:x+w])
        # return frame with detected faces
        return cropped_faces, faces_dimensions

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

    def train_model(self):
        """
        This method trains the recognizer model if not already trained and saves it. Otherwise,
        it loads the model from a file
        """
        try:
            # load the face recognizer if available
            self.face_recognizer.read(resource_path(
                self.training_data_dir + os.sep + 'trained_model.xml'))
            # notify that the model has been trained
            self.is_model_trained = True
        except:
            # create list to hold the faces data and corresponding labels
            faces = []
            labels = []
            # get the faces and their corresponding labels
            for subject_dir in os.listdir(resource_path(self.training_data_dir)):
                if subject_dir.startswith('s'):
                    for img_file_name in os.listdir(resource_path(self.training_data_dir + os.sep + subject_dir)):
                        face = cv2.imread(resource_path(
                            'training_data' + os.sep + subject_dir + os.sep + img_file_name))
                        face = self.convertToGRAY(face)
                        faces.append(face)
                        labels.append(int(subject_dir.replace('s', '')))
            # train the recognizer
            self.face_recognizer.train(faces, numpy.array(labels))
            # save the trained model
            self.face_recognizer.save(resource_path(
                self.training_data_dir + os.sep + 'trained_model.xml'))
            # notify that the model has been trained
            self.is_model_trained = True

    def predict_faces(self, frame):  # argument types: Mat
        """
        This method predicts the faces in the frame and returns the frame with the predicted id embedded on it
        """
        try:
            if self.frame_counter == 0:
                # make a copy of the frame to be used for processing
                frame_copy = frame.copy()
                # get the faces and their dimensions
                faces, dims = self.detect_faces(frame_copy)
                if faces is not None:
                    # set the current faces and dimensions as the previous faces and dimensions
                    self.prev_faces = faces
                    self.prev_faces_dims = dims
                    # clear the previous confidences and predicted ids
                    self.prev_confidences.clear()
                    self.prev_predicted_ids.clear()
                    for i, face in enumerate(faces):
                        # recognize the face and return the label
                        collector = cv2.face.StandardCollector_create()
                        self.face_recognizer.predict_collect(
                            self.convertToGRAY(cv2.resize(face, (200, 200))), collector)
                        label = collector.getMinLabel()
                        # get the subject id and confidence (for identifying the particular image)
                        subject_id = self.label_id_dic.get(str(label))
                        distance = collector.getMinDist()
                        max_distance = 250.0
                        # distance of 0 means 100% match
                        confidence = int(
                            round(100.0 * (max_distance - distance) / max_distance, 0))
                        # draw a rectangle around the face
                        self.rectangle(frame, dims[i])
                        # add confidence to previous confidences as well as the predicted ids
                        self.prev_predicted_ids.append(subject_id)
                        self.prev_confidences.append(confidence)
                        if confidence > self.face_recog_conf_thresh:
                            # write the id above the face
                            self.putText(frame, 'ID: ' + subject_id +
                                         ' (' + str(confidence) + '%)', dims[i])
                            # send the ID to the main thread for login
                            self.recognized_id.emit(subject_id)
                        else:
                            # write the UNKNOWN above the face
                            self.putText(frame, 'UNKNOWN', dims[i])
                        # increase the frame counter
                        self.frame_counter += 1
            else:
                for i, face in enumerate(self.prev_faces):
                    # draw a rectangle around the face
                    self.rectangle(frame, self.prev_faces_dims[i])
                    if self.prev_confidences[i] > self.face_recog_conf_thresh:
                        # write the id above the face
                        self.putText(frame, 'ID: ' + self.prev_predicted_ids[i] + ' (' + str(
                            self.prev_confidences[i]) + '%)', self.prev_faces_dims[i])
                    else:
                        # write the UNKNOWN above the face
                        self.putText(frame, 'UNKNOWN', self.prev_faces_dims[i])
                # increase frame counter
                if self.frame_counter <= self.frames_to_jump:
                    self.frame_counter += 1
                else:
                    self.frame_counter = 0
            return frame
        except:
            return frame
        QApplication.processEvents()

    def run(self):
        """
        This method runs the facial recognition thread
        """
        try:
            # set loading image
            self.change_pixmap.emit(
                QPixmap(resource_path(self.icons_base_dir + os.sep + 'loading_vid.jpg')))
            # set model trained to false
            self.is_model_trained = False
            # prepare video capture
            self.prep_video_capture()
            # set fps checker
            is_fps_set = False
            # run video capture loop
            while self.video_playing:
                # get the frames
                ret, frame = self.vid_capture.read()
                # get the fps
                if not is_fps_set:
                    self.fps = self.vid_capture.get(5)
                    is_fps_set = True
                # if a valid frame was returned ...
                if ret:
                    #########
                    # resize the frame is it is larger that 400 in width
                    if frame.shape[1] > 400:
                        frame = cv2.resize(frame, (400, 300))

                    #########
                    # get rgb image from frame
                    rgb_image = self.convertToRGB(frame)

                    #########
                    # load the label-id dictionary if model has not been trained
                    if not self.is_model_trained:
                        self.load_label_id_dict()
                    # if a face or more is registered, then proceed with recognition else skip recogntion
                    # recognize faces if face recognition mode is on else skip face recognition
                    if len(self.label_id_dic.keys()) != 0:
                        # if the model has not been trained already, train it before recognition
                        if not self.is_model_trained:
                            # set loading image
                            self.change_pixmap.emit(
                                QPixmap(resource_path(self.icons_base_dir + os.sep + 'loading_vid.jpg')))
                            # train model
                            self.train_model()
                        # start prediction
                        predicted_faces_frame = self.predict_faces(frame)
                        # get the frames with the recognition return data
                        predicted_faces_rgb = self.convertToRGB(
                            predicted_faces_frame)
                        # convert the bgr image into a pyqt image
                        qimage = QImage(predicted_faces_rgb.data, predicted_faces_rgb.shape[1],
                                        predicted_faces_rgb.shape[0], QImage.Format_RGB888)
                    else:
                        # convert the bgr image into a pyqt image
                        qimage = QImage(
                            rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QImage.Format_RGB888)

                    # create the QPixmap from the QImage
                    qpixmap = QPixmap.fromImage(qimage)
                    # send the pixmap as a signal to the caller (the label in the mdi sub window)
                    self.change_pixmap.emit(qpixmap)
                else:
                    # stop other running processes
                    self.stop_capture()
                    # set the default image for the camera view
                    self.change_pixmap.emit(QPixmap(resource_path(
                        self.icons_base_dir + os.sep + 'default_camera_view.jpg')))
            # when the video stream is stopped, release the camera and its related resources
            self.vid_capture.release()
            # set the default image for the camera view
            self.change_pixmap.emit(QPixmap(resource_path(
                self.icons_base_dir + os.sep + 'default_camera_view.jpg')))
        except:
            self.change_pixmap.emit(
                QPixmap(resource_path(self.icons_base_dir + os.sep + 'conn_error.jpg')))
