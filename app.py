"""
    Download complete audio books from audioknigi.ru
"""
import contextlib
import json
import os
import sys

import click
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def get_playist(browser):
    """Extract the playlist."""
    script = open(os.path.realpath(__file__) + '.js').read()
    browser.execute_script(script)
    playlist_loaded = EC.presence_of_element_located((By.ID, 'book_data'))
    element = WebDriverWait(browser, 60).until(playlist_loaded)
    return json.loads(element.text)

def download_chapter(url):
    """Download a chapter."""
    return requests.get(url).content

def get_audiobook_name(url):
    """Extract the audiobook name from its URL."""
    # TODO: sanitize the path
    return url.split('/')[-1]

def get_full_dirname(dirname, do_overwrite):
    """
    Return absolute path for dirname, and check for existence.
    
    If dirname exists and is not a directory - raise an exception.
    If not empty - prompt before overwriting unless do_overwrite is True.
    """
    full_path_dir = os.path.abspath(dirname)

    if os.path.exists(full_path_dir):
        if not os.path.isdir(full_path_dir):
            click.echo('\n{} exists, and is not a directory!\n'.format(full_path_dir))
            exit(1)
        if os.listdir(full_path_dir) and not do_overwrite:
            if not click.confirm('\nDirectory "{}" exists. Overwrite?'.format(full_path_dir)):
                sys.exit(1)
            else:
                click.echo('Overwriting files in "{}"\n'.format(full_path_dir))
    else:
        click.echo('\nCreating directory "{}"'.format(full_path_dir))
        # TODO: avoid side effects
        os.makedirs(full_path_dir)
    return full_path_dir

def save_byte_data_to_file(full_path_dir, file_name, data):
    open(os.path.join(full_path_dir, file_name), 'wb').write(data)

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('audio_book_url')
@click.option(
    '-o', '--output_dir', 'output_dir', default=None,
    help='Directory the audio book will be dowloaded to. Default: <Audio Book Name>'
)
@click.option(
    '-w', '--overwrite', 'do_overwrite', is_flag=True,
    help='Overwrite existing audiobook directory without asking'
)
def downloader_main(output_dir, do_overwrite, audio_book_url):
    """Download the book."""
    if output_dir is None:
        output_dir = get_audiobook_name(audio_book_url)

    full_path_dir = get_full_dirname(output_dir, do_overwrite)

    msg = '\nDownloading audiobook\n from "{}"\n to "{}"\n'
    click.echo(msg.format(audio_book_url, full_path_dir))

    with open_browser(audio_book_url) as browser:
        book_data = get_playist(browser)
        playlist = tuple((track['mp3'], track['title']) for track in book_data['playlist'])

    save_byte_data_to_file(full_path_dir, '00 - cover.jpg', download_chapter(book_data['cover']))
    save_byte_data_to_file(full_path_dir, '00 - description.txt', str.encode(book_data['description']))

    for url, fname in playlist:
        click.echo('Downloading chapter "{}"'.format(fname))
        save_byte_data_to_file(full_path_dir, fname + '.mp3', download_chapter(url))


    click.echo('All done!\n')

# start the app
if __name__ == '__main__':

    downloader_main()
