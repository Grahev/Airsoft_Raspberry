
# Use balenalib Python image for Raspberry Pi Zero W compatibility
FROM balenalib/raspberry-pi-python:3.9


# Install system dependencies (add/remove as needed)
RUN apt-get update && apt-get install -y \
    git mosquitto mosquitto-clients curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Set working directory
WORKDIR /app


# Copy requirements and install Python dependencies first for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code
COPY . .


# Make setup script executable (if needed)
RUN chmod +x setup_airsoft_full.sh


# Expose the port your app runs on
EXPOSE 8000

# Default command to run the app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
