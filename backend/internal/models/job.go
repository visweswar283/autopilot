package models

import (
	"time"

	"github.com/google/uuid"
)

type Job struct {
	ID                    uuid.UUID  `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	Portal                string     `gorm:"not null"                                       json:"portal"`
	ExternalID            string     `gorm:"not null"                                       json:"external_id"`
	Title                 string     `gorm:"not null"                                       json:"title"`
	Company               string     `gorm:"not null"                                       json:"company"`
	Location              string     `                                                      json:"location"`
	Remote                bool       `                                                      json:"remote"`
	Description           string     `                                                      json:"description"`
	ApplyURL              string     `                                                      json:"apply_url"`
	SalaryMin             int        `                                                      json:"salary_min"`
	SalaryMax             int        `                                                      json:"salary_max"`
	PostedAt              *time.Time `                                                      json:"posted_at"`
	ScrapedAt             time.Time  `gorm:"default:now()"                                  json:"scraped_at"`
	Fingerprint           string     `gorm:"uniqueIndex"                                    json:"fingerprint"`
	CrossPortalFingerprint string    `gorm:"index"                                          json:"cross_portal_fingerprint"`
	RawData               []byte     `gorm:"type:jsonb"                                     json:"-"`
}

type JobStatus string

const (
	JobStatusNew         JobStatus = "new"
	JobStatusApproved    JobStatus = "approved"
	JobStatusSkipped     JobStatus = "skipped"
	JobStatusBlacklisted JobStatus = "blacklisted"
)

// UserJobScore is the per-user view of a job (score + status)
type UserJobScore struct {
	UserID   uuid.UUID `gorm:"type:uuid;primaryKey" json:"user_id"`
	JobID    uuid.UUID `gorm:"type:uuid;primaryKey" json:"job_id"`
	Score    float64   `gorm:"not null"             json:"score"`
	Status   JobStatus `gorm:"default:'new'"        json:"status"`
	ScoredAt time.Time `gorm:"default:now()"        json:"scored_at"`

	Job Job `gorm:"foreignKey:JobID" json:"job,omitempty"`
}
