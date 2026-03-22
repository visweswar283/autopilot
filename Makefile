.PHONY: dev stop migrate-up migrate-down build test lint

dev:
	docker compose up -d

stop:
	docker compose down

migrate-up:
	docker run --rm \
		--network host \
		-v $(PWD)/backend/migrations:/migrations \
		migrate/migrate \
		-path=/migrations \
		-database "$(DATABASE_URL)" \
		up

migrate-down:
	docker run --rm \
		--network host \
		-v $(PWD)/backend/migrations:/migrations \
		migrate/migrate \
		-path=/migrations \
		-database "$(DATABASE_URL)" \
		down 1

build:
	docker compose build

test:
	cd backend && go test ./...

lint:
	cd backend && golangci-lint run
