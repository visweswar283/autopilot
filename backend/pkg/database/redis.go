package database

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
)

func NewRedis(redisURL string) *redis.Client {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("failed to parse redis URL: %v", err)
	}

	rdb := redis.NewClient(opts)

	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}

	return rdb
}
