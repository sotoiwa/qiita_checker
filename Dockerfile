FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY qiitacheck.py ./

ENV IS_DOCKER TRUE
ENTRYPOINT [ "python", "./qiitacheck.py" ]