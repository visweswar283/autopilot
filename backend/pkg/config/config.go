package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port           string
	DatabaseURL    string
	RedisURL       string
	MLServiceURL   string
	JWTS           string
	AWSRegion      string
	S3Bucket       string
	// Email / SMTP
	SMTPHost       string
	SMTPPort       string
	SMTPUser       string
	SMTPPass       string
	SMTPFrom       string
	AppURL         string
	// CORS — comma-separated list of allowed origins
	// e.g. "https://applypilotjobs.com,https://www.applypilotjobs.com"
	// Leave empty or set to "*" to allow all (development only)
	AllowedOrigins string
}

func Load() *Config {
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, reading from environment")
	}

	return &Config{
		Port:           getEnv("PORT", "8080"),
		DatabaseURL:    mustEnv("DATABASE_URL"),
		RedisURL:       getEnv("REDIS_URL", "redis://localhost:6379"),
		MLServiceURL:   getEnv("ML_SERVICE_URL", "http://localhost:8001"),
		JWTS:           mustEnv("JWT_SECRET"),
		AWSRegion:      getEnv("AWS_REGION", "us-east-1"),
		S3Bucket:       getEnv("S3_BUCKET", "applypilot-docs"),
		SMTPHost:       getEnv("SMTP_HOST", ""),
		SMTPPort:       getEnv("SMTP_PORT", "587"),
		SMTPUser:       getEnv("SMTP_USER", ""),
		SMTPPass:       getEnv("SMTP_PASS", ""),
		SMTPFrom:       getEnv("SMTP_FROM", "noreply@applypilotjobs.com"),
		AppURL:         getEnv("APP_URL", "https://www.applypilotjobs.com"),
		AllowedOrigins: getEnv("ALLOWED_ORIGINS", "https://applypilotjobs.com,https://www.applypilotjobs.com"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func mustEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatalf("required env var %s is not set", key)
	}
	return v
}
