package middleware

import (
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// TenantMiddleware sets the PostgreSQL session variable used by RLS policies.
// Must run after JWTAuth so user_id is already in context.
func TenantMiddleware(db *gorm.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID != "" {
			db.Exec("SET LOCAL app.current_user_id = ?", userID)
		}
		c.Next()
	}
}
