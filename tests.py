"""
Unit details :  CITS5501 Test and Automation Project
Due Date:       18/05/2018
Student :       Damon van der Linde
Student ID :    21506136
Description :   Provided 3 unittests and 3 browser-based test
                to examine the behaviour and functionality of
                the provided CITS5501 To Do Application

                Also submit a report covering the various aspects
                such as test descriptions, rationale, plans for 
                extending tests as well as any bugs uncovered
                (See report for Acronyms and Abbreviations)
"""

from django.test import TestCase, LiveServerTestCase
from django.test.client import RequestFactory
from django.db import models
from django.contrib.auth.models import Group, User
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait 
from selenium import webdriver
import time, platform, datetime, todo.models, todo.views
from management.commands.reset import Command as setup

LOCAL_HOST = 'http://localhost:8081/'

class CITS5501BlankUnitTestCase(TestCase):
    fixtures = ['users.json']

    def setUp(self):
        # Initialise a user
        self.test_user_one_name = "testUser1"
        self.test_user = User.objects.create_user(self.test_user_one_name, "testUser1@test.com", self.test_user_one_name)
        self.request_factory = RequestFactory()
        
        # Initialise a test list
        group_name = "Test Group"
        list_name = "Test List"
        self.group = Group(name=group_name)
        self.group.save()
        self.list1 = todo.models.TaskList.objects.create(name = list_name, group = self.group)

        # Initialise a test task with an overdue status
        self.task_title_overdue = "Test task overdue"
        self.task1 = todo.models.Task.objects.create(title = self.task_title_overdue, task_list = self.list1,
        due_date = "2000-12-03", priority = 1, created_by = self.test_user)

        # Initialise a test task with a non-overdue status
        self.task_title_nonoverdue = "Test task non-overdue"
        self.task2 = todo.models.Task.objects.create(title = self.task_title_nonoverdue, task_list = self.list1,
        due_date = "9999-12-03", priority = 1, created_by = self.test_user)

        # Create a comment on the above task and define snippet paramaters
        self.comment_text = "Hello I am a test comment that goes beyond 35 characters"
        self.comment = todo.models.Comment.objects.create(author = self.test_user, task = self.task1, body = self.comment_text)
        self.snippet_length = 35

    def tearDown(self):
        self.list1.delete()
        self.group.delete()
        self.comment.delete()

    def test_due_date_overdue(self):
        """ 
            Unit Test #1 (ODTS)

            Procedure:
            1. Retrieve the test task which has a due date sometime in the past
            2. Call the overdue_status method on it 
            3. Retrieve the test task that has due date sometime in the future
            4. Call the overdue statys method on it
            - - - - - - - -
            Verification:
            5. Check that the method returned true for the overdue task
            6. Check that the method returned false for the non overdue task

        """
        task_overdue = todo.models.Task.objects.get(title = self.task_title_overdue)
        task_overdue_status = task_overdue.overdue_status()
        task_non_overdue = todo.models.Task.objects.get(title = self.task_title_nonoverdue)
        task_non_overdue_status = task_non_overdue.overdue_status()
        self.assertEquals(task_overdue_status, True)
        self.assertEquals(task_non_overdue_status, False)

    def test_auto_set_task_complete_date(self):
        """
            Unit Test #2 (SCDA)

            Procedure:
            1. Retrieve test task 
            2. Mark test task as complete
            3. Call the save method within models class
            - - - - - - - -
            Verification:
            4. Check that the completed date matches the current system date (dd/mm/yyyy only)
        """
        task_to_mark_complete = todo.models.Task.objects.get(title = self.task_title_overdue)
        task_to_mark_complete.completed = True
        task_to_mark_complete.save()
        self.assertEquals(task_to_mark_complete.completed_date.date(), datetime.datetime.now().date())

    def test_comment_snippet(self):
        """
            Unit Test #3 (CSF)

            Procedure:
            1. Retrieve comment belonging to test user 
            2. Call the snippet function as that is used by the admin user 
            - - - - - - - -
            Verification:
            3. Ensure that the format produced by the snippet method is correct
            Eg. Author_Name - Code snippet up to 35 chars followed by ...

        """
        comment = todo.models.Comment.objects.get(author = self.test_user)
        comment_snippet = comment.snippet()
        self.assertEquals(comment_snippet, self.test_user_one_name + " - " + comment.body[:self.snippet_length]+ "...")

