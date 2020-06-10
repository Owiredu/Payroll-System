import sys
import os
import cv2
import numpy as np
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QMenu, QAction
from payroll_ui import Ui_PayrollMainWindow
from facial_registration import FaceRegistrationThread
from utils import resource_path
from db_conn import DbConnection
from PyQt5.QtCore import QDate, Qt
from send_email import SendEmail


# define indices for the items on the sidebar menu
DASHBOARD_INDEX = 0
EMPLOYEES_INDEX = 1
ADMIN_INDEX = 2
TAX_INDEX = 3
# define number of columns of employee table
EMPLOYEE_NUMBER_OF_COLUMNS = 12


class Payroll(QMainWindow):
    """
    This is the payroll application
    """

    def __init__(self):
        super().__init__()
        self.ui = Ui_PayrollMainWindow()
        self.ui.setupUi(self)
        # initialize items for all segments of app
        self.sidebar_init()
        self.dashboard_init()
        self.employee_init()
        self.admin_init()
        self.tax_init()

    ######### Sidebar Functions #########

    def sidebar_init(self):
        """
        Initializes sidebar related items
        """
        # connect widgets to their corresponding actions
        self.sidebar_connect_widgets_to_actions()
        # switch to dashboard on startup
        self.ui.sidebar_menu_listwidget.setCurrentRow(DASHBOARD_INDEX)

    def sidebar_connect_widgets_to_actions(self):
        """
        Connects the widgets to their respective actions
        """
        self.ui.sidebar_menu_listwidget.currentItemChanged.connect(
            self.switch_view)

    def switch_view(self):
        """
        Switches view based on sidebar menu item selected
        """
        if (self.ui.sidebar_menu_listwidget.currentRow() == DASHBOARD_INDEX):
            self.switch_to_dashboard()
        elif self.ui.sidebar_menu_listwidget.currentRow() == EMPLOYEES_INDEX:
            self.switch_to_employees()
        elif self.ui.sidebar_menu_listwidget.currentRow() == ADMIN_INDEX:
            self.switch_to_admin()
        else:
            self.switch_to_tax()

    def switch_to_dashboard(self):
        """
        Switches view to dashboard
        """
        self.ui.app_stackedwidget.setCurrentWidget(self.ui.dashboard_page)
        self.dashboard_init()

    def switch_to_employees(self):
        """
        Switches view to employees page
        """
        self.ui.app_stackedwidget.setCurrentWidget(self.ui.employees_page)
        self.clear_email_notification()

    def switch_to_admin(self):
        """
        Switches view to admin page
        """
        self.ui.app_stackedwidget.setCurrentWidget(self.ui.admin_page)
        self.admin_load_registration_data()

    def switch_to_tax(self):
        """
        Switches view to admin page
        """
        self.ui.app_stackedwidget.setCurrentWidget(self.ui.tax_page)

    ######### Dashboard Functions #########

    def dashboard_init(self):
        """
        Initializes all the items in the dashboard
        """
        # load the summary data
        self.dashboard_load_summary_data()
        # load the receipts table
        self.dashboard_load_payments_table()

    def dashboard_connect_widgets_to_actions(self):
        """
        Connects widgets in the tax section to their respective actions
        """
        pass

    def dashboard_load_summary_data(self):
        """
        Loads the data to be placed in the cards on the dashboard
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # select all the employees data
            result = cursor.execute(
                "SELECT * FROM employees ORDER BY EMPLOYEE_ID;")
            data = result.fetchall()
            # get and set the card values
            num_of_employees = 0
            total_monthly_tax = 0.0
            total_gross_salary = 0.0
            total_employee_allowance = 0.0
            total_ssnit = 0.0
            total_net_employee_salary = 0.0
            for row in data:
                # get the gross salary and total allowances
                gross_salary = row[7]
                total_allowance = row[8]
                # find gross salary minus total allowances
                net_salary_with_tax_and_ssnit = gross_salary - total_allowance
                # find the tax
                tax = self.get_tax(net_salary_with_tax_and_ssnit)
                # find the gross salary minus tax and total allowances
                net_salary_with_ssnit = net_salary_with_tax_and_ssnit - tax
                # find the ssnit
                ssnit = 0.145 * (net_salary_with_ssnit)
                # find the net salary
                net_salary = net_salary_with_ssnit - ssnit
                # update totals
                num_of_employees += 1
                total_monthly_tax += tax
                total_gross_salary += gross_salary
                total_employee_allowance += total_allowance
                total_ssnit += ssnit
                total_net_employee_salary += net_salary
                # enhance smoothness
                QApplication.processEvents()
            # display the data on the cards
            self.dashboard_display_card_data(num_of_employees, total_monthly_tax, total_gross_salary,
                                             total_employee_allowance, total_ssnit, total_net_employee_salary)
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(
                self, 'Error', 'Failed to load dashboard data!')

    def dashboard_display_card_data(self, num_of_employees, total_monthly_tax, total_gross_salary,
                                    total_employee_allowance, total_ssnit, total_net_employee_salary):
        """
        Displays the data on the dashboard cards
        """
        self.ui.dashboard_num_of_employees_label.setText(str(num_of_employees))
        self.ui.dashboard_total_monthly_tax_label.setText(
            '{0:.2f}'.format(total_monthly_tax))
        self.ui.dashboard_total_gross_salary_label.setText(
            '{0:.2f}'.format(total_gross_salary))
        self.ui.dashboard_total_allowance_label.setText(
            '{0:.2f}'.format(total_employee_allowance))
        self.ui.dashboard_total_ssnit_label.setText(
            '{0:.2f}'.format(total_ssnit))
        self.ui.dashboard_total_net_salary_label.setText(
            '{0:.2f}'.format(total_net_employee_salary))

    def dashboard_load_payments_table(self):
        """
        Loads the payment receipts table
        """
        self.ui.dashboard_recent_payment_receipts_tablewidget.setRowCount(0)
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # select all the employees data
            result = cursor.execute(
                "SELECT * FROM payment_receipts ORDER BY PAYMENT_ID DESC;")
            data = result.fetchall()
            # insert payment data into the table widget
            for i, row in enumerate(data):
                self.dashboard_add_row_to_tablewidget(i, row)
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(
                self, 'Error', 'Failed to load payments receipts data!')

    def dashboard_add_row_to_tablewidget(self, row_index, row):
        """
        Adds a row to the dashboard tablewidget
        """
        # create an empty row
        self.ui.dashboard_recent_payment_receipts_tablewidget.insertRow(
            row_index)
        # create the items to add to the cells
        item_payment_id = QTableWidgetItem(str(row[0]))
        item_transaction_time = QTableWidgetItem(row[1])
        item_recipients = QTableWidgetItem(row[2])
        item_total_amount = QTableWidgetItem('{0:.2f}'.format(row[3]))
        # make rows uneditable
        item_payment_id.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_transaction_time.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_recipients.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_total_amount.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # insert the items into the cells
        self.ui.dashboard_recent_payment_receipts_tablewidget.setItem(
            row_index, 0, item_payment_id)
        self.ui.dashboard_recent_payment_receipts_tablewidget.setItem(
            row_index, 1, item_transaction_time)
        self.ui.dashboard_recent_payment_receipts_tablewidget.setItem(
            row_index, 2, item_recipients)
        self.ui.dashboard_recent_payment_receipts_tablewidget.setItem(
            row_index, 3, item_total_amount)

    ######### Employee Functions #########

    def employee_init(self):
        """
        Initializes items in the employee panel
        """
        # connect widgets to their respective actions
        self.employee_connect_widgets_to_actions()
        # initialize external classes
        self.employee_initialize_external_classes()
        # connect signals to functions
        self.employee_connect_signals_to_functions()
        # load employee data
        self.employee_load_data()

    def employee_connect_widgets_to_actions(self):
        """
        Connects widgets in the tax section to their respective actions
        """
        self.ui.employee_submit_btn.clicked.connect(
            self.employee_submit_registration)
        self.ui.employee_update_btn.clicked.connect(
            self.employee_update_registration)
        self.ui.employee_reset_btn.clicked.connect(
            self.employee_reset_registration_form)
        self.ui.employee_reload_table_btn.clicked.connect(
            self.employee_reload_data)
        self.ui.employee_edit_btn.clicked.connect(self.employee_edit_data)
        self.ui.employee_remove_btn.clicked.connect(self.employee_remove_data)
        self.ui.employee_search_btn.clicked.connect(self.employee_search_by_id)
        # the pay salary menu button
        self.pay_salary_menu_options = QMenu()
        # create the selected employees option action
        self.pay_selected_employees_action = QAction(
            'Selected Employees', self.ui.employee_pay_salary_toolbtn)
        self.pay_selected_employees_action.triggered.connect(
            lambda: self.employee_pay_selected_employees())
        self.pay_salary_menu_options.addAction(
            self.pay_selected_employees_action)
        # create the all employees option action
        self.pay_all_employees_action = QAction(
            'All Employees', self.ui.employee_pay_salary_toolbtn)
        self.pay_all_employees_action.triggered.connect(
            lambda: self.employee_pay_all_employees())
        self.pay_salary_menu_options.addAction(
            self.pay_all_employees_action)
        # add actions to pay salary button
        self.ui.employee_pay_salary_toolbtn.addActions(
            [self.pay_selected_employees_action, self.pay_all_employees_action])

    def employee_connect_signals_to_functions(self):
        """
        Connects signals to functions
        """
        self.send_mail_thread.progress_message.connect(
            self.email_progress_monitor)
        self.send_mail_thread.error_message.connect(
            self.email_error_monitor)

    def employee_initialize_external_classes(self):
        """
        Initializes external classes
        """
        # initialize send email thread
        self.send_mail_thread = SendEmail()

    def employee_submit_registration(self):
        """
        Submits employee data
        """
        # get the data
        name = self.ui.employee_name_lineedit.text().strip()
        dob = self.ui.employee_dob_datewidget.text().strip()
        sex = self.ui.employee_sex_combobox.currentText().strip()
        department = self.ui.employee_department_combobox.currentText().strip()
        gross_salary = self.ui.employee_salary_lineedit.text().strip()
        phone = self.ui.employee_phone_lineedit.text().strip()
        email = self.ui.employee_email_lineedit.text().strip()
        employee_id = self.ui.employee_id_lineedit.text().strip()
        total_allowance = self.ui.total_allowance_lineedit.text().strip()
        if name != '' and department != '' and gross_salary != '' and phone != '' and email != '' and employee_id != '' and total_allowance != '':
            try:
                db_conn = DbConnection()
                cursor = db_conn.connection.cursor()
                # check if id exists before submitting
                result = cursor.execute(
                    "SELECT COUNT(EMPLOYEE_ID) FROM employees WHERE EMPLOYEE_ID='" + employee_id + "';")
                data = result.fetchone()
                if data[0] == 0:
                    # submit data if all the fields are filled
                    cursor.execute("INSERT INTO employees(EMPLOYEE_ID, NAME, DOB, SEX, DEPARTMENT, PHONE, EMAIL, \
                        GROSS_SALARY, TOTAL_ALLOWANCE) VALUES(?,?,?,?,?,?,?,?,?)",
                                   (employee_id, name, dob, sex, department, phone, email,
                                       float(gross_salary), float(total_allowance)))
                    db_conn.save_changes()
                    # reload the data
                    self.employee_reload_data()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Employee data submitted successfully!')
                else:
                    QMessageBox.critical(
                        self, 'Failure', 'Employee ID already exists! Update instead.')
                # close the cursor and database connection
                cursor.close()
                db_conn.close_connection()
            except:
                # show error message
                QMessageBox.critical(
                    self, 'Error', 'Failed to submit employee data!')
        else:
            QMessageBox.critical(self, 'Failure', 'Fill the form completely! ')

    def employee_update_registration(self):
        """
        Updates the employee registration data
        """
        # get the data
        name = self.ui.employee_name_lineedit.text().strip()
        dob = self.ui.employee_dob_datewidget.text().strip()
        sex = self.ui.employee_sex_combobox.currentText().strip()
        department = self.ui.employee_department_combobox.currentText().strip()
        gross_salary = self.ui.employee_salary_lineedit.text().strip()
        phone = self.ui.employee_phone_lineedit.text().strip()
        email = self.ui.employee_email_lineedit.text().strip()
        employee_id = self.ui.employee_id_lineedit.text().strip()
        total_allowance = self.ui.total_allowance_lineedit.text().strip()
        if name != '' and department != '' and gross_salary != '' and phone != '' and email != '' and employee_id != '' and total_allowance != '':
            try:
                db_conn = DbConnection()
                cursor = db_conn.connection.cursor()
                # check if id exists before submitting
                result = cursor.execute(
                    "SELECT COUNT(EMPLOYEE_ID) FROM employees WHERE EMPLOYEE_ID='" + employee_id + "';")
                data = result.fetchone()
                if data[0] == 1:
                    # update data if all the fields are filled
                    cursor.execute("UPDATE employees SET NAME=?, DOB=?, SEX=?, DEPARTMENT=?, PHONE=?, \
                            EMAIL=?, GROSS_SALARY=?, TOTAL_ALLOWANCE=? WHERE EMPLOYEE_ID='" + employee_id + "';",
                                   (name, dob, sex, department, phone, email, float(
                                       gross_salary), float(total_allowance)))
                    db_conn.save_changes()
                    # reload the data
                    self.employee_reload_data()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Employee data updated successfully!')
                else:
                    QMessageBox.critical(
                        self, 'Failure', 'Employee ID does not exist! Submit instead.')
                # close the cursor and database connection
                cursor.close()
                db_conn.close_connection()
            except:
                # show error message
                QMessageBox.critical(
                    self, 'Error', 'Failed to update employee data!')
        else:
            QMessageBox.critical(self, 'Failure', 'Fill the form completely! ')

    def employee_reset_registration_form(self):
        """
        Resets the employee registration form
        """
        self.ui.employee_name_lineedit.clear()
        self.ui.employee_sex_combobox.setCurrentIndex(0)
        self.ui.employee_department_combobox.setCurrentIndex(0)
        self.ui.employee_salary_lineedit.clear()
        self.ui.employee_phone_lineedit.clear()
        self.ui.employee_email_lineedit.clear()
        self.ui.employee_id_lineedit.clear()
        self.ui.total_allowance_lineedit.setText('0.00')

    def employee_load_data(self):
        """
        Loads the employee data into the tablewidget
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # select all the employees data
            result = cursor.execute(
                "SELECT * FROM employees ORDER BY EMPLOYEE_ID;")
            data = result.fetchall()
            # insert employee data into the table widget
            for i, row in enumerate(data):
                self.employee_add_row_to_tablewidget(i, row)
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(
                self, 'Error', 'Failed to load employees data!')

    def get_tax(self, net_salary_with_tax):
        """
        Calculates and returns the tax, given the net salary
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # select all the tax data
            result = cursor.execute(
                "SELECT * FROM monthly_income_tax_rates ORDER BY ROW_ID;")
            data = result.fetchall()
            # split the salary into chunks according to the taxation table
            total_tax = 0.0
            for tax_row in data:
                taxable_amount = float(tax_row[0].split(" ")[1].strip())
                salary_left = net_salary_with_tax - tax_row[3]
                if salary_left < taxable_amount or tax_row[0].split(" ")[0].strip().lower() == 'exceeding':
                    total_tax += (tax_row[1] / 100) * \
                        (net_salary_with_tax - (tax_row[3] - taxable_amount))
                    break
                else:
                    total_tax = tax_row[-2]
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to calculate tax!')
        # return the total tax
        return total_tax

    def employee_add_row_to_tablewidget(self, row_index, row):
        """
        Adds a row to the employee tablewidget
        """
        # create an empty row
        self.ui.employee_data_tablewidget.insertRow(row_index)
        # create the items to add to the cells
        item_employee_id = QTableWidgetItem(row[0])
        item_name = QTableWidgetItem(row[1])
        item_dob = QTableWidgetItem(row[2])
        item_sex = QTableWidgetItem(row[3])
        item_department = QTableWidgetItem(row[4])
        item_phone = QTableWidgetItem(row[5])
        item_email = QTableWidgetItem(row[6])
        ### START OF SALARY CALCULATIONS ###
        gross_salary = row[7]
        total_allowance = row[8]
        # find gross salary minus total allowances
        net_salary_with_tax_and_ssnit = gross_salary - total_allowance
        # find the tax
        tax = self.get_tax(net_salary_with_tax_and_ssnit)
        # find the gross salary minus tax and total allowances
        net_salary_with_ssnit = net_salary_with_tax_and_ssnit - tax
        # find the ssnit
        ssnit = 0.145 * (net_salary_with_ssnit)
        # find the net salary
        net_salary = net_salary_with_ssnit - ssnit
        ### END OF SALARY CALCULATIONS ###
        item_gross_salary = QTableWidgetItem(
            '{0:.2f}'.format(gross_salary))
        item_ssnit = QTableWidgetItem('{0:.2f}'.format(ssnit))
        item_net_salary = QTableWidgetItem(
            '{0:.2f}'.format(net_salary))
        item_total_allowance = QTableWidgetItem(
            '{0:.2f}'.format(total_allowance))
        item_tax = QTableWidgetItem('{0:.2f}'.format(tax))
        # make rows uneditable
        item_employee_id.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_name.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_dob.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_sex.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_department.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_phone.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_email.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_gross_salary.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_ssnit.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_net_salary.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_total_allowance.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item_tax.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # insert the items into the cells
        self.ui.employee_data_tablewidget.setItem(
            row_index, 0, item_employee_id)
        self.ui.employee_data_tablewidget.setItem(row_index, 1, item_name)
        self.ui.employee_data_tablewidget.setItem(row_index, 2, item_dob)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 3, item_sex)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 4, item_phone)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 5, item_email)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 6, item_department)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 7, item_gross_salary)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 8, item_net_salary)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 9, item_tax)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 10, item_ssnit)
        self.ui.employee_data_tablewidget.setItem(
            row_index, 11, item_total_allowance)

    def employee_search_by_id(self):
        """
        Searches employee by id
        """
        # get the search term
        search_term = self.ui.employee_search_lineedit.text().strip()
        # perform search
        if search_term != "":
            try:
                db_conn = DbConnection()
                cursor = db_conn.connection.cursor()
                # get the admin data
                result = cursor.execute(
                    "SELECT * FROM employees WHERE EMPLOYEE_ID LIKE'%" + search_term + "%';")
                data = result.fetchall()
                if data:
                    # remove all the rows from table
                    self.ui.employee_data_tablewidget.setRowCount(0)
                    # insert search results into the table widget
                    for i, row in enumerate(data):
                        self.employee_add_row_to_tablewidget(i, row)
                    # close the cursor and database connection
                    cursor.close()
                    db_conn.close_connection()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Search complete. Match(es) found!')
                else:
                    # show no match found message
                    QMessageBox.information(
                        self, 'Success', 'Search complete. No match(es) found!')
            except:
                # show error message
                QMessageBox.critical(
                    self, 'Error', 'No match found for "' + search_term + '"')

    def employee_reload_data(self):
        """
        Reloads the employee data into the tablewidget
        """
        # remove all the current rows from the tablewidget
        self.ui.employee_data_tablewidget.setRowCount(0)
        # load the employee data into the table
        self.employee_load_data()

    def employee_edit_data(self):
        """
        Loads employee data into the form for editing or updating
        """
        # get the index of the selected row
        selected_row = self.ui.employee_data_tablewidget.currentRow()
        # load row data into the form
        if selected_row != -1:
            self.ui.employee_id_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 0).text())
            self.ui.employee_name_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 1).text())
            day, month, year = self.ui.employee_data_tablewidget.item(
                selected_row, 2).text().split('/')
            self.ui.employee_dob_datewidget.setDate(
                QDate(int(year), int(month), int(day)))
            self.ui.employee_sex_combobox.setCurrentText(
                self.ui.employee_data_tablewidget.item(selected_row, 3).text())
            self.ui.employee_phone_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 4).text())
            self.ui.employee_email_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 5).text())
            self.ui.employee_department_combobox.setCurrentText(
                self.ui.employee_data_tablewidget.item(selected_row, 6).text())
            self.ui.employee_salary_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 7).text())
            self.ui.total_allowance_lineedit.setText(
                self.ui.employee_data_tablewidget.item(selected_row, 11).text())
        else:
            QMessageBox.information(
                self, 'Error', 'Select a single row to edit!')

    def employee_remove_data(self):
        """
        Delete an employee data from the database
        """
        # get the index of the selected row
        selected_row = self.ui.employee_data_tablewidget.currentRow()
        # load row data into the form
        if selected_row != -1:
            # get the selected employee's id
            employee_id = self.ui.employee_data_tablewidget.item(
                selected_row, 0).text()
            # delete selected employee's data
            try:
                # confirm deletion
                ok_pressed = QMessageBox.question(
                    self, 'Confirm Deletion', 'Delete employee with id = ' + employee_id)
                # perform deletion on approval
                if ok_pressed == QMessageBox.Yes:
                    db_conn = DbConnection()
                    cursor = db_conn.connection.cursor()
                    # delete all the previous tax data
                    cursor.execute(
                        "DELETE FROM employees WHERE EMPLOYEE_ID='" + employee_id + "';")
                    # save changes
                    db_conn.save_changes()
                    # close the cursor and database connection
                    cursor.close()
                    db_conn.close_connection()
                    # reload the data
                    self.employee_reload_data()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Successfully removed employee with id = ' + employee_id)
            except:
                # show error message
                QMessageBox.critical(
                    self, 'Error', 'Failed to remove employee!')
        else:
            QMessageBox.information(
                self, 'Error', 'Select a single employee to remove!')

    def employee_pay_selected_employees(self):
        """
        Pays selected employees
        """
        # get the emails from the selected rows and total net salaries paid
        time_now = time.localtime()
        transaction_time = f'{time_now.tm_mday}/{time_now.tm_mon}/{time_now.tm_year} {time_now.tm_hour}:{time_now.tm_min}:{time_now.tm_sec}'
        selected_row_emails = []
        selected_row_ids = []
        total_net_salaries = 0.0
        selected_items = self.ui.employee_data_tablewidget.selectedItems()
        if selected_items:
            for col, item in enumerate(selected_items):
                if col % EMPLOYEE_NUMBER_OF_COLUMNS == 0:
                    selected_row_ids.append(item.text())
                if col % EMPLOYEE_NUMBER_OF_COLUMNS == 5:
                    selected_row_emails.append(item.text())
                if col % EMPLOYEE_NUMBER_OF_COLUMNS == 8:
                    total_net_salaries += float(item.text())
            # create the recipient ids and emails string
            recipient_ids = ";".join(selected_row_ids)
            recipient_emails = ";".join(selected_row_emails)
            # submit transaction details to the database
            try:
                # confirm deletion
                ok_pressed = QMessageBox.question(
                    self, 'Confirm Payment', 'Do you wish to proceed with payment for selected employees?')
                # perform deletion on approval
                if ok_pressed == QMessageBox.Yes:
                    db_conn = DbConnection()
                    cursor = db_conn.connection.cursor()
                    # delete all the previous tax data
                    cursor.execute("INSERT INTO payment_receipts(TRANSACTION_TIME, RECIPIENTS, TOTAL_AMOUNT) VALUES(?,?,?)",
                                   (transaction_time, recipient_ids, float(total_net_salaries)))
                    # save changes
                    db_conn.save_changes()
                    # close the cursor and database connection
                    cursor.close()
                    db_conn.close_connection()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Successfully completed payment(s)!')
            except:
                # show error message
                QMessageBox.critical(self, 'Error', 'Payment failed!')
            # send the email to the recipients
            self.send_mail_thread.set_email_info(recipient_emails)
            self.send_mail_thread.start()
        else:
            QMessageBox.information(
                self, 'Failure', 'Select at least one row to make payment!')

    def employee_pay_all_employees(self):
        """
        Pays all employees
        """
        # get the emails from the selected rows and total net salaries paid
        time_now = time.localtime()
        transaction_time = f'{time_now.tm_mday}/{time_now.tm_mon}/{time_now.tm_year} {time_now.tm_hour}:{time_now.tm_min}:{time_now.tm_sec}'
        selected_row_emails = []
        selected_row_ids = []
        total_net_salaries = 0.0
        # submit transaction details to the database
        try:
            # confirm deletion
            ok_pressed = QMessageBox.question(
                self, 'Confirm Payment', 'Do you wish to proceed with payment for all employees?')
            # perform deletion on approval
            if ok_pressed == QMessageBox.Yes:
                db_conn = DbConnection()
                cursor = db_conn.connection.cursor()
                # select all the employee data
                result = cursor.execute("SELECT * FROM employees")
                data = result.fetchall()
                for row in data:
                    # accummulate net salaries
                    gross_salary = row[7]
                    total_allowance = row[8]
                    tax = self.get_tax(gross_salary)
                    ssnit = 0.145 * (gross_salary - total_allowance - tax)
                    net_salary = gross_salary - ssnit
                    total_net_salaries += net_salary
                    # get emails
                    selected_row_emails.append(row[6])
                    # get ids
                    selected_row_ids.append(row[0])
                # join emails and ids
                recipient_ids = ";".join(selected_row_ids)
                recipient_emails = ";".join(selected_row_emails)
                # # delete all the previous tax data
                cursor.execute("INSERT INTO payment_receipts(TRANSACTION_TIME, RECIPIENTS, TOTAL_AMOUNT) VALUES(?,?,?)",
                               (transaction_time, recipient_ids, float(total_net_salaries)))
                # save changes
                db_conn.save_changes()
                # close the cursor and database connection
                cursor.close()
                db_conn.close_connection()
                # show success message
                QMessageBox.information(
                    self, 'Success', 'Successfully completed payment(s)!')
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Payment failed!')
        # send the email to the recipients
        self.send_mail_thread.set_email_info(recipient_emails)
        self.send_mail_thread.start()

    def email_progress_monitor(self, msg):
        """
        Monitors the progress and success of the email
        """
        if msg.startswith('Sending'):
            self.ui.email_notif_label.setText(msg)
        else:
            self.ui.email_notif_label.setStyleSheet(
                'background-color: rgb(99, 255, 117);')
            self.ui.email_notif_label.setText(
                'Notification sent successfully!')

    def email_error_monitor(self, msg):
        """
        Monitors the errors encountered in sending the email
        """
        self.ui.email_notif_label.setStyleSheet(
            'background-color: rgb(255, 128, 119);')
        self.ui.email_notif_label.setText('Failed to send email notification!')

    def clear_email_notification(self):
        self.ui.email_notif_label.setStyleSheet(
            'background-color: rgb(193, 193, 193);')
        self.ui.email_notif_label.setText('')

    ######### Admin Functions #########

    def admin_init(self):
        """
        Initializes items the admin panel
        """
        self.subject_id = 'admin'
        self.cap_source = 0
        self.training_data_dir = 'src\\..//training_data'
        # connect widgets to their corresponding actions
        self.admin_connect_widgets_to_actions()
        # initialze the face recognizer for training the model
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()

    def admin_connect_widgets_to_actions(self):
        """
        Connects widgets in the admin section to their respective actions
        """
        self.ui.admin_reset_button.clicked.connect(
            self.admin_reset_registration)
        self.ui.admin_submit_btn.clicked.connect(
            self.admin_submit_registration)
        self.ui.admin_update_btn.clicked.connect(
            self.admin_update_registration)
        self.ui.register_face_btn.clicked.connect(self.registration)
        self.ui.train_model_btn.clicked.connect(self.train_model)

    def admin_load_registration_data(self):
        """
        Loads the admin registration data
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # get the admin data
            result = cursor.execute("SELECT * FROM admin_details;")
            data = result.fetchone()
            if data:
                username = data[0]
                password = data[1]
                full_name = data[2]
                date = data[3]
                sex = data[4]
                phone = data[5]
                email = data[6]
                # set the admin data their respective fields
                self.ui.admin_name_lineedit.setText(full_name)
                day, month, year = date.split('/')
                self.ui.admin_dob_datewidget.setDate(
                    QDate(int(year), int(month), int(day)))
                self.ui.admin_sex_combobox.setCurrentIndex(
                    0 if sex[0] == 'M' else 1)
                self.ui.admin_phone_lineedit.setText(phone)
                self.ui.admin_email_lineedit.setText(email)
                self.ui.admin_username_lineedit.setText(username)
                self.ui.admin_password_lineedit.setText(password)
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to load admin data!')

    def admin_submit_registration(self):
        """
        Submits the admin registration
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # check if admin data exists before submitting
            result = cursor.execute(
                "SELECT COUNT(USERNAME) FROM admin_details;")
            data = result.fetchone()
            if data[0] == 0:
                # get the data
                username = self.ui.admin_username_lineedit.text().strip()
                password = self.ui.admin_password_lineedit.text().strip()
                full_name = self.ui.admin_name_lineedit.text().strip()
                dob = self.ui.admin_dob_datewidget.text().strip()
                sex = self.ui.admin_sex_combobox.currentText().strip()
                phone = self.ui.admin_phone_lineedit.text().strip()
                email = self.ui.admin_email_lineedit.text().strip()
                if username != '' and password != '' and full_name != '' and phone != '' and email != '':
                    # submit data if all the fields are filled
                    cursor.execute("INSERT INTO admin_details(USERNAME, PASSWORD, FULL_NAME, DOB, SEX, PHONE, EMAIL) VALUES(?,?,?,?,?,?,?)",
                                   (username, password, full_name, dob, sex, phone, email))
                    db_conn.save_changes()
                    # show success message
                    QMessageBox.information(
                        self, 'Success', 'Admin data submitted successfully!')
                else:
                    QMessageBox.critical(
                        self, 'Failure', 'Fill the form completely!')
            else:
                QMessageBox.critical(
                    self, 'Failure', 'Admin data already exists! Update instead.')
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to submit admin data!')

    def admin_update_registration(self):
        """
        Updates the admin registration
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # update the data
            result = cursor.execute(
                "SELECT USERNAME FROM admin_details;")
            data = result.fetchone()
            prev_username = data[0]
            if prev_username:
                # get the data
                username = self.ui.admin_username_lineedit.text().strip()
                password = self.ui.admin_password_lineedit.text().strip()
                full_name = self.ui.admin_name_lineedit.text().strip()
                dob = self.ui.admin_dob_datewidget.text().strip()
                sex = self.ui.admin_sex_combobox.currentText().strip()
                phone = self.ui.admin_phone_lineedit.text().strip()
                email = self.ui.admin_email_lineedit.text().strip()
                if username != '' and password != '' and full_name != '' and phone != '' and email != '':
                    # update data if all the fields are filled
                    cursor.execute("UPDATE admin_details SET USERNAME=?, PASSWORD=?, FULL_NAME=?, DOB=?, SEX=?, PHONE=?, EMAIL=? WHERE USERNAME=?",
                                   (username, password, full_name, dob, sex, phone, email, prev_username))
                    db_conn.save_changes()
                    QMessageBox.information(
                        self, 'Success', 'Admin data updated successfully!')
                else:
                    QMessageBox.critical(
                        self, 'Failure', 'Fill the form completely!')
            else:
                QMessageBox.critical(
                    self, 'Failure', 'No data available to update! Submit instead.')
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to update admin data!')

    def admin_reset_registration(self):
        """
        Reset the admin registration
        """
        self.admin_load_registration_data()
        QMessageBox.information(self, 'Success', 'Admin data reset completed!')

    def registration(self):
        """
        This method calls the capture face thread to register the face
        """
        # initialize the face capturing thread
        self.face_registration_thread = FaceRegistrationThread(
            self.subject_id, self.cap_source)
        # connect the face capturing label to recieve the images from the thread
        self.face_registration_thread.change_pixmap.connect(
            self.ui.video_capture_label.setPixmap)
        # start thread
        self.face_registration_thread.start()
        self.face_registration_thread.start_capture()

    def train_model(self):
        """
        This method trains the facial recognition model and saves it to a file
        """
        try:
            # set the train button text and face capture groupbox title to training
            self.ui.train_model_btn.setText('Training...')
            QApplication.processEvents()
            # create list to hold the faces data and corresponding labels
            faces = []
            labels = []
            # get the faces and their corresponding labels
            for subject_dir in os.listdir(resource_path(self.training_data_dir)):
                if subject_dir.startswith('s'):
                    for img_file_name in os.listdir(resource_path(self.training_data_dir + os.sep + subject_dir)):
                        face = cv2.imread(resource_path(
                            self.training_data_dir + os.sep + subject_dir + os.sep + img_file_name))
                        face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
                        faces.append(face)
                        labels.append(int(subject_dir.replace('s', '')))
            # train the recognizer
            self.face_recognizer.train(faces, np.array(labels))
            # save the trained model
            self.face_recognizer.save(resource_path(
                self.training_data_dir + os.sep + 'trained_model.xml'))
            # set the train button text and face capture groupbox title to default
            self.ui.train_model_btn.setText('Train Model')
            # show success notification
            QMessageBox.information(
                self, 'Training Success', 'Successfully trained facial recognition model')
        except:
            # set the train button text and face capture groupbox title to default
            self.ui.train_model_btn.setText('Train Model')
            # show failure notification
            QMessageBox.critical(
                self, 'Training Alert', 'Register at least one face before training the model')

    ######### Tax Functions #########

    def tax_init(self):
        """
        Initializes items in the tax panel
        """
        # load the tax data into the table
        self.tax_load_data()
        # connect widgets to their respective actions
        self.tax_connect_widgets_to_actions()

    def tax_connect_widgets_to_actions(self):
        """
        Connects widgets in the tax section to their respective actions
        """
        self.ui.save_tax_btn.clicked.connect(self.tax_save_data)
        self.ui.revert_tax_btn.clicked.connect(self.tax_revert_data)

    def tax_load_data(self):
        """
        Loads the tax data in the table
        """
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # select all the tax data
            result = cursor.execute(
                "SELECT * FROM monthly_income_tax_rates ORDER BY ROW_ID;")
            data = result.fetchall()
            # insert tax data into the table widget
            for i, row in enumerate(data):
                # create an empty row
                self.ui.tax_tablewidget.insertRow(i)
                # create the items to add to the cells
                item_chargeable_income = QTableWidgetItem(row[0].upper())
                item_rate = QTableWidgetItem('{0:.2f}'.format(row[1]))
                item_tax = QTableWidgetItem('{0:.2f}'.format(row[2]))
                item_cummulative_chargeable_income = QTableWidgetItem(
                    '{0:.2f}'.format(row[3]))
                item_cummulative_tax = QTableWidgetItem(
                    '{0:.2f}'.format(row[4]))
                # insert the items into the cells
                self.ui.tax_tablewidget.setItem(i, 0, item_chargeable_income)
                self.ui.tax_tablewidget.setItem(i, 1, item_rate)
                self.ui.tax_tablewidget.setItem(i, 2, item_tax)
                self.ui.tax_tablewidget.setItem(
                    i, 3, item_cummulative_chargeable_income)
                self.ui.tax_tablewidget.setItem(i, 4, item_cummulative_tax)
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to load tax data!')

    def tax_save_data(self):
        """
        Saves the tax data to the database
        """
        # get all the tax data in the tablewidget
        new_tax_data = []
        for r in range(self.ui.tax_tablewidget.rowCount()):
            row_data = []
            for c in range(self.ui.tax_tablewidget.columnCount()):
                cell_data = self.ui.tax_tablewidget.item(r, c).text()
                if c != 0:
                    cell_data = float(cell_data)
                row_data.append(cell_data)
            # insert the row id at the end of the row data
            row_data.insert(len(row_data), r)
            new_tax_data.append(tuple(row_data))
        # update the tax data in the database
        try:
            db_conn = DbConnection()
            cursor = db_conn.connection.cursor()
            # delete all the previous tax data
            cursor.execute('DELETE FROM monthly_income_tax_rates')
            # save changes
            db_conn.save_changes()
            # insert the new tax data
            cursor.executemany(
                'INSERT INTO monthly_income_tax_rates VALUES(?,?,?,?,?,?)', new_tax_data)
            # save changes
            db_conn.save_changes()
            # close the cursor and database connection
            cursor.close()
            db_conn.close_connection()
            # reload tax data
            self.tax_reload()
            # show success message
            QMessageBox.information(
                self, 'Success', 'Successfully saved the new tax data!')
        except:
            # show error message
            QMessageBox.critical(self, 'Error', 'Failed to update tax data!')

    def tax_revert_data(self):
        """
        Restore most recently saved taxed data
        """
        # remove all the current rows from the tablewidget
        self.ui.tax_tablewidget.setRowCount(0)
        # load the tax data into the table
        self.tax_load_data()
        # show success message
        QMessageBox.information(
            self, "Success", "Successfully reverted changes!")

    def tax_reload(self):
        """
        Reloads tax data
        """
        # remove all the current rows from the tablewidget
        self.ui.tax_tablewidget.setRowCount(0)
        # load the tax data into the table
        self.tax_load_data()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Payroll()
    window.showMaximized()
    sys.exit(app.exec_())
