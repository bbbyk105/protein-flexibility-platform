// internal/handlers/analyze_uniprot.go
package handlers

import (
	"fmt"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"protein-flex-api/internal/models"
	"protein-flex-api/internal/services"
)

type UniProtAnalyzeHandler struct {
	analyzerService *services.AnalyzerService
}

// NewUniProtAnalyzeHandler は新しいUniProtAnalyzeHandlerを作成
func NewUniProtAnalyzeHandler(analyzerService *services.AnalyzerService) *UniProtAnalyzeHandler {
	return &UniProtAnalyzeHandler{
		analyzerService: analyzerService,
	}
}

// HandleUniProtAnalyze はUniProt ID を使った自動解析を処理
func (h *UniProtAnalyzeHandler) HandleUniProtAnalyze(c *fiber.Ctx) error {
	// リクエストボディパース
	var req models.UniProtAnalyzeRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "invalid_request",
			Message: fmt.Sprintf("Failed to parse request body: %v", err),
		})
	}

	// UniProt ID バリデーション
	if req.UniProtID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "uniprot_id_required",
			Message: "UniProt ID is required",
		})
	}

	// MaxStructures デフォルト値設定
	if req.MaxStructures <= 0 {
		req.MaxStructures = 20
	}

	// MaxStructures 上限チェック
	if req.MaxStructures > 100 {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "max_structures_exceeded",
			Message: "max_structures must be <= 100",
		})
	}

	// ジョブID生成
	jobID := uuid.New().String()

	// 非同期で解析実行
	go func() {
		if err := h.analyzerService.AnalyzeUniProt(jobID, req.UniProtID, req.MaxStructures); err != nil {
			// エラーログ出力
			fmt.Printf("UniProt analysis failed for job %s: %v\n", jobID, err)
		}
	}()

	// レスポンス返却
	return c.Status(fiber.StatusAccepted).JSON(models.AnalyzeResponse{
		JobID:   jobID,
		Status:  "accepted",
		Message: fmt.Sprintf("UniProt analysis started for %s. Use job_id to check status and retrieve results.", req.UniProtID),
	})
}
