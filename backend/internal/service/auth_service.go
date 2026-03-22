package service

import (
	"errors"

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
