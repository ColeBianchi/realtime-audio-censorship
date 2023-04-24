FROM fedora:latest

#Install python 3.9
RUN dnf -y update && \
    dnf -y install python3.9 && \
    dnf -y install python3-pip && \
	dnf -y install sox && \
	dnf -y install portaudio portaudio-devel python3-pyaudio

#Setup workdir
WORKDIR /app
COPY . /app

#Setup virtual env
RUN pip install virtualenv
RUN virtualenv --python="/usr/bin/python3.9" venv

#Add pip installs
RUN source venv/bin/activate && pip install -r requirements.txt

CMD ["venv/bin/python3.9", "example.py"]
