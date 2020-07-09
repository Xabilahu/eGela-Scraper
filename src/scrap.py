#!/usr/bin/env python3

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Set
import argparse, getpass, os, time, requests, re, string, math

BASE_URL = 'https://egela.ehu.eus'
OUTPUT_PATH = ''
totalSize = 0
driver = None
session = None
filenameRegex = re.compile('filename="(.+)"')
assignRegex = re.compile('(submission|feedback)_files')

def parseArguments():
    parser = argparse.ArgumentParser(description="eGela Web Scraper")
    parser.add_argument('--output', '-o', metavar='output', required=True, type=str, help='Path to folder where scrapped documents will be downloaded.')
    return parser.parse_args()

def convertSize(sizeBytes):
   if sizeBytes == 0:
       return "0 B"
   sizeName = ("B", "KiB", "MiB", "GiB", "TiB")
   i = int(math.floor(math.log(sizeBytes, 1024)))
   p = math.pow(1024, i)
   s = round(sizeBytes / p, 2)
   return f'{s} {sizeName[i]}'

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
    global totalSize
    courseSize = 0
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
            sectionSize = 0
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'sectionname')))
            secName = section.text.split('\n')[0]
            sectionLink = section.find_element_by_class_name('content').find_element_by_tag_name('a')
            folderSection = f'{OUTPUT_PATH}/{folderName}/{removePunctuation(sectionLink.text)}'
            createDir(folderSection)
            
            try:
                imgText = section.find_element_by_class_name('img-text')
                for activity in imgText.find_elements_by_tag_name('li'):
                    sectionSize += scrapLi(activity, folderSection, 2)
            except NoSuchElementException:
                pass
            courseSize += sectionSize
            print(f'[INFO]: Scrapped {convertSize(sectionSize)} from section {secName}')
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
    totalSize += courseSize
    print(f'[INFO]: Scrapped a total of {convertSize(courseSize)} from course {folderName}')

def scrapSingleSection(courseName: str):
    global totalSize
    currentSize = 0
    scrappableSection = driver.find_element_by_class_name('single-section')
    secName = removePunctuation(scrappableSection.find_element_by_class_name('sectionname').text)
    currentDirPath = f'{OUTPUT_PATH}/{courseName}/{secName}'
    createDir(currentDirPath)

    try:
        mainSection = scrappableSection.find_element_by_class_name('img-text')
        for elem in mainSection.find_elements_by_tag_name('li'):
            currentSize += scrapLi(elem, currentDirPath)
    except NoSuchElementException:
        pass

    totalSize += currentSize
    print(f'[INFO]: Scrapped {convertSize(currentSize)} from section {secName}')

def scrapLi(elem, currentDirPath, index=3) -> int:
    currentSize = 0

    if 'resource' in elem.get_attribute('class'):
        currentSize = scrapResource(elem, currentDirPath, index)
    elif 'assign' in elem.get_attribute('class'):
        currentSize = scrapAssign(elem, currentDirPath, index)
    elif 'folder' in elem.get_attribute('class'):
        currentSize = scrapFolder(elem, currentDirPath, index)
    
    return currentSize

def scrapResource(resourceLi, basePath, index=3) -> int:
    currentSize = 0

    resourceLink = resourceLi.find_element_by_tag_name('a')
    response = session.get(resourceLink.get_attribute('href'))
    contentDisposition = response.headers.get('content-disposition')
    if contentDisposition:
        filename = checkFilename(filenameRegex.search(contentDisposition).group(1))
        if filename is not None:
            currentSize = len(response.content)
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
            currentSize = len(response.content)
            writeFile(f'{basePath}/{filename}', response.content)
        driver.close()
        driver.switch_to.window(currentWindow)

    return currentSize

def scrapFolder(folderLi, basePath, index=3) -> int:
    currentSize = 0

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
        currentSize = len(response.content)
        writeFile(f'{basePath}/{filename}', response.content)
    driver.close()
    driver.switch_to.window(currentWindow)

    return currentSize

def scrapAssign(assignLi, basePath, index=3) -> int:
    try:
        currentSize = 0
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
                        currentSize = len(response.content)
                        writeFile(f'{basePath}/{filename}', response.content)
        driver.close()
        driver.switch_to.window(currentWindow)
    except NoSuchElementException:
        pass
    except StaleElementReferenceException:
        scrapAssign(assignLi, basePath, index)
    
    return currentSize

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
    punctuation = string.punctuation
    for c in ['-', '.', '_']:
        puntuation = punctuation.replace(c, '')
    return s.translate(str.maketrans('', '', punctuation))

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
    print(f'[INFO]: Scrapper finished. A total of {convertSize(totalSize)} were scrapped.')
    session.cookies.clear()
    driver.delete_all_cookies()
    driver.quit()
