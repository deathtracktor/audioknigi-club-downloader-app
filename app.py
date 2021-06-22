"""
    Download complete audio books from audioknigi.ru
"""
from contextlib import contextmanager
from itertools import count
import os
import sys
from time import sleep
from multiprocessing import freeze_support, Process, Queue

import click
import requests
from pathvalidate import sanitize_filename
from seleniumwire import webdriver


def get_book_title(url):
    """Extract the audiobook name from its URL."""
    return sanitize_filename(url.split('/')[-1])


def get_chapter_elements(browser):
    """Get player UI element representing a chapter."""
    selector = '//div[boolean(@data-pos) and boolean(@data-id)]'
    for el in browser.find_elements_by_xpath(selector):
        yield el


def get_current_chapter_url(browser):
    """Get the most recent media request."""
    urls = (r.url for r in reversed(browser.requests))
    mp3_urls = filter(lambda url: url.endswith('.mp3'), urls)
    url = next(mp3_urls)
    return url


@contextmanager
def open_browser(url):
    """Open a web page with Selenium."""
    if getattr(sys, 'frozen', False):
        tmp_path = getattr(sys, '_MEIPASS')
        os.environ['PATH'] += os.pathsep + tmp_path
    fp = webdriver.FirefoxProfile()
    fp.accept_untrusted_certs = True
    fp.set_preference('permissions.default.image', 2)  # disable images
    browser = webdriver.Firefox(firefox_profile=fp)
    browser.get(url)
    try:
        yield browser
    finally:
        browser.close()


def scrape_chapter_metadata(audio_book_url, queue):
    """Scrape chapter URLs and titles."""
    cached = []
    with open_browser(audio_book_url) as browser:
        for el in get_chapter_elements(browser):
            el.click()
            sleep(1)
            url = get_current_chapter_url(browser)
            if url not in cached:
                cached.append(url)
                queue.put(url)
    queue.put(None)


@contextmanager
def get_playlist(audio_book_url):
    """Fetch the complete playlist in background."""
    queue = Queue()
    p = Process(target=scrape_chapter_metadata, args=(audio_book_url, queue,))
    p.start()
    try:
        yield queue
    finally:
        p.join()


def download_chapter(url):
    """Download a chapter."""
    with requests.get(url) as r:
        return r.content


def get_non_blank_path(*dirs):
    """Return the first non-blank directory path."""
    return os.path.abspath(next(filter(bool, dirs)))


def get_or_create_output_dir(dirname, book_title):
    """Create or reuse output directory in a fail-safe manner."""
    path = get_non_blank_path(dirname, book_title, os.getcwd())
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except FileExistsError:
        raise TypeError('"{}" is not a directory.'.format(path))


def contains_files(path):
    """Return True if the directory is not empty."""
    return bool(os.listdir(path))


@click.command()
@click.argument('audio_book_url')
@click.option(
    '-o', '--output-dir', 'output_dir', default=None,
    help=('Download directory. Default: <audio-book-title>')
)
@click.option(
    '-y', '--yes', 'force_overwrite', is_flag=True,
    help='Overwrite existing files without a prompt.'
)
@click.option(
    '-1', '--one-file', 'one_file', is_flag=True,
    help='Merge all book chapters into one file.'
)
def cli(audio_book_url, output_dir, force_overwrite, one_file):
    """Download the complete book."""
    book_title = get_book_title(audio_book_url)
    try:
        path = get_or_create_output_dir(output_dir, book_title)
    except TypeError as exc:
        click.echo(str(exc))
        sys.exit(1)

    if contains_files(path) and not force_overwrite:
        msg = 'The directory "{}" is not empty. Overwite?'.format(path)
        if not click.confirm(msg):
            click.echo('Terminated.')
            sys.exit(0)

    click.echo('Downloading "{}" to "{}"...'.format(audio_book_url, path))

    if one_file:
        output_file = lambda _: open(os.path.join(path, book_title), 'ab')
    else:
        output_file = lambda fname: open(os.path.join(path, fname), 'wb')

    counter = count(1)
    with get_playlist(audio_book_url) as queue:
        while True:
            url = queue.get()
            if url is None:
                break
            chapter = next(counter)
            click.echo('Downloading chapter {}...'.format(chapter))
            with output_file('chapter-{:03d}.mp3'.format(chapter)) as outfile:
                outfile.write(download_chapter(url))

    click.echo('All done!\n')


if __name__ == '__main__':
    # NB: PyInstaller likes this
    multiprocessing.freeze_support()
    cli()
