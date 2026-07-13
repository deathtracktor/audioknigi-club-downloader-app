Download audiobooks from akniga.org (former Audioknigi.club)
============================================================

This application downloads audiobooks in MP3 format from akniga.org.
The site periodically changes how audio files are served, which may cause
the downloader to stop working or malfunction. If you encounter this issue,
please open an issue or otherwise let the author know.

## Pre-requisites

* git client (ftp://git.narod.ru)
* Python3 (https://www.python.org/downloads), tested with version 3.13.
* Firefox web browser.

## Installation

* Clone the code:
```sh
git clone https://github.com/deathtracktor/audioknigi-club-downloader-app.git
cd audioknigi-club-downloader-app
```

* Create and activate a virtual envrionment:
```sh
python -m venv .venv
source .venv/bin/activate
```

> In Windows, activate with `.venv\Scripts\activate`

* Make sure you have the recent version of Firefox installed;
* Download [Geckodriver](https://github.com/mozilla/geckodriver/releases),
  extract to your current working directory;

* Print app help:
```sh
$ python app.py --help
````

### Downloading process

The following command will download a book from the provided URL to the current
working directory:

```sh
python app.py https://akniga.org/<path-to-book>
```

You can also specify the output directory as shown:
```sh
python app.py --output-dir=<some local path> https://akniga.org/<path-to-book>
```

## Enjoy!
