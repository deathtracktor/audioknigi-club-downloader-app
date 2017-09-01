Download multi-part audio books from Audioknigi.club
----------------------------------------------------

## Pre-requisites

* Python3 (https://www.python.org/downloads)
* pip (https://pip.pypa.io/en/stable/installing/)
* virtualenv (https://pypi.python.org/pypi/virtualenv)
* git client (ftp://git.narod.ru)

## Installation (Windows)

* Create a virtual environment, clone the code:
```
virtualenv downloader
cd downloader
git clone https://github.com/deathtracktor/audioknigi-club-downloader-app.git src
```

* Install dependencies:
```
scripts\pip install -r src\requirements.txt
```

* Run the app:
```
cd src
scripts\python app.py
```
* Or build a single-file executable:
```
cd src
pyinstaller app.spec --onefile
```
NB: the current version of PyInstaller (3.2.1) is broken. Use development version instead:
```
pip install https://github.com/pyinstaller/pyinstaller/archive/develop.tar.gz
```

Enjoy!
