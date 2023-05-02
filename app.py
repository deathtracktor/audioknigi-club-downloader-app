"""
    Download complete audio books from audioknigi.ru
"""
from contextlib import contextmanager
from functools import partial
from itertools import count
from pathlib import Path
import os
import sys
from urllib.parse import urlparse

from typing import Callable, Iterable

from Crypto.Cipher import AES
import click
import m3u8  # type:ignore
import requests
from pathvalidate import sanitize_filename  # type:ignore
from selenium.webdriver.firefox.options import Options
from seleniumwire import webdriver  # type:ignore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def get_book_title(url: str) -> str:
    """
    Extract the audiobook name from its URL.
    """
    return sanitize_filename(url.split('/')[-1])


@retry(stop=stop_after_attempt(20), wait=wait_fixed(5),
       retry=retry_if_exception_type(FileNotFoundError))
def get_m3u8_url(browser) -> str:
    """
    Return the first URL containing the `.m3u8` path suffix.
    """
    urls = (r.url for r in reversed(browser.requests))
    for url in urls:
        if urlparse(url).path.endswith('.m3u8'):
            return url
    raise FileNotFoundError('No m3u8 playlist.')


def get_signed_playlist_url(url: str) -> str:
    """
    Open book page in the browser, get the signed playlist URL.
    """
    with open_browser(url) as browser:
        return get_m3u8_url(browser)


@contextmanager
def open_browser(url):
    """
    Open a web page with Selenium.
    """
    if getattr(sys, 'frozen', False):
        tmp_path = getattr(sys, '_MEIPASS')
        os.environ['PATH'] += os.pathsep + tmp_path
    opt = Options()
    opt.add_argument('-headless')  # run in a headless mode
    opt.set_preference('permissions.default.image', 2)  # disable images
    browser = webdriver.Firefox(options=opt)
    browser.get(url)
    try:
        yield browser
    finally:
        browser.close()


def get_or_create_output_dir(dirname: str, book_title: str) -> Path:
    """
    Create or reuse output directory in a fail-safe manner.
    """
    dirs = (dirname, book_title, str(Path.cwd()))
    path = Path(next(filter(bool, dirs))).resolve()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        raise TypeError(f'"{ path }" is not a directory.')
    return path


def contains_files(path: Path) -> bool:
    """
    Return True if the directory is not empty.
    """
    for _ in path.iterdir():
        return True
    return False


def file_factory(prefix: Path, title: str, merge: bool) -> Iterable[Callable]:
    """
    A factory producing file openers for the audio segments.
    Always append to one single file if segment merging is requested.
    """
    mode = 'ab' if merge else 'wb'
    for index in count(start=1):
        stem = f'{title}' if merge else f'{title}-{index:03}'
        path = (prefix / stem).with_suffix('.mp3')
        yield partial(open, path, mode)


def get_key(url: str) -> bytes:
    """Download decryption key."""
    resp = requests.get(url)
    assert resp.status_code == 200, 'Could not fetch decryption key.'
    return resp.content


def make_cipher_for_segment(segment):
    """
    Initialize an AES decryptor.
    """
    key = get_key(segment.key.absolute_uri)
    iv = bytes.fromhex(segment.key.iv.lstrip('0x'))
    return AES.new(key, AES.MODE_CBC, IV=iv)


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
    path = get_or_create_output_dir(output_dir, book_title)
    if contains_files(path) and not force_overwrite:
        msg = f'The directory "{ path }" is not empty. Overwite?'
        if not click.confirm(msg):
            click.echo('Terminated.')
            sys.exit(0)
    click.echo(f'Downloading "{ audio_book_url }" to "{ path }"...')
    playlist_url = get_signed_playlist_url(audio_book_url)
    segments = m3u8.load(playlist_url).segments
    openers = file_factory(path, book_title, merge=one_file)
    for n, [segment, opener] in enumerate(zip(segments, openers), start=1):
        cipher = make_cipher_for_segment(segment)
        with opener() as file:
            click.echo(f'Downloading segment { n }/{ len(segments) }...')
            for chunk in requests.get(segment.absolute_uri, stream=True):
                file.write(cipher.decrypt(chunk))
    click.echo('All done!\n')


if __name__ == '__main__':
    cli()
