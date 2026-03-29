package repository

import (
	"errors"
	"time"

	"github.com/applypilot/backend/internal/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type UserRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) Create(user *models.User) error {
	return r.db.Create(user).Error
}

func (r *UserRepository) FindByEmail(email string) (*models.User, error) {
	var user models.User
	err := r.db.Where("email = ?", email).First(&user).Error
	return &user, err
}

func (r *UserRepository) FindByID(id uuid.UUID) (*models.User, error) {
	var user models.User
	err := r.db.First(&user, "id = ?", id).Error
	return &user, err
}

func (r *UserRepository) UpdatePassword(userID uuid.UUID, hashedPassword string) error {
	return r.db.Exec("UPDATE users SET password = ? WHERE id = ?", hashedPassword, userID).Error
}

func (r *UserRepository) CreateResetToken(userID uuid.UUID, token string, expiresAt time.Time) error {
	return r.db.Exec(
		"INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
		userID, token, expiresAt,
	).Error
}

func (r *UserRepository) FindValidResetToken(token string) (uuid.UUID, error) {
	var userID uuid.UUID
	err := r.db.Raw(
		"SELECT user_id FROM password_reset_tokens WHERE token = ? AND used = false AND expires_at > NOW()",
		token,
	).Scan(&userID).Error
	if err != nil {
		return uuid.Nil, err
	}
	if userID == uuid.Nil {
		return uuid.Nil, errors.New("token not found")
	}
	return userID, nil
}

func (r *UserRepository) MarkResetTokenUsed(token string) error {
	return r.db.Exec("UPDATE password_reset_tokens SET used = true WHERE token = ?", token).Error
}
