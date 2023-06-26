from random_user_agent.params import SoftwareName, OperatingSystem
from random_user_agent.user_agent import UserAgent
from seleniumwire import webdriver
from seleniumwire.webdriver import ChromeOptions
from selenium.common import WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from pytube import YouTube
import ffmpeg
import os
import sys
import io
import contextlib
import requests
import re


def get_random_useragent():
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value,
                         OperatingSystem.LINUX.value]

    user_agent_rotator = UserAgent(
        software_names=software_names, operating_systems=operating_systems, limit=100)
    user_agent = user_agent_rotator.get_random_user_agent()
    return user_agent


def get_web_driver(remoteUrl="http://localhost:4444") -> webdriver.Chrome:
    options = ChromeOptions()
    # options.add_argument("--headless") #this remove chrome open visually
    options.add_argument("--log-level=3")
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    prefs = {"intl.accept_languages": 'en_US,en',
             "credentials_enable_service": False,
             "profile.password_manager_enabled": False,
             "profile.default_content_setting_values.notifications": 2,
             "download_restrictions": 3}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option('extensionLoadTimeout', 120000)
    options.add_argument(f"user-agent={get_random_useragent()}")
    options.add_argument("--mute-audio")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-features=UserAgentClientHint')
    options.add_argument("--disable-web-security")
    webdriver.DesiredCapabilities.CHROME['loggingPrefs'] = {
        'driver': 'OFF', 'server': 'OFF', 'browser': 'OFF'}

    # disable images
    chrome_prefs = {}
    options.experimental_options["prefs"] = chrome_prefs
    chrome_prefs["profile.default_content_settings"] = {"images": 2}

    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(5)
    return driver


def close_script(driver: webdriver.Chrome, msg: str):
    driver.close()
    driver.quit()
    print(msg)
    os.abort()


def Download_from_youtube_link(link: str, folder: str, videoLesson: int):
    yt = YouTube(link)
    audio_filename = f"audio-{videoLesson}.mp3"
    video_filename = f"video-{videoLesson}.mp4"
    title = re.sub(r'[^\w\-_\. ]', '_', yt.title)
    output_file_path = f"{folder}/{title}-{videoLesson}.mp4"

    if os.path.isfile(output_file_path):
        print(output_file_path, " alredy downloaded!")
        return None

    stream_audio = yt.streams.filter(
        only_audio=True).order_by("abr").last()
    stream_audio.download(output_path=folder, filename=audio_filename)
    audio = ffmpeg.input(f"{folder}/{audio_filename}")

    stream_video = yt.streams.filter(
        only_video=True).order_by("resolution").last()
    stream_video.download(output_path=folder, filename=video_filename)
    video = ffmpeg.input(f"{folder}/{video_filename}")

    ffmpeg.output(audio, video, output_file_path).run()

    os.remove(f"{folder}/{video_filename}")
    os.remove(f"{folder}/{audio_filename}")


class Download_from_viemo_link:
    def __init__(self, video_url: str, audio_url: str, folder: str, videoLesson: int, video_title: str):
        audio_filename = f"audio-{videoLesson}.mp4"
        video_filename = f"video-{videoLesson}.mp4"
        output_file_path = f"{folder}/{video_title}-{videoLesson}.mp4"
        if os.path.isfile(output_file_path):
            print(output_file_path, " alredy downloaded!")
            return None
        self.download_video(video_url, folder, video_filename)
        self.download_video(audio_url, folder, audio_filename)

        audio = ffmpeg.input(f"{folder}/{audio_filename}")
        video = ffmpeg.input(f"{folder}/{video_filename}")

        print("Downloading file:%s" % output_file_path)
        ffmpeg.output(audio, video, output_file_path).run()
        print("%s downloaded!\n" % output_file_path)

        os.remove(f"{folder}/{video_filename}")
        os.remove(f"{folder}/{audio_filename}")

    def download_video(self, url, folder, file_name):
        r = requests.get(url, stream=True)
        open(f"{folder}/{file_name}", "wb").write(r.content)
