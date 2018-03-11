import json

from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options


URL_INSTAGRAM = 'https://www.instagram.com'


class InstagramError(Exception):
    """Instagram errors"""


class Instagram:

    def __init__(self, user):
        self.user = user

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
        if user.profile.insta_cookies:
            cookies = json.loads(user.profile.insta_cookies)
            self.driver.get(URL_INSTAGRAM)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # persist cookies for next use
        self.user.profile.insta_cookies = json.dumps(self.driver.get_cookies())
        self.user.save()

        self.driver.quit()
        
    def login(self):
        LoginPage(self.driver).login(
            self.user.username,
            self.user.profile.insta_password)


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
        """Check if user is logged-in (If there's two 'nav' elements)"""
        try:
            self.nav_profile
        except NoSuchElementException:
            return False
        return True

    def login(self, username, password):
        """
        Logins the user with the given username and password
        Enter username and password and logs the user in
        Sometimes the element name isn't 'Username' and 'Password'
        (valid for placeholder too)
        """
        self.driver.get(URL_INSTAGRAM)

        if self.is_logged_in():
            return

        # Check if the first div is 'Create an Account' or 'Log In'
        if self.login_link:
            ActionChains(self.driver).move_to_element(self.login_link).click().perform()

        ActionChains(self.driver).move_to_element(self.input_username).click().send_keys(username).perform()
        ActionChains(self.driver).move_to_element(self.input_password).click().send_keys(password).perform()
        ActionChains(self.driver).move_to_element(self.login_button).click().perform()

        if not self.is_logged_in():
            raise LoginPageError('Could not authenticate')

