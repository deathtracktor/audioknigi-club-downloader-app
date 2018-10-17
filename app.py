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

import click

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

def get_audiobook_name(url):
    """
    Extract the audiobook name from its url
    """
    return url.split('/')[-1]

def get_full_dirname(dirname, doOverwrite):
    """
    Return absolute path for dirname, and check for existence
    if dirname exists and is not a directory - raise and exception
    if exists and not empty - prompt before overwriting unless doOverwrite is True
    """
    fullPathDir = os.path.abspath(dirname)

    #Check outputDir
    if os.path.exists(fullPathDir):
        #outputDir Exists
        if not os.path.isdir(fullPathDir):
            #outputPath is not a directory
            click.echo("\n{} exists, and is not a directory!\n".format(fullPathDir))
            exit(1)
        elif os.listdir(fullPathDir) and not doOverwrite:
            #outputPath is a directory, is not empty and overwrite flag is off
            if not click.confirm('\nDirectory <{}> exists. Overwrite?'.format(fullPathDir)):
                #Prompt for overwrite returned NO
                sys.exit(1)
            else:
                #Prompt for overwrite returned YES
                click.echo("overwriting files in <{}>\n".format(fullPathDir))
    else:
      #outputDir does not exist - create directory
      click.echo("Creating directory <{}>".format(fullPathDir))
      os.makedirs(fullPathDir)

    return fullPathDir

CLICK_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CLICK_CONTEXT_SETTINGS)
@click.option('-o', '--outputDir', 'outputDir',
              default=None,
              help="Directory the AudioBook will be dowloaded to. Default: <AudioBookName>")
@click.option('-w', '--overwrite', 'doOverwrite',
              is_flag=True,
              help="Overwrite existing audiobook directory without asking")
@click.option('-u', '--url', 'audio_book_url',
              prompt="\nURL of the audiobook",
              help="a URL of a multi-part audio book")
def downloader_main(outputDir, doOverwrite, audio_book_url):

    if outputDir is None:
      outputDir = get_audiobook_name(audio_book_url)

    fullPathDir = get_full_dirname(outputDir, doOverwrite)

    click.echo("\nDownloading audiobook\n"
               "from {}\n"
               "to <{}>\n".format(audio_book_url,
                                  fullPathDir))

    with open_browser(audio_book_url) as browser:
        book_id = get_book_id(browser.page_source)
        playlist = get_playist(browser, book_id)

    for url, fname in playlist:
        click.echo('Downloading chapter "{}"'.format(fname))
        with open('{}.mp3'.format(os.path.join(fullPathDir,fname)), 'wb') as outfile:
            outfile.write(download_chapter(url))


    click.echo('All done\n')

# start the app
if __name__ == '__main__':

    downloader_main()
