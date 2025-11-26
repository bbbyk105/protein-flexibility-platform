// internal/middleware/cors.go
package middleware

import (
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
)

// SetupCORS はCORSミドルウェアをセットアップ
func SetupCORS() fiber.Handler {
	return cors.New(cors.Config{
		AllowOrigins:     "*", // 本番環境では具体的なオリジンを指定
		AllowMethods:     "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization",
		AllowCredentials: false,
	})
}
