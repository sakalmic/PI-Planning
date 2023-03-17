FROM python:3.8.5
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
EXPOSE 5002
CMD ["python", "main.py"]
