// internal/handlers/results.go
package handlers

import (
	"github.com/gofiber/fiber/v2"
	"protein-flex-api/internal/models"
	"protein-flex-api/internal/services"
)

type ResultsHandler struct {
	analyzerService *services.AnalyzerService
}

// NewResultsHandler は新しいResultsHandlerを作成
func NewResultsHandler(analyzerService *services.AnalyzerService) *ResultsHandler {
	return &ResultsHandler{
		analyzerService: analyzerService,
	}
}

// HandleGetResult は解析結果を取得（単一PDB用）
func (h *ResultsHandler) HandleGetResult(c *fiber.Ctx) error {
	jobID := c.Params("job_id")
	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "job_id_required",
			Message: "job_id is required",
		})
	}

	result, err := h.analyzerService.GetResult(jobID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.ErrorResponse{
			Error:   "result_not_found",
			Message: err.Error(),
		})
	}

	return c.JSON(result)
}

// HandleGetUniProtResult はUniProt解析結果を取得
func (h *ResultsHandler) HandleGetUniProtResult(c *fiber.Ctx) error {
	jobID := c.Params("job_id")
	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "job_id_required",
			Message: "job_id is required",
		})
	}

	result, err := h.analyzerService.GetUniProtResult(jobID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.ErrorResponse{
			Error:   "result_not_found",
			Message: err.Error(),
		})
	}

	return c.JSON(result)
}

// HandleGetStatus はジョブステータスを取得
func (h *ResultsHandler) HandleGetStatus(c *fiber.Ctx) error {
	jobID := c.Params("job_id")
	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "job_id_required",
			Message: "job_id is required",
		})
	}

	status, err := h.analyzerService.GetJobStatus(jobID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.ErrorResponse{
			Error:   "status_not_found",
			Message: err.Error(),
		})
	}

	return c.JSON(status)
}

// HandleHealth はヘルスチェック
func (h *ResultsHandler) HandleHealth(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"status":  "ok",
		"service": "protein-flexibility-api",
		"version": "1.0.0",
	})
}
