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
    """Prompt user for a y/n answer"""
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

    fullPathDir = os.path.abspath(args.outputDir)

    #Check outputDir
    if os.path.exists(fullPathDir):
        #outputDir Exists
        if not os.path.isdir(fullPathDir):
            #outputPath is not a directory
            print("{} exists, and is not a directory!".format(fullPathDir))
            exit(1)
        elif os.listdir(fullPathDir) and not args.overwrite:
            #outputPath is a directory, is not empty and overwrite flag is off
            if not yes_or_no('Directory <{}> exists. Overwrite?'.format(fullPathDir)):
                #Prompt for overwrite returned NO
                sys.exit(1)
            else:
                #Prompt for overwrite returned YES
                print("overwriting files in <{}>\n".format(fullPathDir))
    else:
      #outputDir does not exist - create directory
      print("Creating directory <{}>".format(fullPathDir))
      os.makedirs(fullPathDir)

    print("\nDownloading audiobook from {} to <{}>\n".format(args.audioBookURL,
                                                           fullPathDir))

    try:
        with open_browser(args.audioBookURL) as browser:
              book_id = get_book_id(browser.page_source)
              playlist = get_playist(browser, book_id)

        for url, fname in playlist:
            print('Downloading chapter "{}"'.format(fname))
            with open('{}.mp3'.format(os.path.join(fullPathDir,fname)), 'wb') as outfile:
                outfile.write(download_chapter(url))

        print('All done\n')

    except Exception as e:
      #remove previously created directory
      if (args.cleanup or
          (os.listdir(fullPathDir) and
           yes_or_no('Error encountered. Remove Audiobook directory?')
          )
         ):
          print("Deleting directory <{}>\n".format(fullPathDir))
          shutil.rmtree(fullPathDir)

      #raise the same exception to print the error
      raise e