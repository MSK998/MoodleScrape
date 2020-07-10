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

#Imports all relevant libraries

import requests
import re
import os
from lxml import html
from bs4 import BeautifulSoup
from mimetypes import guess_extension

#Creates an HTTP session
session_requests = requests.session()

#Sets login URL to harvest authentication token
login_url = "https://campusmoodle.rgu.ac.uk/login/index.php"

#GET request to the login page
result = session_requests.get(login_url)

#Harvests XSRF token
tree = html.fromstring(result.text)
authenticity_token = list(set(tree.xpath("//input[@name='logintoken']/@value")))[0]

#Creates a login payload
payload = {
    "logintoken": authenticity_token,
    "username": input("Moodle Username\n"),
    "password": input("Moodle Password\n")
}

#POSTs an HTTP request to the moodle login page
result = session_requests.post(
    login_url,
    data=payload,
    headers=dict(referer=login_url)
)

#Gets input from user for the module link
scrape_url = input("Moodle Course URL\n")

#GETs the module page HTML
scrape_req = session_requests.get(
    scrape_url,
    headers=dict(referer=login_url)
)

#Uses Beautiful Soup 4 to read the returned HTML
soup = BeautifulSoup(scrape_req.content.decode('UTF-8'), features="lxml")

#Finds the title of the module and removes whitespace
title = soup.find("span", {"itemprop": "title"}).get_text().replace(" ", "_")

#Checks local machine if a directory with the same title of module title exists
#If not then it is created
if not os.path.exists(title):
    os.makedirs(title)

#Finds and iterates through all div tags containing the activity instance class
for links in soup.find_all("div", {"class": "activityinstance"}):
    #Searches for downloadable resources
    if re.search("http://campusmoodle.rgu.ac.uk/mod/resource/view.php\?id=?.+", links.a.get('href')):
        
        #Prints the link along with the filename
        print(links.a.get('href') + "\t\t" + links.find("span", {"class": "instancename"}).get_text())

        #GET request to the resource
        content = session_requests.get(
            links.a.get('href'),
            headers=dict(referer=scrape_url),
            stream=True
        )

        #Sets the filename removes whitespace and removes some regex
        filename = links.find("span", {"class": "instancename"}) \
            .get_text().lower().replace("/", "_").replace(" file", "").replace(" ", "_")

        #If a jupyter notebook exists, manually set the file extention
        if "Content-Disposition" in content.headers and ".ipynb" in content.headers['Content-Disposition']:
            filename += ".ipynb"

        #Set file extention to exe is mimetype is application/octet-stream
        elif "application/octet-stream" in content.headers['Content-Type']:
            filename += ".exe"

        #Otherwise guess the file extention
        else:
            #If content type is missing in headers, skip
            if guess_extension(content.headers['Content-Type']) is None:
                pass

            else:
                #Adds the extention to the filename
                filename += guess_extension(content.headers['Content-Type'])

        #Sets up variables for file checking
        iterator = 1
        stepped_filename = filename

        #While the filename exists
        while os.path.isfile(title + '/' + stepped_filename):
            #Print stating the file exists
            print("Filename already exists... Stepping filename")
            
            #Step the filename by splitting and adding a (n) to the file
            stepped_filename = filename.split(".")[0] + "(" + str(iterator) + ")." + filename.split(".")[1]
            #Iterate the number
            iterator += 1

        #If the stepped filename is not equal to the original 
        if stepped_filename.__ne__(filename):
            #Set the filename to the stepped one
            filename = stepped_filename

        #Create a file with the created filename
        with open(title + "/" + filename, "wb") as f:
            #Split the file into chunks
            for chunk in content.iter_content(chunk_size=1024):
                #If a chunk remains 
                if chunk:
                    #Write the chunk to the file
                    f.write(chunk)

    #If a folder exists within the module page
    elif re.search("http://campusmoodle.rgu.ac.uk/mod/folder/view.php\?id=?.+", links.a.get('href')):
        
        #Print the link and folder name
        print(links.a.get('href') + "\t\t" + links.find("span", {"class": "instancename"}).get_text())

        #GET request to the folder link
        folder_page = session_requests.get(
            links.a.get('href'),
            headers=dict(referer=scrape_url),
            stream=True
        )

        #Crates a Beautiful Soup from the response
        folder_soup = BeautifulSoup(folder_page.content.decode('UTF-8'), features="lxml")

        #Finds all span tags with the fp-filename-icon class
        for files in folder_soup.find_all("span", {"class": "fp-filename-icon"}):
            
            #Finds all links leading to a file
            if re.search("http://campusmoodle.rgu.ac.uk/pluginfile.php/(\w+)/mod_folder/content/?.+",
                         files.a.get('href')):
                
                #Prints the link and filename
                print("\t\t" + files.a.get('href') + "\t\t" + files.find("span", {"class": "fp-filename"}).get_text())

                #Gets filename directly from the fp-filename class
                filename = files.find("span", {"class": "fp-filename"}).get_text().lower()

                #Sets up filename iteration vatiables
                iterator = 1
                stepped_filename = filename

                #Checks if file exists
                while os.path.isfile(title + '/' + stepped_filename):
                    #Lets the user know it exists
                    print("Filename already exists... Stepping filename")
                    #Creates a stepped filename
                    stepped_filename = filename.split(".")[0] + "(" + str(iterator) + ")." + filename.split(".")[1]
                    #Iterates
                    iterator += 1

                #Checks if the names are different
                if stepped_filename.__ne__(filename):
                    filename = stepped_filename

                #Creates a new file with the previously created name
                with open(title + "/" + filename, "wb") as f:
                    #Split file into chunks
                    for chunk in folder_page.iter_content(chunk_size=1024):
                        #If a chunk exists
                        if chunk:
                            #Write chunk
                            f.write(chunk)
