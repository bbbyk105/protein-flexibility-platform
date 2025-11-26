// internal/handlers/analyze.go
package handlers

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"protein-flex-api/internal/models"
	"protein-flex-api/internal/services"
)

type AnalyzeHandler struct {
	analyzerService *services.AnalyzerService
}

// NewAnalyzeHandler は新しいAnalyzeHandlerを作成
func NewAnalyzeHandler(analyzerService *services.AnalyzerService) *AnalyzeHandler {
	return &AnalyzeHandler{
		analyzerService: analyzerService,
	}
}

// HandleAnalyze はPDBファイルのアップロードと解析を処理
func (h *AnalyzeHandler) HandleAnalyze(c *fiber.Ctx) error {
	// ファイルアップロード取得
	file, err := c.FormFile("pdb_file")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "file_required",
			Message: "PDB file is required",
		})
	}

	// ファイル拡張子チェック
	ext := strings.ToLower(filepath.Ext(file.Filename))
	if ext != ".pdb" && ext != ".cif" && ext != ".mmcif" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error:   "invalid_file_type",
			Message: "Only .pdb, .cif, or .mmcif files are allowed",
		})
	}

	// チェーンID取得（デフォルト: "A"）
	chainID := c.FormValue("chain_id")
	if chainID == "" {
		chainID = "A"
	}

	// PDB ID取得（オプション）
	pdbID := c.FormValue("pdb_id")
	if pdbID == "" {
		// ファイル名からPDB IDを推測
		baseName := strings.TrimSuffix(file.Filename, ext)
		if len(baseName) >= 4 {
			pdbID = strings.ToUpper(baseName[:4])
		}
	}

	// ファイルデータ読み込み
	fileData, err := file.Open()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error:   "file_read_error",
			Message: fmt.Sprintf("Failed to read file: %v", err),
		})
	}
	defer fileData.Close()

	// ファイルバイト取得
	buffer := make([]byte, file.Size)
	if _, err := fileData.Read(buffer); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error:   "file_read_error",
			Message: fmt.Sprintf("Failed to read file data: %v", err),
		})
	}

	// ファイル保存
	savedPath, err := h.analyzerService.SaveUploadedFile(buffer, file.Filename)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error:   "file_save_error",
			Message: fmt.Sprintf("Failed to save file: %v", err),
		})
	}

	// ジョブID生成
	jobID := uuid.New().String()

	// 非同期で解析実行
	go func() {
		if err := h.analyzerService.AnalyzePDB(jobID, savedPath, chainID, pdbID); err != nil {
			// エラーログ出力
			fmt.Printf("Analysis failed for job %s: %v\n", jobID, err)
		}
	}()

	// レスポンス返却
	return c.Status(fiber.StatusAccepted).JSON(models.AnalyzeResponse{
		JobID:   jobID,
		Status:  "accepted",
		Message: "Analysis started. Use job_id to check status and retrieve results.",
	})
}
