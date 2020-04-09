#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List
import argparse, getpass, os, time

BASE_URL = 'https://egela.ehu.eus'
OUTPUT_PATH = ''

def parseArguments():
    parser = argparse.ArgumentParser(description="eGela Web Scraper")
    parser.add_argument('--output', '-o', metavar='output', required=True, type=str, help='Path to folder where scrapped documents will be downloaded.')
    return parser.parse_args()

def readFileTypes(fileName: str) -> List:
    fileTypes = set()
    with open(fileName, 'r') as f:
        for line in f:
            trimmedLine = line.strip()
            if trimmedLine and trimmedLine[0] != '#':
                fileTypes.add(trimmedLine)
    return fileTypes

def createDir(path: str):
    try:
        os.mkdir(path, 755)
    except Exception:
        pass

def initDriver() -> webdriver:
    options = Options()
    options.headless = False
    driver = webdriver.Firefox(options=options, executable_path="res/geckodriver")
    driver.get(BASE_URL)
    return driver

def checkChredentials(driver: webdriver):
    form = driver.find_element_by_class_name('fpsignup')
    if form:
        userName = input('Please enter your username: ')
        passwd = getpass.getpass(prompt='Please enter your password: ')
        form.find_element_by_id('username').send_keys(userName)
        form.find_element_by_id('password').send_keys(passwd)
        form.find_element_by_class_name('sign-up-btn').find_element_by_class_name('btn').click()
        del userName, passwd

def scrapCourse(driver: webdriver, course: webdriver.Firefox._web_element_cls):
    folderName = course.text.replace('/', '-')
    createDir(f'{OUTPUT_PATH}/{folderName}')
    course.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
    WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
    driver.switch_to.window(driver.window_handles[1]) #Open second tab
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'topics')))
    sections = driver.find_element_by_class_name('topics').find_elements_by_class_name('section')
    for section in sections:
        try:
            sectionLink = section.find_element_by_class_name('content').find_element_by_tag_name('a')
            folderSection = f'{OUTPUT_PATH}/{folderName}/{sectionLink.text}'
            createDir(folderSection)
            driver.get(sectionLink.get_attribute('href'))
            scrapSection(driver, folderSection)
        except Exception:
            pass
    driver.close() #Close current tab

def scrapSection(driver: webdriver, folderPath:str):
    #TODO: implement section traversal and document download
    pass

if __name__ == "__main__":

    args = parseArguments()
    OUTPUT_PATH = args.output
    fileTypes = readFileTypes('res/fileTypes.txt')
    driver = initDriver()
    checkChredentials(driver)
    for coursebox in driver.find_elements_by_class_name('coursebox'):
        currentWindow = driver.current_window_handle #Save current tab
        course = coursebox.find_element_by_tag_name('a')
        scrapCourse(driver, course)
        driver.switch_to.window(currentWindow) #Restore saved tab
    driver.delete_all_cookies()
    driver.quit()
