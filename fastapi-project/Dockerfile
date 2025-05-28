FROM python:3.12.6

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ .

# Copy the startup script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# Expose the FastAPI port
EXPOSE 8003

# Command to run the application
CMD ["./start.sh"]