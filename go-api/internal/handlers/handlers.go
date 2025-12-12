package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/yourusername/flex-api/internal/models"
	"github.com/yourusername/flex-api/internal/services"
)

type Handler struct {
	jobService *services.JobService
}

func NewHandler(jobService *services.JobService) *Handler {
	return &Handler{
		jobService: jobService,
	}
}

// CreateAnalysis は解析ジョブを作成
// POST /api/dsa/analyze
func (h *Handler) CreateAnalysis(c *gin.Context) {
	// デバッグ: リクエストボディを読み取り
	bodyBytes, err := io.ReadAll(c.Request.Body)
	if err != nil {
		log.Printf("[DEBUG] CreateAnalysis - Failed to read request body: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read request body"})
		return
	}
	
	// リクエストボディをログ出力
	log.Printf("[DEBUG] CreateAnalysis - Request body (raw): %s", string(bodyBytes))
	
	// リクエストボディを再度設定（ShouldBindJSONで使用するため）
	c.Request.Body = io.NopCloser(io.Reader(bytes.NewReader(bodyBytes)))
	
	// JSONをパースしてログ出力
	var rawParams map[string]interface{}
	if err := json.Unmarshal(bodyBytes, &rawParams); err == nil {
		log.Printf("[DEBUG] CreateAnalysis - Parsed JSON: %+v", rawParams)
	} else {
		log.Printf("[DEBUG] CreateAnalysis - Failed to parse JSON: %v", err)
	}
	
	var params models.AnalysisParams
	if err := c.ShouldBindJSON(&params); err != nil {
		log.Printf("[DEBUG] CreateAnalysis - Binding error: %v", err)
		log.Printf("[DEBUG] CreateAnalysis - Binding error type: %T", err)
		
		// エラーの詳細を取得
		if validationErr, ok := err.(*gin.Error); ok {
			log.Printf("[DEBUG] CreateAnalysis - Validation error details: %+v", validationErr)
		}
		
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	// デバッグ: パースされたパラメータをログ出力
	log.Printf("[DEBUG] CreateAnalysis - Parsed params:")
	log.Printf("  UniProtIDs: %s", params.UniProtIDs)
	if params.Method != nil {
		log.Printf("  Method: %s", *params.Method)
	} else {
		log.Printf("  Method: nil")
	}
	if params.SeqRatio != nil {
		log.Printf("  SeqRatio: %f", *params.SeqRatio)
	} else {
		log.Printf("  SeqRatio: nil")
	}
	if params.NegativePDBID != nil {
		log.Printf("  NegativePDBID: %s", *params.NegativePDBID)
	} else {
		log.Printf("  NegativePDBID: nil")
	}
	if params.CisThreshold != nil {
		log.Printf("  CisThreshold: %f", *params.CisThreshold)
	} else {
		log.Printf("  CisThreshold: nil")
	}
	if params.Export != nil {
		log.Printf("  Export: %t", *params.Export)
	} else {
		log.Printf("  Export: nil")
	}
	if params.Heatmap != nil {
		log.Printf("  Heatmap: %t", *params.Heatmap)
	} else {
		log.Printf("  Heatmap: nil")
	}
	if params.ProcCis != nil {
		log.Printf("  ProcCis: %t", *params.ProcCis)
	} else {
		log.Printf("  ProcCis: nil")
	}
	if params.Overwrite != nil {
		log.Printf("  Overwrite: %t", *params.Overwrite)
	} else {
		log.Printf("  Overwrite: nil")
	}

	response, err := h.jobService.CreateJob(params)
	if err != nil {
		log.Printf("[DEBUG] CreateAnalysis - CreateJob error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	log.Printf("[DEBUG] CreateAnalysis - Job created successfully: %s", response.JobID)
	c.JSON(http.StatusOK, response)
}

// GetStatus はジョブの状態を取得
// GET /api/dsa/status/:job_id
func (h *Handler) GetStatus(c *gin.Context) {
	jobID := c.Param("job_id")
	if jobID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "job_id is required"})
		return
	}

	status, err := h.jobService.GetJobStatus(jobID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, status)
}

// GetResult はジョブの結果を取得
// GET /api/dsa/result/:job_id
func (h *Handler) GetResult(c *gin.Context) {
	jobID := c.Param("job_id")
	if jobID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "job_id is required"})
		return
	}

	result, err := h.jobService.GetResult(jobID)
	if err != nil {
		// ジョブが未完了の場合
		if err.Error() == "job not completed: pending" || err.Error() == "job not completed: processing" {
			c.JSON(http.StatusAccepted, gin.H{"error": "Job not yet completed"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

// HealthCheck はヘルスチェック
// GET /health
func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
		"time":   gin.H{},
	})
}

// GetHeatmap はジョブのヒートマップ PNG を返す
// GET /api/dsa/jobs/:job_id/heatmap
func (h *Handler) GetHeatmap(c *gin.Context) {
	jobID := c.Param("job_id")
	if jobID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "job_id is required"})
		return
	}

	jobDir := filepath.Join(h.jobService.StorageDir(), jobID)
	
	// Notebook DSAのヒートマップファイル名パターン: {uniprotid}_{seq_ratio}_heatmap.png
	// まず、標準のheatmap.pngを確認
	heatmapPath := filepath.Join(jobDir, "heatmap.png")
	
	// 標準のheatmap.pngが存在しない場合は、Notebook DSA形式を検索
	if _, err := os.Stat(heatmapPath); err != nil {
		// ディレクトリ内の_heatmap.pngファイルを検索
		if entries, err := os.ReadDir(jobDir); err == nil {
			for _, entry := range entries {
				if !entry.IsDir() && strings.HasSuffix(entry.Name(), "_heatmap.png") {
					heatmapPath = filepath.Join(jobDir, entry.Name())
					log.Printf("[DEBUG] GetHeatmap - Found Notebook DSA heatmap: %s", entry.Name())
					break
				}
			}
		}
	}

	if _, err := os.Stat(heatmapPath); err != nil {
		if os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "heatmap not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to stat heatmap"})
		return
	}

	c.File(heatmapPath)
}

// GetDistanceScore は distance–score プロット PNG を返す
// GET /api/dsa/jobs/:job_id/distance-score
func (h *Handler) GetDistanceScore(c *gin.Context) {
	jobID := c.Param("job_id")
	if jobID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "job_id is required"})
		return
	}

	jobDir := filepath.Join(h.jobService.StorageDir(), jobID)
	
	// まず、標準のdistance_score.pngを確認
	pngPath := filepath.Join(jobDir, "distance_score.png")
	
	// 標準のdistance_score.pngが存在しない場合は、Notebook DSA形式を検索
	if _, err := os.Stat(pngPath); err != nil {
		// ディレクトリ内のdistance_score.pngファイルを検索
		if entries, err := os.ReadDir(jobDir); err == nil {
			for _, entry := range entries {
				if !entry.IsDir() && entry.Name() == "distance_score.png" {
					pngPath = filepath.Join(jobDir, entry.Name())
					log.Printf("[DEBUG] GetDistanceScore - Found distance_score.png: %s", entry.Name())
					break
				}
			}
		}
	}

	if _, err := os.Stat(pngPath); err != nil {
		if os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "distance_score.png not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to stat distance_score.png"})
		return
	}

	c.File(pngPath)
}
