#!/usr/bin/env python3

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Set
import argparse, getpass, os, time, requests, re, string

BASE_URL = 'https://egela.ehu.eus'
OUTPUT_PATH = ''
driver = None
session = None
filenameRegex = re.compile('filename="(.+)"')
assignRegex = re.compile('(submission|feedback)_files')

def parseArguments():
    parser = argparse.ArgumentParser(description="eGela Web Scraper")
    parser.add_argument('--output', '-o', metavar='output', required=True, type=str, help='Path to folder where scrapped documents will be downloaded.')
    return parser.parse_args()

def readFileTypes(fileName: str) -> Set:
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

def checkCredentials():
    form = driver.find_element_by_class_name('fpsignup')
    if form:
        userName = input('Please enter your username: ')
        passwd = getpass.getpass(prompt='Please enter your password: ')
        form.find_element_by_id('username').send_keys(userName)
        form.find_element_by_id('password').send_keys(passwd)
        form.find_element_by_class_name('sign-up-btn').find_element_by_class_name('btn').click()
        del userName, passwd

def scrapCourse(course: webdriver.Firefox._web_element_cls):
    folderName = course.text.replace('/', '-')
    print('[INFO]: Scrapping {}'.format(folderName))
    createDir(f'{OUTPUT_PATH}/{folderName}')
    driver.execute_script('arguments[0].removeAttribute("onclick");', course)
    course.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
    WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
    driver.switch_to.window(driver.window_handles[1]) #Open second tab
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'topics')))
    clickableSections = driver.find_elements_by_class_name('section-go-link')
    if clickableSections == []:
        print('[INFO]: Scrapping mode = Unique-Portal')
        sections = driver.find_element_by_class_name('topics').find_elements_by_class_name('main')
        for section in sections:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'sectionname')))
            print('[INFO]: Scrapping section {}'.format(section.text.split('\n')[0]))
            sectionLink = section.find_element_by_class_name('content').find_element_by_tag_name('a')
            folderSection = f'{OUTPUT_PATH}/{folderName}/{removePunctuation(sectionLink.text)}'
            createDir(folderSection)
            
            try:
                imgText = section.find_element_by_class_name('img-text')
                for activity in imgText.find_elements_by_tag_name('li'):
                    scrapLi(activity, folderSection, 2)
            except NoSuchElementException:
                pass
    else:
        print('[INFO]: Scrapping mode = Multiple-Portals')
        for section in clickableSections:
            driver.execute_script('arguments[0].removeAttribute("onclick");', section)
            currentWindow = driver.current_window_handle
            section.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
            WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
            driver.switch_to.window(driver.window_handles[2]) #Open third tab
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'single-section')))
            scrapSingleSection(folderName)
            driver.close()
            driver.switch_to.window(currentWindow)
    driver.close() #Close current tab

def scrapSingleSection(courseName: str):
    scrappableSection = driver.find_element_by_class_name('single-section')
    secName = removePunctuation(scrappableSection.find_element_by_class_name('sectionname').text)
    currentDirPath = f'{OUTPUT_PATH}/{courseName}/{secName}'
    createDir(currentDirPath)

    try:
        mainSection = scrappableSection.find_element_by_class_name('img-text')
        for elem in mainSection.find_elements_by_tag_name('li'):
            scrapLi(elem, currentDirPath)
    except NoSuchElementException:
        pass

def scrapLi(elem, currentDirPath, index=3):
    if 'resource' in elem.get_attribute('class'):
        scrapResource(elem, currentDirPath, index)
    elif 'assign' in elem.get_attribute('class'):
        scrapAssign(elem, currentDirPath, index)
    elif 'folder' in elem.get_attribute('class'):
        scrapFolder(elem, currentDirPath, index)

