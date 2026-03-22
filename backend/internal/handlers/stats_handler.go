package handlers

import (
	"net/http"

	"github.com/applypilot/backend/internal/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type StatsHandler struct {
	db *gorm.DB
}

func NewStatsHandler(db *gorm.DB) *StatsHandler {
	return &StatsHandler{db: db}
}

func (h *StatsHandler) Get(c *gin.Context) {
	userID, _ := uuid.Parse(c.GetString("user_id"))

	var stats struct {
		TotalJobs        int64 `json:"total_jobs"`
		ApprovedJobs     int64 `json:"approved_jobs"`
		TotalApplied     int64 `json:"total_applied"`
		TotalInterviews  int64 `json:"total_interviews"`
		TotalOffers      int64 `json:"total_offers"`
	}

	h.db.Model(&models.UserJobScore{}).Where("user_id = ?", userID).Count(&stats.TotalJobs)
	h.db.Model(&models.UserJobScore{}).Where("user_id = ? AND status = 'approved'", userID).Count(&stats.ApprovedJobs)
	h.db.Model(&models.Application{}).Where("user_id = ? AND status = 'applied'", userID).Count(&stats.TotalApplied)
	h.db.Model(&models.Application{}).Where("user_id = ? AND status = 'interview'", userID).Count(&stats.TotalInterviews)
	h.db.Model(&models.Application{}).Where("user_id = ? AND status = 'offer'", userID).Count(&stats.TotalOffers)

	c.JSON(http.StatusOK, stats)
}
