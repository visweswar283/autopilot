package models

import (
	"time"

	"github.com/google/uuid"
)

type Plan string

const (
	PlanFree Plan = "free"
	PlanPro  Plan = "pro"
	PlanTeam Plan = "team"
)

type User struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	Email     string    `gorm:"uniqueIndex;not null"                           json:"email"`
	Password  string    `gorm:"not null"                                       json:"-"`
	Plan      Plan      `gorm:"not null;default:'free'"                        json:"plan"`
	CreatedAt time.Time `                                                      json:"created_at"`
}
