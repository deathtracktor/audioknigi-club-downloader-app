"""
    Download complete audio books from audioknigi.ru
"""
import contextlib
import json
import re
import sys

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


USAGE_HELP = '''
    Audioknigi.club book downloader.
    Usage: {0} <url>
        url: a URL of a multi-part audio book.
'''

AJAX_ON_SUCCESS = '''
    $(document).ajaxSuccess(function(event, xhr, opt) {
        if (opt.url.indexOf('ajax/bid') !== -1) {
            $('body').html($('<div />', {
                id: 'playlist',
                text: JSON.parse(xhr.responseText).aItems
            }))
        }
    });
'''

INIT_PLAYER = '$(document).audioPlayer({}, 0)'


@contextlib.contextmanager
def open_browser(url):
    """Open a web page with Selenium."""
    if getattr(sys, 'frozen', False):
        tmp_path = getattr(sys, '_MEIPASS')
        os.environ['PATH'] += os.pathsep + tmp_path
    browser = webdriver.Firefox()
    browser.get(url)
    yield browser
    browser.close()


def get_book_id(html):
    """Get the internal book ID."""
    player = re.compile(r'audioPlayer\((.*)\,')
    return player.search(html).group(1)


def get_playist(browser, book_id):
    """Extract the playlist."""
    browser.execute_script(AJAX_ON_SUCCESS)
    browser.execute_script(INIT_PLAYER.format(book_id))
    playlist_loaded = EC.presence_of_element_located((By.ID, 'playlist'))
    element = WebDriverWait(browser, 60).until(playlist_loaded)
    return tuple((track['mp3'], track['title']) for track in json.loads(element.text))


def download_chapter(url):
    """Download a chapter."""
    return requests.get(url).content


# start the app
if __name__ == '__main__':

    if len(sys.argv) != 2:
        print(USAGE_HELP.format(*sys.argv))
        sys.exit(1)

    book_url = sys.argv[1]

    with open_browser(book_url) as browser:
        book_id = get_book_id(browser.page_source)
        playlist = get_playist(browser, book_id)

    for url, fname in playlist:
        print('Downloading chapter "{}"'.format(fname))
        with open('{}.mp3'.format(fname), 'wb') as outfile:
            outfile.write(download_chapter(url))

    print('All done.')
