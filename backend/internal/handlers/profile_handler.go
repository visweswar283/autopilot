package handlers

import (
	"net/http"

	"github.com/applypilot/backend/internal/models"
	"github.com/applypilot/backend/internal/repository"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ProfileHandler struct {
	repo *repository.ProfileRepository
}

func NewProfileHandler(repo *repository.ProfileRepository) *ProfileHandler {
	return &ProfileHandler{repo: repo}
}

func (h *ProfileHandler) Get(c *gin.Context) {
	userID, _ := uuid.Parse(c.GetString("user_id"))

	profile, err := h.repo.GetByUserID(userID)
	if err == gorm.ErrRecordNotFound {
		c.JSON(http.StatusOK, gin.H{"profile": nil})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch profile"})
		return
	}

	c.JSON(http.StatusOK, profile)
}

func (h *ProfileHandler) Update(c *gin.Context) {
	userID, _ := uuid.Parse(c.GetString("user_id"))

	var profile models.Profile
	if err := c.ShouldBindJSON(&profile); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	profile.UserID = userID

	if err := h.repo.Upsert(&profile); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update profile"})
		return
	}

	c.JSON(http.StatusOK, profile)
}
