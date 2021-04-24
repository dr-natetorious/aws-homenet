# Define function directory
ARG FUNCTION_DIR="/var/task"
FROM python:3.9

RUN apt-get -y update && \
  apt-get -y install libgl1-mesa-dev python3-opencv && \
  apt-get -y install net-tools && \
  apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev && \
  rm -rf /var/cache/*

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

WORKDIR ${FUNCTION_DIR}

# Install Dependencies...
COPY requirements.txt .
RUN pip install -r requirements.txt -t ${FUNCTION_DIR}

# Setup application
COPY *.py .
RUN chmod a+x app.py

CMD [ "app.handler" ]