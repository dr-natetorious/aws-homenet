# Define function directory
ARG FUNCTION_DIR="/var/task"

FROM python:3.8 as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get -y update && \
  apt-get -y install libgl1-mesa-dev python3-opencv && \
  rm -rf /var/cache/apt/*

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy function code
COPY . ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install \
  --target ${FUNCTION_DIR} \
  awslambdaric

RUN pip install \
  --target ${FUNCTION_DIR} \
  -r ${FUNCTION_DIR}/requirements.txt

# Multi-stage build: grab a fresh copy of the base image
FROM public.ecr.aws/lambda/python:3.8

# Install Dependencies...
RUN yum -y update && yum -y install \ 
  mesa-libGL.x86_64 \
  opencv-python.x86_64

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

#ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "handler.process_notification" ]