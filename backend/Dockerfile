FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/api

FROM alpine:3.20
RUN apk add --no-cache ca-certificates postgresql-client bash

WORKDIR /app
COPY --from=builder /app/server .
COPY --from=builder /app/migrations ./migrations
COPY scripts/migrate.sh ./migrate.sh
RUN chmod +x ./migrate.sh

EXPOSE 8080
# Run migrations then start the server
CMD sh -c "./migrate.sh && ./server"
