"""
Download complete audio books from audioknigi.ru
"""

from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path, PurePosixPath
import os
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from typing import Callable, Mapping

from Crypto.Cipher import AES
import click
import ffmpeg  # type:ignore[import-untyped]
import m3u8  # type:ignore[import-untyped]
import requests
from pathvalidate import sanitize_filename  # type:ignore
from selenium.webdriver.firefox.options import Options
from selenium import webdriver  # type:ignore
from streamable import Stream, star
from tenacity import (
    Retrying,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)


@dataclass
class Chapter:
    """
    A downladable, decrypted book chapter.
    """

    segment: m3u8.Segment
    key: bytes

    @property
    def name(self) -> str:
        """
        Return the chapter's file name.
        """
        path = urlparse(self.segment.absolute_uri).path
        return PurePosixPath(path).name

    @cached_property
    def decrypt(self) -> Callable[[bytes], bytes]:
        """
        Return an AES decryptor function for the chapter.
        """
        iv = bytes.fromhex(self.segment.key.iv.lstrip('0x'))
        return AES.new(self.key, AES.MODE_CBC, IV=iv).decrypt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(requests.exceptions.ConnectionError),
        after=lambda s: click.echo(
            f'Waiting for server response [{ s.attempt_number }]'
        ),
    )
    def download(self, prefix: str) -> Path:
        """
        Download the chapter, decrypt and save to the specified path.
        """
        path = Path(prefix) / self.name
        with open(path, mode='wb') as file:
            for chunk in requests.get(self.segment.absolute_uri, stream=True, timeout=10):
                file.write(self.decrypt(chunk))
        return path


def get_book_title(url: str) -> str:
    """
    Extract the audiobook name from its URL.
    """
    return sanitize_filename(url.split('/')[-1])


def get_m3u8_url(browser) -> str:
    """
    Return the first URL containing the `.m3u8` path suffix.
    """
    perf_log = browser.execute_script('return window.performance.getEntries();')
    for entry in perf_log:
        url = entry['name']
        if urlparse(url).path.endswith('.m3u8'):
            return url
    raise FileNotFoundError


@contextmanager
def open_browser(url):
    """
    Open a web page with Selenium.
    """
    if getattr(sys, 'frozen', False):
        tmp_path = getattr(sys, '_MEIPASS')
        os.environ['PATH'] += os.pathsep + tmp_path
    opt = Options()
    opt.add_argument('-headless')
    browser = webdriver.Firefox(options=opt)
    browser.get(url)
    try:
        yield browser
    finally:
        browser.close()


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
        for retry_no, attempt in enumerate(Retrying(**retry_opt), start=1):
            with attempt, suppress(RetryError):
                return get_m3u8_url(browser)
            click.echo(f'Waiting for playlist [{ retry_no }]')
    raise click.Abort('Failed to fetch playlist.')


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


@cache
def get_key(segment: m3u8.Segment) -> bytes:
    """
    Download decryption key for the segment.
    """
    resp = requests.get(segment.key.absolute_uri, timeout=10)
    if resp.status_code != 200:
        raise click.Abort('Could not fetch decryption key.')
    return resp.content


def convert_to_mp3(stream_path: str) -> None:
    """
    Attempt to convert .ts file to .mp3 with `ffmpeg`.
    """
    ts_path = Path(stream_path)
    mp3_path = ts_path.with_suffix('.mp3')
    try:
        ffmpeg.input(str(ts_path)).output(str(mp3_path)).run()
    except FileNotFoundError:
        click.secho(
            "Warning: `ffmpeg` is not installed, won't convert to MP3.", fg='magenta'
        )
    else:
        ts_path.unlink()


def confirm_overwrite(overwrite: bool, path: Path) -> None:
    """
    Confirm overwriting of non-empty target directories.
    """
    if overwrite:
        return
    for _ in path.iterdir():
        if click.confirm(f'The directory "{ path }" is not empty. Overwrite?'):
            return
        raise click.Abort('Terminated.')


@click.command(context_settings={'show_default': True})
@click.argument('audio_book_url')
@click.option(
    '-o',
    '--output-dir',
    'output_dir',
    default=None,
    help='Path to download directory',
)
@click.option(
    '-y',
    '--yes',
    'force_overwrite',
    is_flag=True,
    help='Overwrite existing files without a prompt',
)
@click.option('-c', '--concurrency', type=int, default=8, help='Download segments concurrently')
def cli(audio_book_url: str, output_dir: str, force_overwrite: bool, concurrency: int):
    """
    Download the complete book.
    """
    book_title = get_book_title(audio_book_url)
    path = get_or_create_output_dir(output_dir, book_title)
    confirm_overwrite(force_overwrite, path)
    click.secho('Fetching book metadata, please stand by...', fg='green')
    playlist_url = get_signed_playlist_url(audio_book_url)
    segments = m3u8.load(playlist_url).segments
    with (
        TemporaryDirectory() as tmp_path,
        open((path / book_title).with_suffix('.ts'), mode='wb') as merged,
    ):
        keys = (
            Stream(segments)
            .map(get_key, concurrency=concurrency)
            .observe('keys')
        )
        segments = (
            Stream(zip(segments, keys))
            .map(star(lambda seg, key: Chapter(segment=seg, key=key)))
            .map(lambda c: c.download(prefix=tmp_path), concurrency=concurrency)
            .observe('segments')
            .map(lambda file: file.read_bytes())
            .foreach(merged.write)
            .observe('files')
        )
        click.secho('Downloading segments...', fg='yellow')
        segments.count()
    convert_to_mp3(merged.name)
    click.secho(f'Finished, check the { path } directory.\n', fg='green')


if __name__ == '__main__':
    # pylint:disable=no-value-for-parameter
    cli()
