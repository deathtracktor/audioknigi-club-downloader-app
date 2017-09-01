"""
    Download complete audio books from audioknigi.ru
"""
import re
import requests
import sys
from bs4 import BeautifulSoup


CHAPTERS_URL = 'https://audioknigi.club/rest/bid/{}'
USAGE_HELP = '''
    Audioknigi.club book downloader.
    Usage: {0} <url>
        url: a URL of a multi-part audio book.
'''

def get_book_id(url):
    """Get internal book ID."""
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, 'html.parser')
    player = re.compile(r'audioPlayer\((.*)\,')
    script_code = next(filter(lambda el: player.search(el.text), soup.findAll('script')))
    return player.search(str(script_code)).group(1)

    
def get_chapters(book_id):
    """Get chapter info."""
    for chapter in requests.get(CHAPTERS_URL.format(book_id)).json():
        yield chapter['title'], chapter['mp3']


def download_chapter(url):
    """Download a chapter."""
    return requests.get(url).content

# start the app
if __name__ == '__main__':

    if len(sys.argv) != 2:
        print(USAGE_HELP.format(*sys.argv))
        sys.exit(1)
    
    book_url = sys.argv[1]
        
    for fname, url in get_chapters(get_book_id(book_url)):
        print('Downloading chapter {}'.format(fname))
        with open('{}.mp3'.format(fname), 'wb') as outfile:
            outfile.write(download_chapter(url))
            
    print('All done.')

