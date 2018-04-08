import json
import re
import time
from urllib.parse import urlparse

from django.conf import settings
from django.utils.dateparse import parse_datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait

from .models import Account, Post, Tag, Location, Media

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
        # self.driver.implicitly_wait(5)

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

    def upsert_profile(self, account, check_posts=1000):
        """Update profile"""
        page = ProfilePage(self.driver, account.username)
        if page.is_private():
            return account.delete()

        # upsert counts
        account.posts_count = page.posts_count
        account.followers_count = page.followers_count
        account.following_count = page.following_count
        account.bio = page.bio
        account.website = page.website
        account.save()

        # upsert posts
        for i, code in enumerate(page.posts):
            # only check a limited amount of posts per user
            if i >= check_posts:
                break
            # upsert post
            post, created = Post.objects.update_or_create(
                account=account,
                code=code,
            )
            # till existing post found
            if not created:
                break

    def upsert_post(self, post):
        """Update information from post"""
        # posts can be deleted
        page = PostPage(self.driver, post.code)
        if page.is_deleted():
            return post.delete()

        post.count, post.kind = page.popularity
        post.created_at = page.created_at
        post.description = page.description
        loc_code, loc_name = page.location

        # the media seems to move around on the vpn, will have to update it
        # with every update and remove the duplicate old rows
        previous_pks = [m.pk for m in post.media.all()]
        current_pks = []
        for media_item in page.media:
            media, created = Media.objects.get_or_create(
                post=post, kind=media_item['kind'], source=media_item['source'],
                defaults={
                    'size': media_item.get('size'),
                    'poster': media_item.get('poster'),
                    'extension': media_item.get('extension')
                })
            current_pks.append(media.pk)
        redundant_pks = set(previous_pks) - set(current_pks)
        if redundant_pks:
            Media.objects.filter(pk__in=redundant_pks).delete()

        if loc_code:
            location, created = Location.objects.get_or_create(
                code=loc_code, name=loc_name)
            post.location = location
        tags = []
        for tag_item in page.tags:
            tag, created = Tag.objects.get_or_create(word=tag_item)
            tags.append(tag)
        post.tags.set(tags)
        post.save()


########################################################################################
# Base page
########################################################################################

class BasePage:

    def __init__(self, driver, param=''):
        self.driver = driver
        self.driver.get(self.URL_PATTERN.format(param))

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

    def _parse_tags(self, sentence):
        """Parses the sentences for hashtags and returns a list"""
        if not sentence:
            return []
        return [t.lower() for t in re.findall(r'#(\w+)', sentence)]


# location feed
# explore/locations/(\d+)


########################################################################################
# Post page
########################################################################################

class PostPageError(InstagramError):
    """Error on post page"""


class PostPage(BasePage):

    URL_PATTERN = URL_INSTAGRAM + '/p/{}'

    def is_deleted(self):
        """is post deleted"""
        try:
            self.driver.find_element_by_xpath('//h2[text()="Sorry, this page isn\'t available."]')
        except NoSuchElementException:
            return False
        return True


    @property
    def created_at(self):
        return parse_datetime(
            self.driver.find_element_by_xpath('//time').get_attribute('datetime'))

    @property
    def username(self):
        return self.driver.find_element_by_xpath('//article/header/div/div/div/a').text

    @property
    def popularity(self):
        # todo fix: 'charityflock, veneration_helensvale, ilove_relaxx, angislon, kuldeep_singh.solanki, hayley_brown6, mardanjahya111 and martadziak like this'
        sentence = self.driver.find_element_by_xpath('//article/div/section/div').text
        words = sentence.split(' ')
        try:
            count = self._parse_number(words[0])
        except ValueError:
            return None, None
        kind = words[1]
        return count, kind

    @property
    def media_container(self):
        return self.driver.find_element_by_xpath('//article/div[1]/div')

    @property
    def media_chevron(self):
        return self.driver.find_element_by_xpath(
            '//article/div/div//a[contains(concat(" ",normalize-space(@class)," ")," coreSpriteRightChevron ")]')

    @property
    def media(self):
        """return the media sources"""
        media = []
        while True:
            try:
                vid = self.driver.find_element_by_xpath('//article//video')
                src = vid.get_attribute('src')
                poster = vid.get_attribute('poster')
                extension = vid.get_attribute('type')
                media.append({'kind': Media.VID, 'source': src, 'poster': poster, 'extension': extension})
            except NoSuchElementException:
                # sometimes the srcset is not loaded yet
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.find_element_by_xpath(
                        '//article/div[1]/div/div//div[1]/img').get_attribute('srcset')
                )
                img = self.driver.find_element_by_xpath('//article/div[1]/div/div//div[1]/img')
                src = [s.strip() for s in img.get_attribute('srcset').split(',')][-1]
                src, size = src.split(' ')
                media.append({'kind': Media.IMG, 'source': src, 'size': int(size[:-1])})
            # next image
            try:
                ActionChains(self.driver).move_to_element(
                    self.media_container).pause(1).click(
                    self.media_chevron).perform()
            except NoSuchElementException:
                break
        return media

    @property
    def description(self):
        """If no description there would be no comment"""
        try:
            return self.driver.find_element_by_xpath(
                f'//article//ul/li//*[contains(text(), "{self.username}")]/following-sibling::span').text
        except NoSuchElementException:
            return

    @property
    def tags(self):
        """Return parsed tags from description"""
        return self._parse_tags(self.description)

    @property
    def location(self):
        """Return id and location name"""
        try:
            loc = self.driver.find_element_by_xpath('//article/header/div[2]/div[2]/a')
        except NoSuchElementException:
            return None, None
        code = re.search(r'locations/(\d+)', loc.get_attribute('href')).groups()[0]
        name = loc.text
        return code, name


########################################################################################
# Profile page
########################################################################################

class ProfilePageError(InstagramError):
    """Error on profile page"""


class ProfilePage(BasePage):

    URL_PATTERN = URL_INSTAGRAM + '/{}'

    def is_private(self):
        """some accounts are private"""
        try:
            self.driver.find_element_by_xpath('//h2[text()="This Account is Private"]')
        except NoSuchElementException:
            return False
        return True

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
    def bio(self):
        try:
            return self.driver.find_element_by_xpath("//article/header//div[2]/span").text
        except NoSuchElementException:
            pass

    @property
    def website(self):
        try:
            return self.driver.find_element_by_xpath("//article/header//div[2]/a").text
        except NoSuchElementException:
            pass

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


class LoginPage(BasePage):

    URL_PATTERN = URL_INSTAGRAM

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
