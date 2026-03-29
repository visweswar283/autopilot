package middleware

import (
	"net/http"
	"strings"

	"github.com/applypilot/backend/internal/auth"
	"github.com/gin-gonic/gin"
)

func JWTAuth(jwtSecret string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Accept token from Authorization header OR ?token= query param (SSE clients)
		var token string
		header := c.GetHeader("Authorization")
		if strings.HasPrefix(header, "Bearer ") {
			token = strings.TrimPrefix(header, "Bearer ")
		} else if q := c.Query("token"); q != "" {
			token = q
		} else {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing token"})
			return
		}
		claims, err := auth.ParseAccessToken(token, jwtSecret)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
			return
		}

		c.Set("user_id", claims.UserID.String())
		c.Set("plan", claims.Plan)
		c.Next()
	}
}