def scrapResource(resourceLi, basePath, index=3):
    resourceLink = resourceLi.find_element_by_tag_name('a')
    response = session.get(resourceLink.get_attribute('href'))
    contentDisposition = response.headers.get('content-disposition')
    if contentDisposition:
        filename = checkFilename(filenameRegex.search(contentDisposition).group(1))
        if filename is not None:
            writeFile(f'{basePath}/{filename}', response.content)
    else:
        driver.execute_script('arguments[0].removeAttribute("onclick");', resourceLink)
        currentWindow = driver.current_window_handle
        resourceLink.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
        WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
        driver.switch_to.window(driver.window_handles[index]) #Open fourth tab
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.resourceworkaround, .resourceimage')))
        try:
            downloadableLink = driver.find_element_by_class_name('resourceworkaround').find_element_by_tag_name('a').get_attribute('href')
        except NoSuchElementException:
            downloadableLink = driver.find_element_by_class_name('resourceimage').get_attribute('src')
        response = session.get(downloadableLink)
        filename = checkFilename(filenameRegex.search(response.headers.get("content-disposition")).group(1))
        if filename is not None:
            writeFile(f'{basePath}/{filename}', response.content)
        driver.close()
        driver.switch_to.window(currentWindow)

def scrapFolder(folderLi, basePath, index=3):
    folderLink = folderLi.find_element_by_class_name('activityinstance').find_element_by_tag_name('a')
    driver.execute_script('arguments[0].removeAttribute("onclick");', folderLink)
    currentWindow = driver.current_window_handle
    folderLink.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
    WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
    driver.switch_to.window(driver.window_handles[index]) #Open fourth tab
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'singlebutton')))
    params = {}
    singleButton = driver.find_element_by_class_name('singlebutton')
    for inp in singleButton.find_elements_by_tag_name('input'):
        params[inp.get_attribute('name')] = inp.get_attribute('value')
    response = session.post(singleButton.find_element_by_tag_name('form').get_attribute('action'), data = params)
    filename = checkFilename(filenameRegex.search(response.headers.get("content-disposition")).group(1))
    if filename is not None:
        writeFile(f'{basePath}/{filename}', response.content)
    driver.close()
    driver.switch_to.window(currentWindow)

def scrapAssign(assignLi, basePath, index=3):
    try:
        assignLink = assignLi.find_element_by_class_name('activityinstance').find_element_by_tag_name('a')
        driver.execute_script('arguments[0].removeAttribute("onclick");', assignLink)
        currentWindow = driver.current_window_handle
        assignLink.send_keys(Keys.CONTROL + Keys.RETURN) #Open on new tab
        WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles)) #Wait until tab is open
        driver.switch_to.window(driver.window_handles[index]) #Open fourth tab
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'generaltable')))
        for table in driver.find_elements_by_class_name('generaltable'):
            for link in table.find_elements_by_tag_name('a'):
                currentHref = link.get_attribute('href')
                if assignRegex.search(currentHref) is not None:
                    response = session.get(currentHref)
                    filename = checkFilename(filenameRegex.search(response.headers.get("content-disposition")).group(1))
                    if filename is not None:
                        writeFile(f'{basePath}/{filename}', response.content)
        driver.close()
        driver.switch_to.window(currentWindow)
    except NoSuchElementException:
        pass
    except StaleElementReferenceException:
        scrapAssign(assignLi, basePath, index)

def writeFile(filename: str, content: bytes):
    fout = open(filename, 'wb')
    fout.write(content)
    fout.close()

def checkFilename(filename: str) -> str:
    dotIndex = filename.rindex('.')
    extension = filename[dotIndex + 1:]
    if extension in fileTypes:
        filenameNoExt = removePunctuation(filename[:dotIndex])
        return f'{filenameNoExt}.{extension}'
    else:
        return None

def removePunctuation(s: str) -> str:
    return s.translate(str.maketrans('', '', string.punctuation))

if __name__ == "__main__":

    args = parseArguments()
    OUTPUT_PATH = args.output
    fileTypes = readFileTypes('res/fileTypes.txt')
    driver = initDriver()
    checkCredentials()
    session = requests.Session()
    cookie = driver.get_cookie('MoodleSessionegela')
    session.cookies.set(cookie['name'], cookie['value'])
    for coursebox in driver.find_elements_by_class_name('coursebox'):
        currentWindow = driver.current_window_handle #Save current tab
        course = coursebox.find_element_by_tag_name('a')
        scrapCourse(course)
        driver.switch_to.window(currentWindow) #Restore saved tab
    session.cookies.clear()
    driver.delete_all_cookies()
    driver.quit()
