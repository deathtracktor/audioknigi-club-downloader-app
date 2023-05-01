"""
    Download complete audio books from audioknigi.ru
"""
from contextlib import contextmanager
import os
import sys
from urllib.parse import urlparse

from Crypto.Cipher import AES
import click
import m3u8
import requests
from pathvalidate import sanitize_filename
from seleniumwire import webdriver
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def get_book_title(url):
    """Extract the audiobook name from its URL."""
    return sanitize_filename(url.split('/')[-1])


@retry(stop=stop_after_attempt(20), wait=wait_fixed(5),
       retry=retry_if_exception_type(FileNotFoundError))
def get_playlist_url(browser):
    """Get the URL of the M3U8 playlist."""
    urls = (r.url for r in reversed(browser.requests))
    for url in urls:
        if urlparse(url).path.endswith('.m3u8'):
            return url
    raise FileNotFoundError('No m3u8 playlist.')


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


def get_key(url):
    """Download decryption key."""
    resp = requests.get(url)
    assert resp.status_code == 200, 'Could not fetch decryption key.'
    return resp.content


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
        raise TypeError(f'"{ path }" is not a directory.')


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
        msg = f'The directory "{ path }" is not empty. Overwite?'
        if not click.confirm(msg):
            click.echo('Terminated.')
            sys.exit(0)

    click.echo(f'Downloading "{ audio_book_url }" to "{ path }"...')

    if one_file:
        output_file = lambda _: open(os.path.join(path, book_title), 'ab')
    else:
        output_file = lambda fname: open(os.path.join(path, fname), 'wb')

    # FIXME: HERE ARE DRAGONS
    # TODO: download segments concurrently
    with open_browser(audio_book_url) as browser:
        playlist_url = get_playlist_url(browser)

    playlist = m3u8.load(playlist_url)
    for n, segment in enumerate(playlist.segments, start=1):
        key = get_key(segment.key.absolute_uri)
        iv = bytes.fromhex(segment.key.iv.lstrip('0x'))
        cipher = AES.new(key, AES.MODE_CBC, IV=iv)
        with output_file(f'chapter-{n:03d}.mp3') as outfile:
            click.echo(f'Downloading chapter { n }/{ len(playlist.segments) }...')
            for chunk in requests.get(segment.absolute_uri, stream=True):
                outfile.write(cipher.decrypt(chunk))

    click.echo('All done!\n')


if __name__ == '__main__':
    cli()
