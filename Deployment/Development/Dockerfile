FROM python:3-alpine
ENV PYTHONUNBUFFERED 1
RUN mkdir app
RUN apk add ffmpeg opus gcc
WORKDIR app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "__init__.py"]