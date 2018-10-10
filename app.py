"""
    Download complete audio books from audioknigi.ru
"""
import contextlib
import json
import re
import sys

import os
import shutil
import argparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False

# start the app
if __name__ == '__main__':

    #set up command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outputDir',
                        help='Directory the AudioBook will be dowloaded to. Default: <AudioBookName>',
                        metavar='OutputDirectory',
                        type=str)
    parser.add_argument('audioBookURL',
                        help='a URL of a multi-part audio book',
                        metavar='URL')
    parser.add_argument('-w', '--overwrite',
                        help='overwrite existing directory without asking',
                        action='store_true',
                        default=False)
    parser.add_argument('-c', '--cleanup',
                        help='delete outputDir in case of errors',
                        action='store_true',
                        default=False)

    #parse arguments
    args = parser.parse_args()

    #default value for output dir is the book name
    if args.outputDir is None:
        args.outputDir = args.audioBookURL.split('/')[-1]

    #create directory if required
    if not os.path.exists(os.path.abspath(args.outputDir)):
      print ("Creating directory <{}>".format(os.path.abspath(args.outputDir)))
      os.makedirs(os.path.abspath(args.outputDir))

    if (os.listdir(os.path.abspath(args.outputDir)) and not args.overwrite):
        if not yes_or_no('Directory <{}> exists. Overwrite?'.format(os.path.abspath(args.outputDir))):
          sys.exit(1)
    else:
        print("overwriting files in <{}>\n".format(os.path.abspath(args.outputDir)))

    print("\nDownloading audiobook from {} to <{}>\n".format(args.audioBookURL,
                                                           os.path.abspath(args.outputDir)))

    try:
        with open_browser(args.audioBookURL) as browser:
              book_id = get_book_id(browser.page_source)
              playlist = get_playist(browser, book_id)

        for url, fname in playlist:
            print('Downloading chapter "{}"'.format(fname))
            with open('{}.mp3'.format(os.path.join(os.path.abspath(args.outputDir),fname)), 'wb') as outfile:
                outfile.write(download_chapter(url))

        print('All done\n')

    except Exception as e:
      #remove previously created directory
      if (args.cleanup or
          (os.listdir(os.path.abspath(args.outputDir)) and
           yes_or_no('Error encountered. Remove Audiobook directory?')
          )
         ):
          print("Deleting directory <{}>\n".format(os.path.abspath(args.outputDir)))
          shutil.rmtree(os.path.abspath(args.outputDir))

      #raise the same exception to print the error
      raise e