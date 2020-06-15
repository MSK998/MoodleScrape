#   __  __                 _ _       _____
#  |  \/  |               | | |     / ____|
#  | \  / | ___   ___   __| | | ___| (___   ___ _ __ __ _ _ __   ___
#  | |\/| |/ _ \ / _ \ / _` | |/ _ \\___ \ / __| '__/ _` | '_ \ / _ \
#  | |  | | (_) | (_) | (_| | |  __/____) | (__| | | (_| | |_) |  __/
#  |_|  |_|\___/ \___/ \__,_|_|\___|_____/ \___|_|  \__,_| .__/ \___|
#                                                        | |
#                                                        |_|
#
#                                                         Version 1.0
#
#                                                   Mark Scott-Kiddie
#
#  ==================================================================
#
#  Copyright (C) 2020 Mark Scott-Kiddie
#
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  ==================================================================
#

import requests
import re
import os
from lxml import html
from bs4 import BeautifulSoup
from mimetypes import guess_extension

session_requests = requests.session()
login_url = "https://campusmoodle.rgu.ac.uk/login/index.php"

result = session_requests.get(login_url)

tree = html.fromstring(result.text)
authenticity_token = list(set(tree.xpath("//input[@name='logintoken']/@value")))[0]

payload = {
    "logintoken": authenticity_token,
    "username": input("Moodle Username\n"),
    "password": input("Moodle Password\n")
}

result = session_requests.post(
    login_url,
    data=payload,
    headers=dict(referer=login_url)
)

scrape_url = input("Moodle Course URL\n")

scrape_req = session_requests.get(
    scrape_url,
    headers=dict(referer=login_url)
)

soup = BeautifulSoup(scrape_req.content.decode('UTF-8'), features="lxml")
title = soup.h1.get_text().replace(" ", "_")

if not os.path.exists(title):
    os.makedirs(title)

for links in soup.find_all("div", {"class": "activityinstance"}):
    if re.search("http://campusmoodle.rgu.ac.uk/mod/resource/view.php\?id=?.+", links.a.get('href')):
        print(links.a.get('href') + "\t\t" + links.find("span", {"class": "instancename"}).get_text())

        content = session_requests.get(
            links.a.get('href'),
            headers=dict(referer=scrape_url),
            stream=True
        )

        filename = links.find("span", {"class": "instancename"}) \
            .get_text().lower().replace("/", "_").replace(" file", "").replace(" ", "_")

        if "Content-Disposition" in content.headers and ".ipynb" in content.headers['Content-Disposition']:
            filename += ".ipynb"

        elif "application/octet-stream" in content.headers['Content-Type']:
            filename += ".exe"

        else:
            if guess_extension(content.headers['Content-Type']) is None:
                pass

            else:
                filename += guess_extension(content.headers['Content-Type'])

        iterator = 1
        stepped_filename = filename

        while os.path.isfile(title + '/' + stepped_filename):
            print("Filename already exists... Stepping filename")
            stepped_filename = filename.split(".")[0] + "(" + str(iterator) + ")." + filename.split(".")[1]
            iterator += 1

        if stepped_filename.__ne__(filename):
            filename = stepped_filename

        with open(title + "/" + filename, "wb") as f:
            for chunk in content.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    elif re.search("http://campusmoodle.rgu.ac.uk/mod/folder/view.php\?id=?.+", links.a.get('href')):
        print(links.a.get('href') + "\t\t" + links.find("span", {"class": "instancename"}).get_text())

        folder_page = session_requests.get(
            links.a.get('href'),
            headers=dict(referer=scrape_url),
            stream=True
        )

        folder_soup = BeautifulSoup(folder_page.content.decode('UTF-8'), features="lxml")

        for files in folder_soup.find_all("span", {"class": "fp-filename-icon"}):
            if re.search("http://campusmoodle.rgu.ac.uk/pluginfile.php/(\w+)/mod_folder/content/?.+",
                         files.a.get('href')):

                print("\t\t" + files.a.get('href') + "\t\t" + files.find("span", {"class": "fp-filename"}).get_text())

                filename = files.find("span", {"class": "fp-filename"}).get_text().lower()

                iterator = 1
                stepped_filename = filename

                while os.path.isfile(title + '/' + stepped_filename):
                    print("Filename already exists... Stepping filename")
                    stepped_filename = filename.split(".")[0] + "(" + str(iterator) + ")." + filename.split(".")[1]
                    iterator += 1

                if stepped_filename.__ne__(filename):
                    filename = stepped_filename

                with open(title + "/" + filename, "wb") as f:
                    for chunk in folder_page.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
