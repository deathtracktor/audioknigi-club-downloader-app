ATTENTION!
==========
The current `master` code is no longer working due to massive changes at the web site, which has also moved to a new location.
In the mean time, have a look at the `refactoring` branch.


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
virtualenv downloader
cd downloader
git clone https://github.com/deathtracktor/audioknigi-club-downloader-app.git src
```

* Install dependencies:
```
scripts\pip install -r src\requirements.txt
```
* Download [Geckodriver](https://github.com/mozilla/geckodriver/releases), extract to your current working directory.
* Make sure you have the recent version of Firefox installed.
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
NB: A precompiled Windows 64-bit executable can be found [here](dist/app.exe).

## Enjoy!
