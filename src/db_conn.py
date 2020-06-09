import sys
import os
import sqlite3
from utils import resource_path


class DbConnection():
    """
    This class handles database connection and creation of tables
    """

    def __init__(self):
        # connect to sqlite database
        self.connection = sqlite3.connect(
            resource_path('src\\..//dbs//payroll_db.sqlite'))

    def save_changes(self):
        """
        Saves changes made to the database
        """
        self.connection.commit()

    def close_connection(self):
        """
        This method closes the database connection
        """
        self.connection.close()
