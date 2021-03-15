FROM python:3.8

RUN apt-get -y update && apt-get -y install npm zip \
  && npm install -g aws-cdk \
  && /usr/local/bin/python -m pip install --upgrade pip

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN apt-get -y install curl
RUN curl -sSL https://get.docker.com/ | sh

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ship-it.sh /usr/local/bin/ship-it
RUN chmod a+x /usr/local/bin/ship-it