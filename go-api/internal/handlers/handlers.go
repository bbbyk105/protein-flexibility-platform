package handlers

import (
	"net/http"

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
	var params models.AnalysisParams
	if err := c.ShouldBindJSON(&params); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	response, err := h.jobService.CreateJob(params)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

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