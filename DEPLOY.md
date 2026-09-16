# Build and deployment notes

The Spring Boot application serves both the REST API and the static dashboard.
The Python pipeline is an offline build step; it is not required on the web
server unless predictions are refreshed there.

## Production build

From the repository root:

```bash
cd backend
./mvnw clean package
```

The runnable application is created at:

```text
backend/target/nfl-game-predictor-api-1.0.0.jar
```

The frontend is packaged inside the JAR. The generated `data/` directory stays
external so predictions can be refreshed without changing source code.

## Run the packaged application

From `backend/`:

```bash
java -jar target/nfl-game-predictor-api-1.0.0.jar
```

The default data location is `../data`. To run from another directory, provide
an absolute artifact directory:

```bash
NFL_DATA_DIR=/absolute/path/to/nfl-game-predictor/data \
  java -jar backend/target/nfl-game-predictor-api-1.0.0.jar
```

The server listens on port 8080 by default. Hosting providers can override it
with Spring Boot's `SERVER_PORT` environment variable.

## Deployment checklist

Before publishing a new build:

```bash
source .venv/bin/activate
python -m pytest
cd backend
./mvnw test
./mvnw clean package
```

Then verify:

- `data/data_contract.json` and all five generated artifacts are deployed
- `GET /api/health` returns `{"status":"ok", ...}`
- `/` loads the dashboard and team selection works
- no `.venv/`, `target/`, IDE metadata, or secrets are included

## Refresh predictions

From the repository root:

```bash
source .venv/bin/activate
python python/build_data.py
```

Redeploy the `data/` files and restart the Java process. Restarting is required
because the backend validates and caches the artifacts once at startup.
