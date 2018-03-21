import json

import time

import re
from urllib.parse import urlparse

from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait

from .models import Account, Post

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

    def upsert_profile(self, account=None, check_posts=1000):
        """Update profile"""
        username = account.username if account else self.account.username
        account, created = Account.objects.update_or_create(username=username)
        page = ProfilePage(self.driver, username)

        # upsert counts
        account.posts_count = page.posts_count
        account.followers_count = page.followers_count
        account.following_count = page.following_count
        account.save()

        # upsert posts
        for i, post in enumerate(page.posts):
            # only check a limited amount of posts per user
            if i >= check_posts:
                break
            # upsert post
            hash, created = Post.objects.update_or_create(
                account=account,
                hash=post,
            )
            # till existing post found
            if not created:
                break


########################################################################################
# Profile page
########################################################################################

class ProfilePageError(InstagramError):
    """Error on profile page"""


class ProfilePage:

    def __init__(self, driver, username):
        self.driver = driver
        self.driver.get(f'{URL_INSTAGRAM}/{username}')

    @property
    def posts_count(self):
        return self._parse_number(
            self.driver.find_element_by_xpath("//ul/li[1]/span/span").text
        )

    @property
    def followers_count(self):
        return self._parse_number(
            self.driver.find_element_by_xpath("//ul/li[2]/a/span").text
        )

    @property
    def following_count(self):
        return self._parse_number(
            self.driver.find_element_by_xpath("//ul/li[3]/a/span").text
        )

    @property
    def container(self):
        return self.driver.find_element_by_xpath('//article')

    @property
    def links(self):
        return self.driver.find_elements_by_xpath('//a[starts-with(@href, "/p/")]')

    @property
    def spinner(self):
        return self.driver.find_elements_by_xpath('//article/div[2]')

    @property
    def posts(self):
        """Generator for the links of the posts"""
        counter = 0
        while True:
            if len(self.links) == counter:
                break
            for link in self.links[counter:]:
                counter += 1
                url = urlparse(link.get_attribute('href'))
                matches = re.match(r'/p/(.*)/', url.path)
                yield matches.groups(0)[0]
            self.driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', self.container)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: len(self.links) != counter)
            except TimeoutException:
                # no new elements, so is spinner gone?
                if not self.is_spinner_gone():
                    raise ProfilePageError('No new elements but spinner remains')
                break

    def _parse_number(self, number):
        """
        Parses the number. Remove the unused comma. Replace the concatenation with relevant zeros. Remove the dot.

        :param number: str

        :return: int
        """
        formatted_num = number.replace(',', '')
        formatted_num = re.sub(r'(k)$', '00' if '.' in formatted_num else '000', formatted_num)
        formatted_num = re.sub(r'(m)$', '00000' if '.' in formatted_num else '000000', formatted_num)
        formatted_num = formatted_num.replace('.', '')
        return int(formatted_num)

    def is_spinner_gone(self):
        """Is the loading spinner removed"""
        try:
            self.spinner
        except NoSuchElementException:
            return False
        return True


########################################################################################
# Login page
########################################################################################

class LoginPageError(InstagramError):
    """Error on login page"""


class LoginPage:

    def __init__(self, driver):
        self.driver = driver
        self.driver.get(URL_INSTAGRAM)

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

    @property
    def security_code_button(self):
        return self.driver.find_element_by_xpath('//form//button[text()="Send Security Code"]')

    def is_suspicious_login(self):
        """Is this a suspicious login"""
        try:
            self.security_code_button
        except NoSuchElementException:
            return False
        return True

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
            True if logged in
            False if already logged in
            Exception for auth failure
        """
        if self.is_logged_in():
            return False

        # Check if the first div is 'Create an Account' or 'Log In'
        if self.login_link:
            ActionChains(self.driver).move_to_element(self.login_link).click().perform()

        ActionChains(self.driver).move_to_element(self.input_username).click().send_keys(username).perform()
        ActionChains(self.driver).move_to_element(self.input_password).click().send_keys(password).perform()
        ActionChains(self.driver).move_to_element(self.login_button).click().perform()

        if self.is_suspicious_login():
            time.sleep(60)

        if not self.is_logged_in():
            raise LoginPageError('Could not authenticate')

        return True
