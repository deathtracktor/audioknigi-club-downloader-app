"""
    Download complete audio books from audioknigi.ru
"""
from contextlib import contextmanager, suppress
from functools import partial
from itertools import count
from pathlib import Path
import os
import sys
from urllib.parse import urlparse

from typing import Callable, Iterable, Mapping

from Crypto.Cipher import AES
import click
import ffmpeg
import m3u8  # type:ignore
import requests
from pathvalidate import sanitize_filename  # type:ignore
from selenium.webdriver.firefox.options import Options
from seleniumwire import webdriver  # type:ignore
from tenacity import (Retrying, RetryError, retry, retry_if_exception_type,
                      stop_after_attempt, wait_fixed)
import tqdm


def get_book_title(url: str) -> str:
    """
    Extract the audiobook name from its URL.
    """
    return sanitize_filename(url.split('/')[-1])


def get_m3u8_url(browser) -> str:
    """
    Return the first URL containing the `.m3u8` path suffix.
    """
    urls = (r.url for r in reversed(browser.requests))
    for url in urls:
        if urlparse(url).path.endswith('.m3u8'):
            return url
    raise FileNotFoundError


def get_signed_playlist_url(url: str) -> str:
    """
    Open book page in the browser, get the signed playlist URL.
    """
    retry_opt: Mapping = {
        'stop': stop_after_attempt(20),
        'wait': wait_fixed(5),
        'retry': retry_if_exception_type(FileNotFoundError),
    }
    with open_browser(url) as browser:
        for attempt in Retrying(**retry_opt):
            with attempt, suppress(RetryError):
                return get_m3u8_url(browser)
            click.echo(f'Waiting for playlist [{ attempt.attempt_number }]')
    raise click.Abort('Failed to fetch playlist.')


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
        # pylint:disable=raise-missing-from
        raise click.BadParameter(f'"{ path }" is not a directory.')
    return path


def file_factory(prefix: Path, title: str, merge: bool) -> Iterable[Callable]:
    """
    A factory producing file openers for the audio segments.
    Always append to one single file if segment merging is requested.
    """
    mode = 'ab' if merge else 'wb'
    for index in count(start=1):
        stem = f'{title}' if merge else f'{title}-{index:03}'
        path = (prefix / stem).with_suffix('.ts')
        yield partial(open, path, mode)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(3),
       retry=retry_if_exception_type(requests.exceptions.ConnectionError),
       after=lambda s: click.echo(f'Waiting for server response [{ s.attempt_number }]'))
def http_get(url: str, **kwargs) -> requests.Response:
    """
    Make an HTTP get request, return response.
    Retry on connection failures.
    """
    return requests.get(url, timeout=10, **kwargs)


def get_key(url: str) -> bytes:
    """
    Download decryption key.
    """
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise click.Abort('Could not fetch decryption key.')
    return resp.content


def make_cipher_for_segment(segment):
    """
    Initialize an AES decryptor.
    """
    key = get_key(segment.key.absolute_uri)
    iv = bytes.fromhex(segment.key.iv.lstrip('0x'))
    return AES.new(key, AES.MODE_CBC, IV=iv)


def convert_to_mp3(stream_path: Path) -> None:
    """
    Attempt to convert .ts file to .mp3 with `ffmpeg`.
    """
    mp3_path = str(stream_path.with_suffix('.mp3'))
    try:
        ffmpeg.input(stream_path).output(mp3_path).run()
    except FileNotFoundError:
        click.echo("Warning: `ffmpeg` is not installed, won't convert to MP3.")
    else:
        stream_path.unlink()


def confirm_overwrite(overwrite: bool, path: Path) -> None:
    """
    Confirm overwriting of non-empty target directories.
    """
    if overwrite:
        return
    for _ in path.iterdir():
        if click.confirm(f'The directory "{ path }" is not empty. Overwrite?'):
            return
        click.echo('Terminated.')
        raise click.Abort(code=0)


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
def cli(audio_book_url, output_dir, force_overwrite):
    """
    Download the complete book.
    """
    book_title = get_book_title(audio_book_url)
    path = get_or_create_output_dir(output_dir, book_title)
    confirm_overwrite(force_overwrite, path)
    click.echo('Fetching book metadata, please stand by...')
    playlist_url = get_signed_playlist_url(audio_book_url)
    segments = m3u8.load(playlist_url).segments
    stream_path = (path / book_title).with_suffix('.ts')
    with open(stream_path, mode='wb') as file:
        bar_format = 'Downloading segment {n}/{total} [{elapsed}]'
        for segment in tqdm.tqdm(segments, bar_format=bar_format):
            cipher = make_cipher_for_segment(segment)
            for chunk in http_get(segment.absolute_uri, stream=True):
                file.write(cipher.decrypt(chunk))
    convert_to_mp3(stream_path)
    click.echo(f'Finished, check the { path } directory.\n')

if __name__ == '__main__':
    # pylint:disable=no-value-for-parameter
    cli()
