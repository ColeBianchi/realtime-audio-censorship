# Configurable Real Time Speech Censorship
Policing and AI

Final project for CMPSC 442 by Cole Bianchi, Dante Dodds, Kevin Dong, Nathan Litzinger, Andre Mitrik, Efe Sahin

Biggest Bird Labs, LLC

## Setup

Setup python virtual environment using Python

### Linux (Fedora)
This guide is specific to Fedora but should be adaptable to any system.

Install required dependencies using:

```
dnf -y update && \
    dnf -y install python3 && \
    dnf -y install python3-pip && \
    dnf -y install sox && \
    dnf -y install pulseaudio && \
	dnf -y install alsa-lib alsa-utils && \
	dnf -y install portaudio portaudio-devel && \
	dnf -y install python3-pyaudio && \
    dnf -y install gcc
```

Navigate to your workspace folder and setup the virtual environment:

`virtualenv --python="/usr/bin/python" venv`

Source the environment:

`source venv/bin/activate`

Install pip requirements:

`pip install -r requirements.txt`

Run the code:

`python censor.py`