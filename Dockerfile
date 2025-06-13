FROM python:3.11-slim

WORKDIR /app

# Create log directory
RUN mkdir -p /var/log/notion_updater

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default values for flags that can be overridden
ENV NOTION_TOKEN=""
ENV DATABASE_ID=""
ENV UPDATE_FREQUENCY="5"
ENV LOG_LEVEL="info"

# Create entrypoint script
RUN echo '#!/bin/sh\n\
python notion_updater.py \
  --notion_token="$NOTION_TOKEN" \
  --database_id="$DATABASE_ID" \
  --update_frequency="$UPDATE_FREQUENCY" \
  --log_dir=/var/log/notion_updater \
  --log_level="$LOG_LEVEL"' > /app/entrypoint.sh && \
  chmod +x /app/entrypoint.sh

# Run the script
ENTRYPOINT ["/app/entrypoint.sh"]
