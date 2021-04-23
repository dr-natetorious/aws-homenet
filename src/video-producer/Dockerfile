FROM python:3

WORKDIR /app

# Install Dependencies...
COPY requirements.txt .
RUN pip install -r requirements.txt

# SEtup application
COPY app.py .
RUN chmod a+x app.py

ENTRYPOINT [ "/app/app.py" ]