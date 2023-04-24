# Configurable Real Time Speech Censorship
Policing and AI

Final project for CMPSC 442 by Cole Bianchi, Dante Dodds, Kevin Dong, Nathan Litzinger, Andre Mitrik, Efe Sahin

Biggest Bird Labs, LLC

## Setup

Setup python virtual environment using Python 3.9

### Docker
Install is made easy for all systems using Docker:

First build the image using

`sudo docker build -t biggestbirdlabs/real-time-speech-censorship:{VERSION} .`

Next run the image using

`sudo docker run biggestbirdlabs/real-time-speech-censorship:{VERSION}`

### Linux (Fedora)
Install Python 3.9, sox, and portaudio (This is required) using:

`sudo dnf install python3.9 sox libportaudio2 libportaudiocpp0 portaudio19-dev`

Navigate to your workspace folder and setup the virtual environment:

`virtualenv --python="/usr/bin/python3.9" venv`

Source the environment:

`source venv/bin/activate`

Install pip requirements:

`pip install -r requirements.txt`

Run the code:

`python censor.py`