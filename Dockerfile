FROM python:3.8

RUN mkdir -p /usr/src/app/
WORKDIR /usr/src/app

COPY . /usr/src/app/
RUN pip install wheel --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir

CMD ["python", "src/main.py"]
