package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
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

// BeforeCreate ensures the UUID is always set before inserting,
// guarding against drivers or test setups that don't use DB defaults.
func (u *User) BeforeCreate(tx *gorm.DB) error {
	if u.ID == uuid.Nil {
		u.ID = uuid.New()
	}
	return nil
}
