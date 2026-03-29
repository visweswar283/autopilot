package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
)

// CORS returns a middleware that sets CORS headers.
// allowedOrigins is a comma-separated list of allowed origins.
// If empty or "*", all origins are allowed (development mode).
func CORS(allowedOrigins string) gin.HandlerFunc {
	origins := parseOrigins(allowedOrigins)
	allowAll := len(origins) == 0 || (len(origins) == 1 && origins[0] == "*")

	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		if allowAll {
			c.Header("Access-Control-Allow-Origin", "*")
		} else {
			for _, o := range origins {
				if o == origin {
					c.Header("Access-Control-Allow-Origin", origin)
					c.Header("Vary", "Origin")
					break
				}
			}
		}

		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin,Content-Type,Authorization")
		c.Header("Access-Control-Max-Age", "86400")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	}
}

func parseOrigins(raw string) []string {
	var result []string
	for _, o := range strings.Split(raw, ",") {
		o = strings.TrimSpace(o)
		if o != "" {
			result = append(result, o)
		}
	}
	return result
}
