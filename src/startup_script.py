import os
import sys
from PyQt5.QtWidgets import QApplication, QStyleFactory
from login import Login
from payroll import Payroll
from utils import resource_path
from db_conn import DbConnection


if __name__ == "__main__":
    # set the GUI style
    QApplication.setStyle(QStyleFactory.create('Fusion'))
    # start the application
    app = QApplication(sys.argv)
    # check if an admin password has been set.
    # if it is set, open login else open main window
    try:
        # connect to database and get cursor
        db_conn = DbConnection()
        cursor = db_conn.connection.cursor()
        # check if any login info exists
        result = cursor.execute("SELECT COUNT(USERNAME) FROM admin_details;")
        data = result.fetchone()
        # close the cursor and database connection
        cursor.close()
        db_conn.close_connection()
        # open login page in login info is found
        if data[0] != 0:
            login_window = Login()
            login_window.show()
        else:
            # if not login info exists, open payroll main window
            payroll_main_window = Payroll()
            payroll_main_window.showMaximized()
    except:
        pass
    # exit app
    sys.exit(app.exec_())
