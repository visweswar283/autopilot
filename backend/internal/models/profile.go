package models

import (
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
)

type Profile struct {
	ID              uuid.UUID      `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	UserID          uuid.UUID      `gorm:"type:uuid;not null;uniqueIndex"                 json:"user_id"`
	FullName        string         `                                                      json:"full_name"`
	Phone           string         `                                                      json:"phone"`
	Location        string         `                                                      json:"location"`
	LinkedInURL     string         `                                                      json:"linkedin_url"`
	GitHubURL       string         `                                                      json:"github_url"`
	PortfolioURL    string         `                                                      json:"portfolio_url"`
	TargetRoles     pq.StringArray `gorm:"type:text[]"                                    json:"target_roles"`
	TargetLocations pq.StringArray `gorm:"type:text[]"                                    json:"target_locations"`
	MinSalary       int            `                                                      json:"min_salary"`
	Skills          pq.StringArray `gorm:"type:text[]"                                    json:"skills"`
	AutoApplyConfig []byte         `gorm:"type:jsonb"                                     json:"auto_apply_config"`
	UpdatedAt       time.Time      `                                                      json:"updated_at"`
}
