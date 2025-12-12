package main

import (
	"flag"
	"log"
	"os"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/yourusername/flex-api/internal/handlers"
	"github.com/yourusername/flex-api/internal/services"
)

func main() {
	// コマンドラインフラグ
	port := flag.String("port", "8080", "Server port")
	storageDir := flag.String("storage", "./storage", "Storage directory for jobs")
	pythonBin := flag.String("python", "python3", "Python binary path")
	flag.Parse()

	// ストレージディレクトリ作成
	if err := os.MkdirAll(*storageDir, 0755); err != nil {
		log.Fatalf("Failed to create storage directory: %v", err)
	}

	// サービス初期化
	jobService := services.NewJobService(*storageDir, *pythonBin)

	// ハンドラー初期化
	h := handlers.NewHandler(jobService)

	// Ginルーター設定
	router := gin.Default()

	// CORS設定
	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"http://localhost:3000", "http://localhost:3001"}
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	config.AllowCredentials = true
	router.Use(cors.New(config))

	// ルート設定
	router.GET("/health", h.HealthCheck)

	api := router.Group("/api/dsa")
	{
		api.POST("/analyze", h.CreateAnalysis)
		api.GET("/status/:job_id", h.GetStatus)
		api.GET("/result/:job_id", h.GetResult)
		api.GET("/jobs/:job_id/heatmap", h.GetHeatmap)
		api.GET("/jobs/:job_id/distance-score", h.GetDistanceScore)
	}

	// サーバー起動
	addr := ":" + *port
	log.Printf("Server starting on %s", addr)
	log.Printf("Storage directory: %s", *storageDir)
	log.Printf("Python binary: %s", *pythonBin)

	if err := router.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
