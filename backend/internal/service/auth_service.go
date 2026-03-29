package service

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"log"
	"time"

	"github.com/applypilot/backend/internal/auth"
	"github.com/applypilot/backend/internal/models"
	"github.com/applypilot/backend/internal/repository"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	users     *repository.UserRepository
	profiles  *repository.ProfileRepository
	email     *EmailService
	jwtSecret string
}

func NewAuthService(
	users *repository.UserRepository,
	profiles *repository.ProfileRepository,
	email *EmailService,
	jwtSecret string,
) *AuthService {
	return &AuthService{users: users, profiles: profiles, email: email, jwtSecret: jwtSecret}
}

type RegisterRequest struct {
	Email        string `json:"email"         binding:"required,email"`
	Password     string `json:"password"      binding:"required,min=8"`
	MobileNumber string `json:"mobile_number"`
	Address      string `json:"address"`
	LinkedInURL  string `json:"linkedin_url"`
	PortfolioURL string `json:"portfolio_url"`
	GitHubURL    string `json:"github_url"`
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

	// Auto-create profile with data provided at registration
	if err := s.profiles.Create(&models.Profile{
		UserID:       user.ID,
		Phone:        req.MobileNumber,
		Location:     req.Address,
		LinkedInURL:  req.LinkedInURL,
		PortfolioURL: req.PortfolioURL,
		GitHubURL:    req.GitHubURL,
	}); err != nil {
		log.Printf("[auth] could not create profile for user %s: %v", user.ID, err)
	}

	// Send welcome email (non-fatal)
	if err := s.email.SendWelcome(user.Email, ""); err != nil {
		log.Printf("[auth] welcome email failed for %s: %v", user.Email, err)
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

// ForgotPassword generates a reset token, stores it, and emails the reset link.
// Always returns nil so we never reveal whether the email is registered.
func (s *AuthService) ForgotPassword(email string) error {
	user, err := s.users.FindByEmail(email)
	if err != nil {
		return nil // silently do nothing if email not found
	}

	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return err
	}
	token := hex.EncodeToString(b)

	if err := s.users.CreateResetToken(user.ID, token, time.Now().Add(1*time.Hour)); err != nil {
		return err
	}

	if err := s.email.SendPasswordReset(email, token); err != nil {
		log.Printf("[auth] password reset email failed for %s: %v", email, err)
		return err
	}

	return nil
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
