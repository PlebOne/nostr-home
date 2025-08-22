# Multi-stage build for Go relay
FROM golang:1.21-bullseye AS builder

# Set working directory
WORKDIR /app

# Install dependencies for CGO (SQLite)
RUN apt-get update && apt-get install -y \
    gcc \
    libc6-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application with CGO enabled for SQLite
ENV CGO_ENABLED=1
RUN go build -o relay-server main.go

# Final stage - use Debian slim for compatibility
FROM debian:bullseye-slim

# Install SQLite and other runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    sqlite3 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 relay && \
    useradd -r -u 1001 -g relay relay

# Set working directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/relay-server .

# Create data directory and set permissions
RUN mkdir -p /app/data && \
    chown -R relay:relay /app

# Switch to non-root user
USER relay

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Run the relay
CMD ["./relay-server"]
