package handlers

import (
	"net/http"
	"strconv"

	"github.com/applypilot/backend/internal/repository"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type ApplicationHandler struct {
	repo *repository.ApplicationRepository
}

func NewApplicationHandler(repo *repository.ApplicationRepository) *ApplicationHandler {
	return &ApplicationHandler{repo: repo}
}

func (h *ApplicationHandler) List(c *gin.Context) {
	userID, _ := uuid.Parse(c.GetString("user_id"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))

	apps, err := h.repo.List(userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch applications"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"applications": apps})
}

func (h *ApplicationHandler) GetByID(c *gin.Context) {
	userID, _ := uuid.Parse(c.GetString("user_id"))
	appID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid application id"})
		return
	}

	app, err := h.repo.GetByID(userID, appID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "application not found"})
		return
	}

	c.JSON(http.StatusOK, app)
}
