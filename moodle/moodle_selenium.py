# -*- coding: utf-8 -*-
"""
Selenium-based interface for Moodle.

.. moduleauthor:: Martin R. Albrecht <martinralbrecht@googlemail.com>

"""
import configparser
import os
from collections import namedtuple

from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException)
from selenium.webdriver import Firefox
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def configf(filename):
    """
    Read config file from ``filename``.

    :param filename: Config file name.
    :returns: ``ConfigParser`` object

    """
    config = configparser.ConfigParser()
    config.read(filename)
    return config


def browserf(config):
    """
    Create browser instance.

    :param config: ``ConfigParser`` object
    :returns: Browser object

    """

    opts = Options()

    headless = config["ui"].getboolean("headless")

    if headless:
        opts.set_headless()
        assert opts.headless

    browser = Firefox(options=opts)

    if not headless:
        browser.set_window_size(int(config["ui"]["xdim"]),
                                int(config["ui"]["ydim"]))

    return browser


def statef(filename="moodle.cfg"):
    """
    Read config file and create browser object.

    :param filename: Config file name.
    :returns: state

    """
    config = configf(filename)
    browser = browserf(config)
    State = namedtuple("State", ["browser", "config"])
    return State(browser=browser, config=config)


def loginf(s):
    """
    Log into Moodle.

    :param s: Current state
    :returns: state

    .. note :: Logging in while already logged in is handled gracefully.

    """
    s.browser.get(s.config["site"]["url"])
    try:
        s.browser.find_element_by_name("username").clear()
        s.browser.find_element_by_name("password").clear()
        s.browser.find_element_by_name("username").send_keys(s.config["auth"]["username"])
        s.browser.find_element_by_name("password").send_keys(s.config["auth"]["password"])
        s.browser.find_element_by_id("submit").click()
    except NoSuchElementException:
        try:
            s.browser.find_element_by_id("loggedin-user")
        except NoSuchElementException:
            raise RuntimeError("Unknown error, seem to be neither logged in nor not logged in.")

    return s


def bootstrap(filename="moodle.cfg"):
    """
    Read config file, create browser object and log in.

    :param filename: Config file name.
    :returns: state

    """
    return loginf(statef(filename))


def coursef(s, course, editable=True):
    """
    Switch to course.

    :param s: Current state
    :param course: Course name
    :param editable: Toggle editable
    :returns: state

    .. note :: This function consults the config's alias database for the course name.

    """
    course = s.config["aliases"].get(course, course)

    s.browser.find_element_by_css_selector("a[title=\"My courses\"]").click()
    s.browser.find_element_by_id("label_2_4").click()
    s.browser.find_element_by_css_selector("a[title=\"{course}\"]".format(course=course)).click()
    if editable:
        s = editablef(s)
    return s


def editablef(s):
    """Set current course editable.

    :param s: Current state
    :returns: state

    """
    s.browser.find_element_by_id("action-menu-toggle-0").click()
    s.browser.find_element_by_link_text("Turn editing on").click()
    return s


def set_summary(s, headline, text, finalize=False, send_keys=False):
    """
    Set the summary of headline to text.

    :param s: Current state with a course page open.
    :param headline: Moodle headline.
    :param text: New text.
    :param finalize: Save changes, i.e. do not do manual sanity checking.
    :param send_keys: send individual key strokes to fill the text area (slow).
    :returns: state

    .. note:: headless implies finalize.
    .. note:: This function consults the config's alias database for the headline.

    """
    headline = s.config["aliases"].get(headline, headline)

    xpath = "/".join(["/",
                      "h3[contains(text(),'{headline}')]",
                      "..",
                      "div[@class='summary']",
                      "a[@title='Edit summary']"])
    s.browser.find_element_by_xpath(xpath.format(headline=headline)).click()

    s.browser.find_element_by_xpath('//*[@title="Show more buttons"]').click()
    s.browser.find_element_by_xpath('//*[@title="HTML"]').click()
    s.browser.find_element_by_id('id_summary_editor').clear()

    if not send_keys:
        text = text.replace("'", "\\'")
        text = text.replace("\n", "\\n")
        s.browser.execute_script("document.getElementById('id_summary_editor').value = '%s';"%text)
    else:
        s.browser.find_element_by_id('id_summary_editor').send_keys(text)

    # Render
    s.browser.find_element_by_xpath('//*[@title="HTML"]').click()

    if s.config["ui"].getboolean("headless") or finalize:
        s.browser.find_element_by_id("id_submitbutton").click()

    return s


def file_list(s):
    """
    Return file list of this course.

    :param s: Current state with a course page open.
    :returns: state

    """
    elements = s.browser.find_elements_by_class_name("instancename")
    files = []
    for element in elements:
        try:
            if element.find_element_by_xpath("*").get_attribute("innerText") == u'File':
                files.append(element.text)
        except NoSuchElementException:
            pass
    return tuple(files)


def upload_file(s, name, filename, finalize=False):
    """
    Upload a file.

    :param s: Current state with a course page open.
    :param name: Name on Moodle (as it appears on Course page)
    :param filename: Local file (will appear on Moodle, too)
    :param finalize: Save changes, i.e. do not do manual sanity checking.
    :returns: state

    .. note :: This function consults the config's alias database for the headline.

    """
    name = s.config["aliases"].get(name, name)
    filename = os.path.abspath(filename)

    xpath = "/".join(["/",
                      "span[contains(text(),'{name}')]",
                      "..", "..", "..",
                      "span[@class='actions']",
                      "div", "ul", "li",
                      "a[contains(text(), 'Edit')]"])
    s.browser.find_element_by_xpath(xpath.format(name=name)).click()
    xpath = "/".join(["/",
                      "span[contains(text(),'{name}')]",
                      "..", "..", "..",
                      "span[@class='actions']",
                      "div",
                      "ul[@class='menu  align-tr-br']",
                      "li",
                      "a",
                      "span[contains(text(), 'Edit settings')]"])
    s.browser.find_element_by_xpath(xpath.format(name=name)).click()

    WebDriverWait(s.browser, 5).until(EC.visibility_of_element_located((
        By.CLASS_NAME, "fp-btn-add"))).click()
    WebDriverWait(s.browser, 5).until(EC.visibility_of_element_located((
        By.XPATH, "//input[@name='repo_upload_file']"))).send_keys(filename)
    s.browser.find_element_by_xpath("//button[@class='fp-upload-btn btn-primary btn']").click()
    try:
        WebDriverWait(s.browser, 5).until(EC.visibility_of_element_located((
            By.XPATH, "//button[@class='fp-dlg-butoverwrite btn']"))).click()
    except TimeoutException:
        pass

    if s.config["ui"].getboolean("headless") or finalize:
        ActionChains(s.browser).move_to_element(s.browser.find_element_by_id("id_submitbutton2")).click().perform()

    return s
