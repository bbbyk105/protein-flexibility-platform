.PHONY: help build run test clean

help:
	@echo "Available commands:"
	@echo "  make build    - Build the Go API server"
	@echo "  make run      - Run the server (dev mode)"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean build artifacts and storage"

build:
	@echo "Building Go API..."
	go mod tidy && go build -o bin/flex-api cmd/server/main.go
	@echo "Build complete: bin/flex-api"

run:
	@echo "Starting DSA API server..."
	go run cmd/server/main.go \
		--port 8080 \
		--storage ../storage \
		--python python3

test:
	go test ./...

clean:
	rm -rf bin
	rm -rf ../storage/*
	@echo "Cleaned build artifacts and storage"