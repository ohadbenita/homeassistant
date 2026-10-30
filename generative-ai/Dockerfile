FROM python:3.14-slim

WORKDIR /app
COPY app.py requirements.txt /app/
RUN python -m pip install --no-cache-dir -r requirements.txt

# Expose the port that the Flask app will run on (5000 by default)
EXPOSE 5000

CMD ["python", "app.py"]
