Download multi-part audio books from Audioknigi.club
----------------------------------------------------

## Pre-requisites

* Python3 (https://www.python.org/downloads)
* pip (https://pip.pypa.io/en/stable/installing/)
* virtualenv (https://pypi.python.org/pypi/virtualenv)
* git client (ftp://git.narod.ru)
* Firefox web browser.

## Installation (Windows)

* Create a virtual environment, clone the code:
```
$ git clone https://github.com/deathtracktor/audioknigi-club-downloader-app.git src
$ cd audioknigi-club-downloader-app
$ python -m venv .venv
```

* Activate virtual environment, install dependencies:
```
$ source .venv/bin/activate
# Windows
> .venv\Scripts\activate
```
* Make sure you have the recent version of Firefox installed;
* Download [Geckodriver](https://github.com/mozilla/geckodriver/releases), extract to your current working directory;
* Download and install [ffmpeg](https://ffmpeg.org/) (optional);
* Run the app:
```
cd src
scripts\python app.py
```
* Or build a single-file executable:
```
cd src
pyinstaller app.spec
```

## Enjoy!
