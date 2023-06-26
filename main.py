from utils import get_web_driver, close_script, Download_from_youtube_link, Download_from_viemo_link
from time import sleep
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import os
from questionary import select
from seleniumwire import webdriver
from typing import List
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from multiprocessing import cpu_count, Process
from threading import Thread
import math
import sys
import gzip
import re


class Bot:
    # processes: List[Process] = []
    ignored_exceptions = (StaleElementReferenceException,)
    url = "https://fireship.io/courses/"
    script_to_inject = r"""
setInterval(async () => {
    document.querySelectorAll("[free=\"\"]").forEach(el => el.setAttribute("free", true)) // set all elements with the attribute free set to "" to true

    if (document.querySelector("if-access [slot=\"granted\"]")) { // replace HOW TO ENROLL to YOU HAVE ACCESS
        document.querySelector("if-access [slot=\"denied\"]").remove()
        document.querySelector("if-access [slot=\"granted\"]").setAttribute("slot", "denied")
    }

    if (document.querySelector("video-player")?.shadowRoot?.querySelector(".vid")?.innerHTML) return; // return if no video player
    const vimeoId = document.querySelector("global-data").vimeo; // get id for vimeo video
    const youtubeId = document.querySelector("global-data").youtube; // get id for vimeo video

    if (vimeoId) { // if there is an id,
        document.querySelector("video-player").setAttribute("free", true) // set free to true
        const html = (await fetch(`https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F${vimeoId}&id=${vimeoId}`).then(r=>r.json())).html
        document.querySelector("video-player").shadowRoot.querySelector(".vid").innerHTML = html // set video
    }
    if (youtubeId) { // if there is an id,
        document.querySelector("video-player").setAttribute("free", true) // set free to true
        document.querySelector("video-player").shadowRoot.querySelector(".vid").innerHTML = `<iframe src="https://youtube.com/embed/${youtubeId}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen="" title="${location.pathname.split("/")[3]}" width="426" height="240" frameborder="0"></iframe>` // set video
    }
}, 100)
"""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def set_max_res_vimeo_video(self, vimeo_iframe):
        driver = self.driver
        driver.switch_to.frame(vimeo_iframe)
        # click settings btn
        el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='player']/div[7]/div[6]/div[2]/div/button[@aria-label='Settings']"))).click()
        sleep(0.5)
        # go to quality oprions
        el = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@role='menuitemradio']")))[0].click()
        sleep(0.5)
        # set the max resolution
        els = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//ul[@role = 'group']/*")))
        for i, el in enumerate(els):
            res = el.get_attribute("data-id")
            resInt = res[0:-1]
            if resInt.isdigit() and len(resInt) <= 4:
                els[i].click()
                break
        sleep(0.2)

        # close settings
        el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Close menu']")))
        driver.execute_script("arguments[0].click();", el)
        sleep(0.2)

        # play video
        el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Play']"))).click()

        driver.switch_to.default_content()

    def _check_if_is_youtube_video_and_get_link(self) -> (bool, str):
        driver = self.driver
        sleep(15)
        try:
            video_player = WebDriverWait(driver, 5, ignored_exceptions=self.ignored_exceptions).until(
                EC.presence_of_element_located((By.TAG_NAME, "video-player"))).shadow_root
        except selenium.common.exceptions.TimeoutException as e:
            section = driver.find_element(By.ID, "coming-soon").parent
            date = BeautifulSoup(section.get_attribute(
                'innerHTML'), "html.parser").find("p").getText()
            print(date)
            driver.close()
            driver.quit()
            print("DONE")
        iframe = video_player.find_element(
            By.CSS_SELECTOR, "iframe")
        iframe_src = iframe.get_attribute("src")
        if "youtube.com" in iframe_src:
            driver.switch_to.frame(iframe)
            linkEl = driver.find_element(
                By.CSS_SELECTOR, '#movie_player > div.ytp-chrome-bottom > div.ytp-chrome-controls > div.ytp-right-controls > a')
            link = linkEl.get_attribute("href")
            driver.switch_to.default_content()
            return (True, link)
        self.set_max_res_vimeo_video(iframe)
        del driver.requests
        sleep(10)
        video_urls, audio_urls = [], []
        for req in driver.requests:
            if "master.json" in req.url:
                pass
            if "video" in req.url and ".mp4" in req.url and not "master.json" in req.url:
                video_urls.append(req.url.split("?")[0])
            if "audio" in req.url and ".mp4" in req.url and not "master.json" in req.url:
                audio_urls.append(req.url.split("?")[0])
        return (False, (video_urls[0], audio_urls[0]))

    def _download_video(self, folder, videoLesson, video_title):
        driver = self.driver
        is_youtube, link = self._check_if_is_youtube_video_and_get_link()
        if is_youtube:
            Download_from_youtube_link(link, folder, videoLesson)
            # process = Process(
            #     target=Download_from_youtube_link, args=(link, folder, videoLesson))
            # process.start()
            # self.processes.append(process)
        else:
            video_url, adudio_url = link
            Download_from_viemo_link(
                video_url, adudio_url, folder, videoLesson, video_title)

    def _download_videos(self, videoEls, course: str):
        driver = self.driver
        currentFolder = None
        videoLesson = 0
        sectionIndex = 0
        for i in range(videoEls):
            videoEl = WebDriverWait(driver, 5, ignored_exceptions=self.ignored_exceptions).until(
                EC.presence_of_all_elements_located((By.XPATH, """//*[@id="sidebar"]/*""")))[i]
            css = videoEl.get_attribute("class")
            videoLesson += 1
            if css != None and css != '':  # if true, is a section else is a video
                videoLesson = 0
                sectionIndex += 1
                section_course = BeautifulSoup(
                    f"<div>{videoEl.get_attribute('innerHTML')}</div>", 'html.parser').find("h3").getText()
                currentFolder = f"./courses/{course}/{section_course}-{sectionIndex}"
                if not os.path.isdir(currentFolder):
                    os.mkdir(currentFolder)
                continue
            video_title = BeautifulSoup(
                f"{videoEl.get_attribute('innerHTML')}", 'html.parser').find('span', {'class': 'mr-auto'}).getText().strip()
            videoEl.click()
            self._download_video(currentFolder, videoLesson, video_title)

    def start_bot(self):
        driver = self.driver
        driver.get(self.url)
        driver.execute_script(self.script_to_inject)
        listOfCourses = None
        try:
            listOfCourses = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, '/html/body/main/ul[1]/*')))
            print("Page is ready!")
        except TimeoutException:
            close_script(driver, "Loading took too much time!")

        # get course we want
        avaible_courses = []
        for el in listOfCourses:
            course_title = el.find_element(
                By.TAG_NAME, "h5")
            avaible_courses.append(course_title.text)

        selected = select(
            "What course you want do download?",
            choices=avaible_courses,
        ).ask()

        # create path if not exisist else close
        if os.path.isdir(f"./courses/{selected}") == False:
            os.mkdir(f"./courses/{selected}")
        else:
            print(
                f"Course: {selected} alredy exisist, downloading video that are missing.")

        # go to course
        element_to_click = None
        for index, el in enumerate(avaible_courses):
            if selected == el:
                element_to_click = listOfCourses[index]
        element_to_click.click()
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "body > main > div:nth-child(11) > ul > a:nth-child(1)"))).click()

        videosElments = driver.find_elements(
            By.XPATH, """//*[@id="sidebar"]/*""")

        # download
        self._download_videos(len(videosElments), selected)

        driver.close()
        driver.quit()
        print("DONE")

    # def wait_until_bot_finish_downloads(self):
    #     cores = cpu_count()
    #     cycles = math.ceil(len(self.processes) / cores)
    #     for i in range(cycles):
    #         for process in self.processes[i*cores:(i+1)*cores]:
    #             print(i, (i+1)*cores)
    #             process.join()


def main():
    REMOTE_URL = os.getenv('REMOTE_URL')
    bot = Bot(driver=get_web_driver(REMOTE_URL))
    bot.start_bot()
    # bot.wait_until_bot_finish_downloads()


if __name__ == "__main__":
    main()
    # 25ea481c30254c58e5d8de8dc5f4f56c54ed5a56
    """
    function_patterns = [
        # https://github.com/ytdl-org/youtube-dl/issues/29326#issuecomment-865985377
        # https://github.com/yt-dlp/yt-dlp/commit/48416bc4a8f1d5ff07d5977659cb8ece7640dcd8
        # var Bpa = [iha];
        # ...
        # a.C && (b = a.get("n")) && (b = Bpa[0](b), a.set("n", b),
        # Bpa.length || iha("")) }};
        # In the above case, `iha` is the relevant function name
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&.*?\|\|\s*([a-z]+)',
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
    ]"""
