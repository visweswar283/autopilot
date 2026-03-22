package repository

import (
	"github.com/applypilot/backend/internal/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ApplicationRepository struct {
	db *gorm.DB
}

func NewApplicationRepository(db *gorm.DB) *ApplicationRepository {
	return &ApplicationRepository{db: db}
}

func (r *ApplicationRepository) List(userID uuid.UUID, limit, offset int) ([]models.Application, error) {
	var apps []models.Application
	err := r.db.
		Where("user_id = ?", userID).
		Preload("Job").
		Preload("Resume").
		Order("last_updated DESC").
		Limit(limit).
		Offset(offset).
		Find(&apps).Error
	return apps, err
}

func (r *ApplicationRepository) GetByID(userID, appID uuid.UUID) (*models.Application, error) {
	var app models.Application
	err := r.db.
		Where("id = ? AND user_id = ?", appID, userID).
		Preload("Job").
		Preload("Resume").
		First(&app).Error
	return &app, err
}

func (r *ApplicationRepository) Create(app *models.Application) error {
	return r.db.Create(app).Error
}

func (r *ApplicationRepository) UpdateStatus(id uuid.UUID, status models.ApplicationStatus) error {
	return r.db.Model(&models.Application{}).
		Where("id = ?", id).
		Update("status", status).Error
}
