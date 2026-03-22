package models

import (
	"time"

	"github.com/google/uuid"
)

type ApplicationStatus string

const (
	AppStatusQueued    ApplicationStatus = "queued"
	AppStatusApplied   ApplicationStatus = "applied"
	AppStatusViewed    ApplicationStatus = "viewed"
	AppStatusInterview ApplicationStatus = "interview"
	AppStatusOffer     ApplicationStatus = "offer"
	AppStatusRejected  ApplicationStatus = "rejected"
	AppStatusFailed    ApplicationStatus = "failed"
)

type Application struct {
	ID           uuid.UUID         `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	UserID       uuid.UUID         `gorm:"type:uuid;not null;index"                       json:"user_id"`
	JobID        uuid.UUID         `gorm:"type:uuid;not null"                             json:"job_id"`
	ResumeID     uuid.UUID         `gorm:"type:uuid"                                      json:"resume_id"`
	Status       ApplicationStatus `gorm:"default:'queued'"                               json:"status"`
	AppliedAt    *time.Time        `                                                      json:"applied_at"`
	LastUpdated  time.Time         `gorm:"default:now()"                                  json:"last_updated"`
	Notes        string            `                                                      json:"notes"`
	ErrorMessage string            `                                                      json:"error_message,omitempty"`

	Job    Job    `gorm:"foreignKey:JobID"    json:"job,omitempty"`
	Resume Resume `gorm:"foreignKey:ResumeID" json:"resume,omitempty"`
}
