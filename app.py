"""
Download MP3 audio books from akniga.club and alike.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import shutil
from urllib.parse import urlparse
from tempfile import NamedTemporaryFile
from typing import Any, Iterator

import click
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from slugify import slugify


@contextmanager
def open_browser():
    """
    Provide a context manager interfacing the local Firefox browser.
    """
    opt = Options()
    opt.add_argument('-headless')
    browser = webdriver.Firefox(options=opt)
    try:
        yield browser
    finally:
        browser.close()


@dataclass
class Chunk:
    """
    Download chunk and it's metadata.
    """

    size: int
    total: int
    content: bytes


def download(url: str, user_agent: str, cookies: dict) -> Iterator[Chunk]:
    """
    Initiate a streaming GET request to the given URL, emit `Chunk` objects.
    """
    kwargs: dict[str, Any] = {'headers': {'User-Agent': user_agent}, 'cookies': cookies}
    with httpx.stream('GET', url, **kwargs) as resp:
        total = int(resp.headers['Content-Length'])
        yield Chunk(total=total, size=0, content=b'')
        for chunk in resp.iter_bytes():
            yield Chunk(total=total, size=len(chunk), content=chunk)


def make_file_path(prefix: Path, book_url: str) -> str:
    """
    Make a safe file name, prepended with the `prefix` directory.
    """
    file_name = slugify(urlparse(book_url).path, allow_unicode=False)
    return str(prefix / Path(file_name).with_suffix('.mp3'))


@click.command
@click.argument('BOOK_URL')
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=Path.cwd(),
    help='Output directory.',
)
def cli(book_url: str, output_dir: Path):
    """
    Download an audiobook from the given URL.
    """
    click.secho('Fetching book metadata, please stand by...', fg='yellow', bold=True)
    with open_browser() as browser:
        browser.get(book_url)
        player = browser.find_element(By.XPATH, '//audio[@preload="none"]')
        audio_url = player.get_attribute('src')
        cookies = {c['name']: c['value'] for c in browser.get_cookies()}
        user_agent = browser.execute_script('return navigator.userAgent;')
        chunks = download(audio_url, user_agent, cookies)
        click.echo('Downloading audio...')
        with (
            click.progressbar(length=next(chunks).total) as progress,
            NamedTemporaryFile(mode='wb', delete=False) as tmpfile,
        ):
            for chunk in chunks:
                tmpfile.write(chunk.content)
                progress.update(chunk.size)
        path = make_file_path(output_dir, book_url)
        shutil.move(tmpfile.name, path)
        click.secho(f'Saved to "{path}".', fg='green', bold=True)


if __name__ == '__main__':
    cli()
