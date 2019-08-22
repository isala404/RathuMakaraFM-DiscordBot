FROM python:3
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y ffmpeg libopus-dev
RUN mkdir app
WORKDIR app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "__init__.py"]