class CITS5501SeleniumCase(LiveServerTestCase):
    fixtures = ['users.json']

    def setUp(self): 
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.close()

    def set_up_random_lists_tasks(self):
        setup.handle(self)

    def perform_login(self, isAdmin):
        # Load login page
        self.browser.implicitly_wait(10)
        self.browser.get('%s%s' % (self.live_server_url, '/login/'))
        
        # Enter credentials based on requested privilege level
        if (isAdmin == True):
            username_box = self.browser.find_element_by_name("username")
            username_box.send_keys("staffer")
            password_box = self.browser.find_element_by_name("password")
            password_box.send_keys("staffer")
        else:
            username_box = self.browser.find_element_by_name("username")
            username_box.send_keys("user1")
            password_box = self.browser.find_element_by_name("password")
            password_box.send_keys("user1")

        # Submit form
        self.browser.find_element_by_css_selector("button.btn-primary").click()

    def perform_logout(self):
        self.browser.find_element_by_css_selector(
            "a[href='/logout/']").click()

    def perform_primary_button_press(self):
        self.browser.find_element_by_css_selector(".btn-primary").click()

    def add_task_to_created_list(self, task_name, task_description, task_due, os_name):
        """
        	Helper method for Selenium Test Scenario #1
        	
        	Used to add a task to the list corresponding to the page which the user 
        	is located on. 

        	:param task_name: Name of the task
        	:param task_description: Details about the task
        	:param task_due: When the task is expected to be completed
        	:param os_name: The name of the operating system the code is being executed on
        """

        # Click the add task button
        self.browser.find_element_by_id("AddTaskButton").click()

        # Wait till task title box is visible
        wait = WebDriverWait(self.browser, 10)
        task_title_box = wait.until(EC.visibility_of_element_located((By.ID, "id_title")))
        
        # Fill in the Task title
        task_title_box.send_keys(task_name)

        # Wait till task description box is visbile
        task_description_box = wait.until(EC.visibility_of_element_located((By.ID, "id_note")))
        
        # Fill in the Task description
        task_description_box.send_keys(task_description)

        # Set task due date
        task_due_date = wait.until(EC.visibility_of_element_located((By.ID, "id_due_date")))
        
        # Seperate the date into dd, mm and yy
        dateInfo = task_due.split("-")

        # Check the OS and apply appropriate interaction method for the date element
        if(os_name == "Windows"):
            # Windows Method
            task_due_win_p1 = dateInfo[0] + dateInfo[1]
            task_due_date.send_keys(task_due_win_p1)
            task_due_date.send_keys(Keys.TAB)
            task_due_win_p2 = dateInfo[2]
            task_due_date.send_keys(task_due_win_p2)
        else:
            # OSX and Linux Mehtod
            task_due_mac = dateInfo[0] + dateInfo[1] + dateInfo[2]
            task_due_date.send_keys(task_due_mac)

        # Press the submit button
        self.browser.find_element_by_name("add_edit_task").click()   

    def create_new_list_from_home_page(self):
        # Got to the create a new List page
        self.perform_primary_button_press()

        # Fill in the textbox with a name 
        list_name_box = self.browser.find_element_by_name("name")
        list_name_box.send_keys("A new List")

        # Press the submit button
        self.perform_primary_button_press()

    def click_on_new_list(self):
        # Click on the newly created list
        self.browser.find_element_by_xpath('//a[contains(@href,"a-new-list")]').click()

    def click_on_list_from_homepage(self):
        # Check the first list at the top
        list_to_do = self.browser.find_element_by_xpath('//html/body/main/ul/li[1]/a')
        list_to_do_name = list_to_do.text
        # Click on that element
        list_to_do.click()

        return list_to_do_name

    def calc_number_tasks(self):
        # Check the number of incomplete tasks 
        number_of_elements = self.browser.find_elements_by_xpath('//html/body/main/table/tbody/tr')
        number_of_tasks = len(number_of_elements) - 1

        return number_of_tasks  

    def click_on_first_task(self):
        # Find and click on the second row's corresponding task 
        task = self.browser.find_element_by_xpath('//html/body/main/table/tbody/tr[2]/td/a')
        task_name = task.text
        task.click()

        return task_name

    def add_comment(self):
    	self.browser.find_element_by_name("comment-body").click()

    def mark_test_as_done(self):
        self.browser.find_element_by_xpath('//a[contains(@href,"toggle_done")]').click()
        
    def test_admin_login_create_list_add_task(self):
        """
    		Selenium Test Case #1 (LTCA)

    		Login as an admin user, create a new list, add a new task to that list
    		and then proceed to loggin off
    	"""

        # Print Basic description of test
        print("...Executing Admin-Login-Create-List-Create-Task Test \n")
        
        # Login as an admin user
        self.perform_login(isAdmin = True)

        # Check the page heading is correct
        page_heading_text = self.browser.find_element_by_css_selector(
            'h1').text
        self.assertEquals(page_heading_text, "Todo Lists")

        # Check that the system identified the user correctly
        footerText = self.browser.find_element_by_class_name("text-muted").text
        self.assertEquals(footerText, "CITS5501-Todo, 2018. Logged in as \"staffer\"")

        # Create a new list 
        self.create_new_list_from_home_page()
        
        # Check that the success alert message has appeared
        alertText = self.browser.find_element_by_class_name("alert-success").text;
        self.assertEquals(alertText, "A new list has been added.")

        # Click on the newly created list
        self.click_on_new_list()

        osName = platform.system()
        self.add_task_to_created_list("Test Task *Selenium*","Random Task Added by automated test", "01-10-2018", osName)
        # Check that the success alert message has appeared for addition of new task
        alertText = self.browser.find_element_by_class_name("alert-success").text;
        self.assertEquals(alertText, "New task \"Test Task *Selenium*\" has been added.")

        # Log out 
        self.perform_logout()

    def test_user_comment_mark_task_done(self):
        """
           Selenium Test Case #2 (CMTD)

           Login as a normal user, navigate to a task, leave a comment, mark it as done 
           and then logoff
        """        

        # Print Basic description of test
        print("...Executing User-Comment-Mark-Task-Done Test \n")
        
        # Generate radom lists with random tasks
        self.set_up_random_lists_tasks()
        
        # Login as a regular user
        self.perform_login(isAdmin = False)
        page_heading_text = self.browser.find_element_by_css_selector(
            'h1').text
        self.assertEquals(page_heading_text, "Todo Lists")

        list_to_do_name = self.click_on_list_from_homepage()
        # Check that we are on the right page corresponding to the list clicked on
        page_name = self.browser.find_element_by_css_selector('h1').text
        self.assertEquals(page_name, "Tasks in \"" + list_to_do_name + "\"")

        # Calculate the number of tasks
        number_of_tasks = self.calc_number_tasks()

        # Click and return the name of the associated task
        task_name = self.click_on_first_task()
        
        # Verify that we are on the corresponding task page
        task_page_name = self.browser.find_element_by_css_selector('h3.card-title').text
        self.assertEquals(task_page_name, task_name)

        # Fill in the comment box
        comment_block = self.browser.find_element_by_name("comment-body")
        comment_block.send_keys("Issue has been resolved. Marking complete now")
        
        # Press the add comment button
        self.add_comment()

        # Check that the comment has been added by examining the comment title
        comment_text_active = self.browser.find_elements_by_css_selector('h5')
        self.assertEquals(comment_text_active[1].text, "Comments on this task")

        # Mark a task as done
        self.mark_test_as_done()

        # Check alert status; Task status changed etc.. 
        alertText = self.browser.find_element_by_class_name("alert-success").text;
        self.assertEquals(alertText, "Task status changed for '" + task_name + "'")

        # Check number of incompelete elements have decreased by one
        number_of_tasks_previous = number_of_tasks
        number_of_tasks = self.calc_number_tasks()
        self.assertEquals(number_of_tasks, number_of_tasks_previous - 1)

        # Logout 
        self.perform_logout() 

    def test_admin_remove_list(self):
        """
			Selenium Test Case #3 (RLA)

			Login as an admin user, navigate to a list, remove list and 
			logout 
        """

        # Print Basic description of test
        print("...Executing Admin-Remove-List Test \n")
        
        # Generate radom lists with random tasks
        self.set_up_random_lists_tasks()

        # Login the admin user
        self.perform_login(isAdmin = True)
        
        # Check the page heading is correct for this user
        page_heading_text = self.browser.find_element_by_css_selector(
            'h1').text
        self.assertEquals(page_heading_text, "Todo Lists")

        # Check that the system identified the user correctly
        footerText = self.browser.find_element_by_class_name("text-muted").text
        self.assertEquals(footerText, "CITS5501-Todo, 2018. Logged in as \"staffer\"")
        
        # Click on a list
        list_to_delete = self.browser.find_element_by_xpath('//html/body/main/ul/li[1]/a')
        list_to_delete_name = list_to_delete.text
        list_to_delete.click()

        # Find the delete button element and click it
        self.browser.find_element_by_xpath('//a[contains(@href,"delete")]').click()

        # Check that the list purposed to be deleted matched the one clicked on
        page_name = self.browser.find_element_by_css_selector('h1').text
        self.assertEquals(page_name, "Delete entire list: " + list_to_delete_name + " ?")
        
        # Delete the list
        self.browser.find_element_by_name("delete-confirm").click()
      
        # Check alert status; Task status changed etc.. 
        alertText = self.browser.find_element_by_class_name("alert-success").text;
        self.assertEquals(alertText, list_to_delete_name + " is gone.")

        # Logout 
        self.perform_logout()


        