# Use a lightweight Python base
FROM python:3.11-slim

# Install Nginx and clean up logs
RUN apt-get update && apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy your requirements and install them
# (If you don't have a requirements.txt, we install them directly)
RUN pip install requests python-dotenv

# Copy your script and the entrypoint script
COPY version_check.py .
COPY entrypoint.sh .
# .env is copied for local testing, but usually handled by docker-compose
COPY .env . 

# Give execution rights to the entrypoint script
RUN chmod +x entrypoint.sh

# Link Nginx logs to stdout/stderr so you can see them in Docker logs
RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

# Expose port 80
EXPOSE 80

# Run the entrypoint script
CMD ["./entrypoint.sh"]