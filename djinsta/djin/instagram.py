import json

import time
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options

URL_INSTAGRAM = 'https://www.instagram.com'


class InstagramError(Exception):
    """Instagram errors"""


class Instagram:

    def __init__(self, account):
        self.account = account

        options = Options()
        options.add_argument('--dns-prefetch-disable')
        options.add_argument('--no-sandbox')
        options.add_argument('--lang=en-US')
        options.add_argument('--disable-setuid-sandbox')
        chrome_prefs = {
            'intl.accept_languages': 'en-US',
        }
        options.add_experimental_option('prefs', chrome_prefs)
        self.driver = webdriver.Chrome(settings.BROWSER_CHROME, chrome_options=options)

        # set waiting on elements to load
        self.driver.implicitly_wait(5)

        # load cookies
        if account.cookies:
            cookies = json.loads(account.cookies)
            self.driver.get(URL_INSTAGRAM)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()

    def login(self):
        """Log account in on login page"""
        new_login = LoginPage(self.driver).login(
            self.account.username,
            self.account.password)
        if new_login:
            self.account.cookies = json.dumps(self.driver.get_cookies())
            self.account.save()

    def get_profile(self):
        """Get profile"""
        ProfilePage(self.driver).get(self.account.username)


########################################################################################
# Profile page
########################################################################################

class ProfilePageError(InstagramError):
    """Error on profile page"""


class ProfilePage:

    def __init__(self, driver):
        self.driver = driver

    def get(self, username):
        self.driver.get(f'{URL_INSTAGRAM}/{username}')
        time.sleep(20)


########################################################################################
# Login page
########################################################################################

class LoginPageError(InstagramError):
    """Error on login page"""


class LoginPage:

    def __init__(self, driver):
        self.driver = driver

    @property
    def login_link(self):
        return self.driver.find_element_by_xpath("//article/div/div/p/a[text()='Log in']")

    @property
    def input_username(self):
        return self.driver.find_element_by_xpath("//input[@name='username']")

    @property
    def login_button(self):
        return self.driver.find_element_by_xpath("//form/span/button[text()='Log in']")

    @property
    def input_password(self):
        return self.driver.find_element_by_xpath("//input[@name='password']")

    @property
    def nav_profile(self):
        return self.driver.find_element_by_xpath('//a[text()="Profile"]')

    def is_logged_in(self):
        """Check if account is logged-in (profile icon in nav)"""
        try:
            self.nav_profile
        except NoSuchElementException:
            return False
        return True

    def login(self, username, password):
        """
        Logins the account with the given username and password
        Enter username and password and logs the account in
        Sometimes the element name isn't 'Username' and 'Password'
        (valid for placeholder too)

        Returns:
            True if logge din
            False if already logged in
            Exception for auth failure
        """
        self.driver.get(URL_INSTAGRAM)

        if self.is_logged_in():
            return False

        # Check if the first div is 'Create an Account' or 'Log In'
        if self.login_link:
            ActionChains(self.driver).move_to_element(self.login_link).click().perform()

        ActionChains(self.driver).move_to_element(self.input_username).click().send_keys(username).perform()
        ActionChains(self.driver).move_to_element(self.input_password).click().send_keys(password).perform()
        ActionChains(self.driver).move_to_element(self.login_button).click().perform()

        if not self.is_logged_in():
            raise LoginPageError('Could not authenticate')

        return True
