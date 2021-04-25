# Define function directory
ARG FUNCTION_DIR="/var/task"
FROM public.ecr.aws/lambda/python:3.8

RUN yum -y update && \
  yum -y install mesa-libGL.x86_64 opencv-python.x86_64 && \
  #yum -y install net-tools && \
  # yum install -y \
  #   g++ \
  #   make \
  #   cmake \
  #   unzip \
  #   libcurl4-openssl-dev && \
  rm -rf /var/cache/yum/*

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
