import time
import requests
import os
import subprocess

from bs4 import BeautifulSoup
from logger.log_manager import LogManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver import Proxy

from sekai import config

CHARACTERS = [None, '一歌', '咲希', '穂波', '志歩',
              'みのり', '遥', '愛莉', '雫',
              'こはね', '杏', '彰人', '冬弥',
              '司', 'えむ', '寧々', '類',
              '奏', 'まふゆ', '絵名', '瑞希',
              'ミク', 'リン', 'レン', 'ルカ', 'MEIKO', 'KAITO'
            ]
CHARACTERS_ROMAJI = [None, 'ICHIKA', 'SAKI', 'HONAMI', 'SHIHO',
              'MINORI', 'HARUKA', 'AIRI', 'SHIZUKU',
              'KOHANE', 'AN', 'AKITO', 'TOYA',
              'TSUKASA', 'EMU', 'NENE', 'RUI',
              'KANADE', 'MAFUYU', 'ENA', 'MIZUKI',
              'MIKU', 'RIN', 'LEN', 'LUKA', 'MEIKO', 'KAITO'
            ]

class Voice:

    def __init__(self):
        # self.config = configparser.ConfigParser()
        # config_file_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'setting_fetch.ini')

        # 下面的内容是对config.ini文件的读取
        self.config = config
        self.url = config.get('DEFAULT', 'url')
        self.interval = config.getint('DEFAULT', 'interval')
        self.selected_characters = config.get('DEFAULT', 'selected_characters')
        self.convert = config.getboolean('DEFAULT', 'convert')
        self.proxy = config.getboolean('DEFAULT', 'proxy')
        self.proxy_ip = config.get('DEFAULT', 'proxy_ip')
        self.proxy_port = config.get('DEFAULT', 'proxy_port')
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

    # 获取mp3的url列表
    @property
    def get_dl_list(self):

        # 初始化浏览器
        url = self.url
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument(f'user-agent={self.user_agent}')

        # 设置内置默认代理参数
        proxy_ip = '127.0.0.1'
        proxy_port = '7890'

        # 判别 config 的 proxy 字段是否为 true
        if self.proxy:
            proxy = Proxy({
                'proxyType': 'MANUAL',
                'httpProxy': f'{proxy_ip}:{proxy_port}',
                'sslProxy': f'{proxy_ip}:{proxy_port}',
            })
            chrome_options.add_argument('--proxy-server=%s' % proxy.httpProxy)
        else:
            chrome_options.add_argument('--proxy-server=direct://')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # 显式等待，等待 JavaScript 加载完成
        wait = WebDriverWait(driver, 30)
        wait.until(ec.presence_of_element_located((By.TAG_NAME, 'body')))

        # 等待页面上某个元素加载完成
        # wait.until(ec.presence_of_element_located((By.XPATH, "//div[@class='MuiContainer-root MuiContainer-maxWidthLg css-1qos7gm']")))

        # 获取网页源代码，并且进行解析
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 查找具有特定类的a标签，其href属性就是我们需要的链接
        mp3_tags = soup.find_all('a', class_='MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineAlways MuiButtonBase-root MuiFab-root MuiFab-circular MuiFab-sizeSmall MuiFab-default MuiFab-root MuiFab-circular MuiFab-sizeSmall MuiFab-default css-4mybps')
        dl_list = [ {'mp3_url': mp3_tag.get('href'),
                      'character':mp3_tag.parent.parent.parent.previous_sibling.find('span', class_='MuiChip-label MuiChip-labelMedium css-9iedg7').text.strip(),
                      'text':mp3_tag.parent.parent.parent.previous_sibling.find('p', class_='MuiTypography-root MuiTypography-body1 css-5kc7yo').text.strip().replace('\n', '').replace('\u3000', '')}
                      for mp3_tag in mp3_tags if mp3_tag.parent.parent.parent.previous_sibling.find('p', class_='MuiTypography-root MuiTypography-body1 css-5kc7yo') is not None]
        # 其父元素的父元素的父元素的上一个兄弟元素中包含了当前角色名及文本
        driver.quit()

        return dl_list

    # 过滤dl_list，只保留指定角色
    def filter_dl_list(self, dl_list):
        selected_characters = self.selected_characters.split(' ')
        new_list = []
        for item in dl_list:
            need_download = False
            for selected_character in selected_characters:
                if CHARACTERS[int(selected_character)] == item['character']:
                    need_download = True
            if  need_download:
                new_list.append(item)

        return new_list

    # 下载mp3
    def download_then_annotate(self, dl_list):
        log_manager = LogManager()

        # 获取当前脚本所在的目录
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resource')

        # 不存在目录即创建
        if not os.path.exists(path):
            os.mkdir(path)

        # 遍历并进行下载获取到的资源文件
        for item in dl_list:
            filename = item['mp3_url'].split('/')[-1]
            charpath = os.path.join(path, CHARACTERS_ROMAJI[CHARACTERS.index(item['character'])])
            if not os.path.exists(charpath):
                os.mkdir(charpath)
            filepath = os.path.join(charpath, filename)
            if os.path.exists(filepath) or os.path.exists(filepath.replace('.mp3', '.wav')):
                log_manager.log(f'{filename} 已存在，跳过下载')
                continue
            response = requests.get(item['mp3_url'])
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # 获取mp3_list中项目数量，并且输出现在正在下载第几个文件
            log_manager.log(f'正在下载第 {dl_list.index(item) + 1} 个文件，共 {len(dl_list)} 个文件')
            log_manager.log(f'下载完成 {filename}')

            if self.convert:
                command = ['ffmpeg', '-i', filepath, filepath.replace('.mp3', '.wav')]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode == 0:
                    log_manager.log(f'转换完成 {filename.replace(".mp3", ".wav")}')
                    os.remove(filepath)
                    filepath = filepath.replace('.mp3', '.wav')

            annopath = os.path.join(charpath, 'dataset_mapping.list')
            with open(annopath, 'a') as f:
                f.write(f'{filepath}|{CHARACTERS_ROMAJI[CHARACTERS.index(item['character'])]}|ja|{item['text']}\n')

            # 显式等待，使得下载请求不过于频繁
            time.sleep(self.interval)
