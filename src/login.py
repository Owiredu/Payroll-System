import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from login_ui import Ui_LoginWindow
from facial_recog import FacialRecognitionThread
from PyQt5.QtGui import QPixmap
from utils import resource_path
from db_conn import DbConnection
from payroll import Payroll


class Login(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)
        # define constants
        self.camera_id = 0
        self.icons_base_dir = 'src\\..//icons'
        # instantiate the facial recognition thread
        self.facial_recog_thread = FacialRecognitionThread(self.camera_id)
        # set default image
        self.set_default_video_image()
        # connect functions and widgets to events from other threads
        self.connect_functions_and_events()
        # connect widgets to actions
        self.connect_widgets_and_actions()
        # start the video capture
        # self.start_facial_recognition()
        # set login to manually login by default
        self.toggle_login_type()

    def connect_widgets_and_actions(self):
        """
        Connects widgets to their corresponding actions
        """
        self.ui.login_type_checkbox.toggled.connect(self.toggle_login_type)
        self.ui.login_btn.clicked.connect(self.manual_login_to_app)
        self.ui.username_field.returnPressed.connect(self.manual_login_to_app)
        self.ui.password_field.returnPressed.connect(self.manual_login_to_app)
        self.ui.cancel_btn.clicked.connect(self.cancel_login)

    def connect_functions_and_events(self):
        """
        Connects functions to events from another thread
        """
        # set the image returned by the signal to the label
        self.facial_recog_thread.change_pixmap.connect(
            self.ui.video_label.setPixmap)
        # get the recognized if from the facial recogntion thread
        self.facial_recog_thread.recognized_id.connect(self.get_recognized_id)

    def toggle_login_type(self):
        """
        Toggles between manual login and facial login
        """
        if self.ui.login_type_checkbox.isChecked():
            self.turn_on_manual_login()
        else:
            self.turn_off_manual_login()
        QApplication.processEvents()

    def turn_off_manual_login(self):
        """
        Turns off manual login
        """
        # start facial recognition
        self.start_facial_recognition()
        # disable the form inputs
        self.ui.username_field.setDisabled(True)
        self.ui.password_field.setDisabled(True)
        self.ui.login_btn.setDisabled(True)
        self.ui.cancel_btn.setDisabled(True)

    def turn_on_manual_login(self):
        """
        Turns off manual login
        """
        # stop facial recognition
        self.stop_facial_recognition()
        # enable the form inputs
        self.ui.username_field.setEnabled(True)
        self.ui.password_field.setEnabled(True)
        self.ui.login_btn.setEnabled(True)
        self.ui.cancel_btn.setEnabled(True)

    def set_default_video_image(self):
        """
        Sets the default image for the video display
        """
        self.ui.video_label.setPixmap(
            QPixmap(resource_path(self.icons_base_dir + os.sep + 'default_camera_view.jpg')))

    def start_facial_recognition(self):
        """
        Starts the facial recognition
        """
        self.facial_recog_thread.start_capture()
        self.facial_recog_thread.start()

    def stop_facial_recognition(self):
        """
        Stops the facial recognition
        """
        self.facial_recog_thread.stop_capture()

    def get_recognized_id(self, recognized_id):
        """
        Gets the recognized ID from the facial recognition thread
        """
        # login to the main window
        self.facial_login_to_app(recognized_id)

    def facial_login_to_app(self, username=None):
        """
        Login to the Payroll main window
        """
        # stop facial recognition
        # turn of manual login again
        self.ui.login_type_checkbox.setChecked(True)
        # open payroll main window
        self.payroll_main_window = Payroll()
        self.payroll_main_window.showMaximized()
        self.hide()

    def manual_login_to_app(self):
        """
        Logs in manually to the app
        """
        # get the user id and password
        username = self.ui.username_field.text()
        password = self.ui.password_field.text()
        # verify login
        if username.strip() != "" and password.strip() != "":
            try:
                db_conn = DbConnection()
                cursor = db_conn.connection.cursor()
                # verify login
                result = cursor.execute(
                    "SELECT USERNAME, PASSWORD FROM admin_details WHERE USERNAME='" + username + "' AND PASSWORD='" + password + "';")
                data = result.fetchone()
                # close the cursor and database connection
                cursor.close()
                db_conn.close_connection()
                # open payroll main window when data is found
                if data:
                    self.payroll_main_window = Payroll()
                    self.payroll_main_window.showMaximized()
                    self.hide()
                else:
                    QMessageBox.information(
                        self, "Failure", "Wrong credentials!")
            except:
                # show error message
                QMessageBox.critical(self, 'Error', 'Login failed!')

    def cancel_login(self):
        """
        Cancels login
        """
        self.close()

    def closeEvent(self, event):
        """
        Handle close events
        """
        # stop video capture if it is still running
        if self.facial_recog_thread.video_playing:
            self.stop_facial_recognition()
        # accept to close window
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Login()
    window.show()
    sys.exit(app.exec_())
