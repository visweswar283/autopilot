package repository

import (
	"github.com/applypilot/backend/internal/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type JobRepository struct {
	db *gorm.DB
}

func NewJobRepository(db *gorm.DB) *JobRepository {
	return &JobRepository{db: db}
}

// ListForUser returns scored jobs for the given user, ordered by score descending.
func (r *JobRepository) ListForUser(userID uuid.UUID, limit, offset int) ([]models.UserJobScore, error) {
	var scores []models.UserJobScore
	err := r.db.
		Where("user_id = ?", userID).
		Preload("Job").
		Order("score DESC").
		Limit(limit).
		Offset(offset).
		Find(&scores).Error
	return scores, err
}

func (r *JobRepository) GetByID(id uuid.UUID) (*models.Job, error) {
	var job models.Job
	err := r.db.First(&job, "id = ?", id).Error
	return &job, err
}

// UpdateUserJobStatus sets approved/skipped/blacklisted for a user+job pair.
func (r *JobRepository) UpdateUserJobStatus(userID, jobID uuid.UUID, status models.JobStatus) error {
	return r.db.Model(&models.UserJobScore{}).
		Where("user_id = ? AND job_id = ?", userID, jobID).
		Update("status", status).Error
}
