package main

import (
	"log"
	"net/http"

	"github.com/applypilot/backend/internal/handlers"
	"github.com/applypilot/backend/internal/middleware"
	"github.com/applypilot/backend/internal/repository"
	"github.com/applypilot/backend/internal/service"
	"github.com/applypilot/backend/pkg/config"
	"github.com/applypilot/backend/pkg/database"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func main() {
	cfg := config.Load()

	db  := database.NewPostgres(cfg.DatabaseURL)
	rdb := database.NewRedis(cfg.RedisURL)

	// Repositories
	userRepo := repository.NewUserRepository(db)
	jobRepo := repository.NewJobRepository(db)
	appRepo := repository.NewApplicationRepository(db)
	profileRepo := repository.NewProfileRepository(db)

	// Services
	emailSvc := service.NewEmailService(
		cfg.SMTPHost, cfg.SMTPPort, cfg.SMTPUser, cfg.SMTPPass,
		cfg.SMTPFrom, cfg.AppURL,
	)
	authSvc := service.NewAuthService(userRepo, profileRepo, emailSvc, cfg.JWTS)

	// Handlers
	authH := handlers.NewAuthHandler(authSvc)
	jobH    := handlers.NewJobHandler(jobRepo)
	appH    := handlers.NewApplicationHandler(appRepo)
	profileH := handlers.NewProfileHandler(profileRepo)
	statsH  := handlers.NewStatsHandler(db)
	eventsH := handlers.NewEventsHandler(rdb)

	r := gin.Default()
	r.Use(middleware.CORS(cfg.AllowedOrigins))

	// Health + metrics
	r.GET("/health", func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{"status": "ok"}) })
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// Auth routes (public)
	v1 := r.Group("/api/v1")
	{
		auth := v1.Group("/auth")
		{
			auth.POST("/register",        authH.Register)
			auth.POST("/login",           authH.Login)
			auth.POST("/forgot-password", authH.ForgotPassword)
			auth.POST("/reset-password",  authH.ResetPassword)
		}
	}

	// Authenticated routes
	protected := v1.Group("")
	protected.Use(middleware.JWTAuth(cfg.JWTS))
	protected.Use(middleware.TenantMiddleware(db))
	{
		protected.GET("/jobs", jobH.List)
		protected.GET("/jobs/:id", jobH.GetByID)
		protected.PATCH("/jobs/:id/status", jobH.UpdateStatus)

		protected.GET("/applications", appH.List)
		protected.GET("/applications/:id", appH.GetByID)

		protected.GET("/profile", profileH.Get)
		protected.PUT("/profile", profileH.Update)

		protected.GET("/stats", statsH.Get)

		protected.GET("/events/stream", eventsH.Stream)
	}

	log.Printf("Server starting on :%s (allowed origins: %s)", cfg.Port, cfg.AllowedOrigins)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
