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
```sh
$ git clone https://github.com/deathtracktor/audioknigi-club-downloader-app.git src
$ cd audioknigi-club-downloader-app
$ python -m venv .venv
```

* Activate virtual environment, install dependencies:
```sh
$ source .venv/bin/activate
# Windows
> .venv\Scripts\activate
```
* Make sure you have the recent version of Firefox installed;
* Download [Geckodriver](https://github.com/mozilla/geckodriver/releases), extract to your current working directory;
* Download and install [ffmpeg](https://ffmpeg.org/) (optional);
* Run the app:
```sh
$ cd src
$ scripts\python app.py
```
* Or build a single-file executable:
```sh
$ cd src
$ pyinstaller app.spec
```

## Installation (Docker/Podman)

To avoid installing bulky dependencies locally, you can use the provided
Docker Compose environment, which also works with Podman Compose.

* Build container images (should only be done once):
  ```sh
  $ docker compose build
  ```
* Run the app:
  ```sh
  $ docker compose run --rm -it downloader <book URL>
  ```
The book will be downloaded into the local `downloads` directory and automatically
converted to MP3 format.

## Enjoy!
