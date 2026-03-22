package models

import (
	"time"

	"github.com/google/uuid"
)

type Resume struct {
	ID         uuid.UUID `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	UserID     uuid.UUID `gorm:"type:uuid;not null;index"                       json:"user_id"`
	Name       string    `gorm:"not null"                                       json:"name"`
	S3Key      string    `gorm:"not null"                                       json:"s3_key"`
	IsDefault  bool      `gorm:"default:false"                                  json:"is_default"`
	UploadedAt time.Time `gorm:"default:now()"                                  json:"uploaded_at"`
}
