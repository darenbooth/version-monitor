FROM python:3.11-slim
WORKDIR /app

# Install dependencies from the file you created
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the data directory for the SQLite database
RUN mkdir -p /app/data

# Copy the application code
COPY version_check.py .

# Expose the Flask port
EXPOSE 80

# Start the app
CMD ["python", "version_check.py"]