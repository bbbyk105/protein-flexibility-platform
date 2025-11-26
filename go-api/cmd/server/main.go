// cmd/server/main.go
package main

import (
	"log"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"protein-flex-api/internal/handlers"
	"protein-flex-api/internal/middleware"
	"protein-flex-api/internal/services"
)

func main() {
	// 環境変数取得
	port := getEnv("PORT", "3001")
	storageDir := getEnv("STORAGE_DIR", "./storage")

	// ストレージディレクトリ作成
	if err := os.MkdirAll(filepath.Join(storageDir, "uploads"), 0755); err != nil {
		log.Fatalf("Failed to create uploads directory: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(storageDir, "results"), 0755); err != nil {
		log.Fatalf("Failed to create results directory: %v", err)
	}

	// Fiberアプリ作成
	app := fiber.New(fiber.Config{
		BodyLimit: 100 * 1024 * 1024, // 100MB (PDBファイル用)
		AppName:   "Protein Flexibility API v1.0.0",
	})

	// ミドルウェア設定
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} - ${method} ${path} (${latency})\n",
	}))
	app.Use(recover.New())
	app.Use(middleware.SetupCORS())

	// サービス初期化
	analyzerService := services.NewAnalyzerService(storageDir)

	// ハンドラー初期化
	analyzeHandler := handlers.NewAnalyzeHandler(analyzerService)
	resultsHandler := handlers.NewResultsHandler(analyzerService)

	// ルーティング設定
	api := app.Group("/api")

	// ヘルスチェック
	api.Get("/health", resultsHandler.HandleHealthCheck)

	// 解析エンドポイント
	api.Post("/analyze", analyzeHandler.HandleAnalyze)

	// 結果取得エンドポイント
	api.Get("/results/:job_id", resultsHandler.HandleGetResult)
	api.Get("/status/:job_id", resultsHandler.HandleGetStatus)

	// ルートパス
	app.Get("/", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"service": "Protein Flexibility Analysis API",
			"version": "1.0.0",
			"endpoints": fiber.Map{
				"health":  "GET /api/health",
				"analyze": "POST /api/analyze (multipart/form-data: pdb_file, chain_id, pdb_id)",
				"status":  "GET /api/status/:job_id",
				"results": "GET /api/results/:job_id",
			},
		})
	})

	// サーバー起動
	log.Printf("🚀 Server starting on port %s", port)
	log.Printf("📁 Storage directory: %s", storageDir)
	log.Printf("🔬 Python flex-analyze command must be available in PATH")
	log.Printf("📊 Access API documentation at http://localhost:%s", port)
	
	if err := app.Listen(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

// getEnv は環境変数を取得（デフォルト値あり）
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
