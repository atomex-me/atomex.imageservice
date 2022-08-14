FROM python:3.9

COPY . /app
COPY favicon.ico /app/static
WORKDIR /app
ENV FLASK_RUN_HOST=0.0.0.0

RUN pip install -r requirements.txt
CMD ["flask", "run", "--port=80"]