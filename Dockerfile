FROM python:3.8-alpine
WORKDIR /app
COPY . /app
 
RUN apk add --no-cache python3-dev openssl-dev libffi-dev gcc musl-dev postgresql-dev && pip3 install --upgrade pip \
    && pip3 --no-cache-dir install -r requirements.txt \
    && apk del --no-cache openssl-dev libffi-dev gcc musl-dev python3-dev 

EXPOSE 8080

ENTRYPOINT ["gunicorn"]
CMD ["-b 0.0.0.0:8080", "-w 3", "rallycall:app", "--log-level=debug"]