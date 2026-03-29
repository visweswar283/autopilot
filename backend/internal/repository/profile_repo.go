package repository

import (
	"github.com/applypilot/backend/internal/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ProfileRepository struct {
	db *gorm.DB
}

func NewProfileRepository(db *gorm.DB) *ProfileRepository {
	return &ProfileRepository{db: db}
}

func (r *ProfileRepository) Create(profile *models.Profile) error {
	return r.db.Create(profile).Error
}

func (r *ProfileRepository) GetByUserID(userID uuid.UUID) (*models.Profile, error) {
	var profile models.Profile
	err := r.db.Where("user_id = ?", userID).First(&profile).Error
	return &profile, err
}

func (r *ProfileRepository) Upsert(profile *models.Profile) error {
	return r.db.Save(profile).Error
}
