FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*
    
# Copy the requirements file from the host to the container
COPY ./requirements.txt ./requirements.txt

# Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install scikit-learn==1.6.1 --timeout=100 --retries=5
# RUN pip install torch==2.7.0 --timeout=100 --retries=5
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code from the host to the container
COPY ./alembic /code/alembic
COPY ./app /code/app
COPY ./alembic.ini /code/alembic.ini

# Copy the startup script
COPY ./start.sh /code/start.sh
RUN chmod +x /code/start.sh

# Secure the app to not run as root
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /code
RUN chown -R appuser /code/app
USER appuser

# Command to run the application using Uvicorn
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5006"]

# Change CMD to use the script
# CMD ["/code/start.sh"]