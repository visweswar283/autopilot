package service

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"time"

	"github.com/applypilot/backend/internal/auth"
	"github.com/applypilot/backend/internal/models"
	"github.com/applypilot/backend/internal/repository"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	users     *repository.UserRepository
	jwtSecret string
}

func NewAuthService(users *repository.UserRepository, jwtSecret string) *AuthService {
	return &AuthService{users: users, jwtSecret: jwtSecret}
}

type RegisterRequest struct {
	Email    string `json:"email"    binding:"required,email"`
	Password string `json:"password" binding:"required,min=8"`
}

type LoginRequest struct {
	Email    string `json:"email"    binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
}

func (s *AuthService) Register(req RegisterRequest) (*models.User, *TokenPair, error) {
	hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		return nil, nil, err
	}

	user := &models.User{
		Email:    req.Email,
		Password: string(hash),
		Plan:     models.PlanFree,
	}
	if err := s.users.Create(user); err != nil {
		return nil, nil, errors.New("email already registered")
	}

	tokens, err := s.generateTokenPair(user)
	return user, tokens, err
}

func (s *AuthService) Login(req LoginRequest) (*models.User, *TokenPair, error) {
	user, err := s.users.FindByEmail(req.Email)
	if err != nil {
		return nil, nil, errors.New("invalid credentials")
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(req.Password)); err != nil {
		return nil, nil, errors.New("invalid credentials")
	}

	tokens, err := s.generateTokenPair(user)
	return user, tokens, err
}

func (s *AuthService) generateTokenPair(user *models.User) (*TokenPair, error) {
	access, err := auth.GenerateAccessToken(user.ID, string(user.Plan), s.jwtSecret)
	if err != nil {
		return nil, err
	}
	refresh, err := auth.GenerateRefreshToken(user.ID, s.jwtSecret)
	if err != nil {
		return nil, err
	}
	return &TokenPair{AccessToken: access, RefreshToken: refresh}, nil
}

// ForgotPassword generates a reset token and returns it.
// In production wire this to an email sender; for now we return the token
// in the response so it can be tested without SMTP configured.
func (s *AuthService) ForgotPassword(email string) (string, error) {
	user, err := s.users.FindByEmail(email)
	if err != nil {
		// Don't reveal whether the email exists
		return "", nil
	}

	// Generate a cryptographically random 32-byte token
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	token := hex.EncodeToString(b)

	if err := s.users.CreateResetToken(user.ID, token, time.Now().Add(1*time.Hour)); err != nil {
		return "", err
	}

	return token, nil
}

// ResetPassword validates the token and updates the password.
func (s *AuthService) ResetPassword(token, newPassword string) error {
	userID, err := s.users.FindValidResetToken(token)
	if err != nil {
		return errors.New("invalid or expired reset token")
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(newPassword), bcrypt.DefaultCost)
	if err != nil {
		return err
	}

	if err := s.users.UpdatePassword(userID, string(hash)); err != nil {
		return err
	}

	return s.users.MarkResetTokenUsed(token)
}
