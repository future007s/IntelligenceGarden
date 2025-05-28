# FastAPI TDengine Project

This project is a FastAPI application that interfaces with a TDengine database to receive and analyze sensor data. It utilizes Celery for asynchronous task processing and Redis as a message broker.

## Project Structure

```
fastapi-tdengine-project
├── app
│   ├── main.py          # Entry point for the FastAPI application, defines API endpoints.
│   └── tasks.py         # Defines Celery tasks for asynchronous data analysis.
├── Dockerfile            # Dockerfile for building the application image.
├── docker-compose.yml    # Configuration for running multiple Docker containers.
├── requirements.txt      # Python dependencies required for the project.
├── .dockerignore         # Files and directories to ignore when building the Docker image.
└── README.md             # Documentation and instructions for the project.
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fastapi-tdengine-project
   ```

2. Build the Docker image:
   ```
   docker-compose build
   ```

3. Start the application:
   ```
   docker-compose up
   ```

## API Endpoints

- `POST /api/sensor-data`: Receives sensor data and stores it in the TDengine database.
- `GET /api/avg-temperature`: Retrieves the average temperature for the last N hours.

## Celery Tasks

The application includes a Celery task to analyze sensor data for anomalies, such as detecting out-of-range pH values.

## Requirements

- Docker
- Docker Compose

## License

This project is licensed under the MIT License.