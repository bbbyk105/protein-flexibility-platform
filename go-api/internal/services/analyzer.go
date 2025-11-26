// internal/services/analyzer.go
package services

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"protein-flex-api/internal/models"
)

type AnalyzerService struct {
	StorageDir string
}

// NewAnalyzerService は新しいAnalyzerServiceを作成
func NewAnalyzerService(storageDir string) *AnalyzerService {
	return &AnalyzerService{
		StorageDir: storageDir,
	}
}

// AnalyzePDB はPDBファイルを解析
func (s *AnalyzerService) AnalyzePDB(jobID, pdbPath, chainID, pdbID string) error {
	// 結果ファイルパス（絶対パスに変換）
	absStorageDir, _ := filepath.Abs(s.StorageDir)
	resultPath := filepath.Join(absStorageDir, "results", fmt.Sprintf("%s.json", jobID))

	// ジョブステータスファイル作成
	statusPath := filepath.Join(absStorageDir, "results", fmt.Sprintf("%s.status.json", jobID))
	s.updateJobStatus(statusPath, jobID, "processing", "Analysis in progress", 10)

	// PDBパスも絶対パスに変換
	absPdbPath, _ := filepath.Abs(pdbPath)

	// flex-analyzeコマンド実行
	args := []string{
		"-m", "flex_analyzer.cli",
		"-i", absPdbPath,
		"-c", chainID,
		"-o", resultPath,
		"--job-id", jobID,
	}

	if pdbID != "" {
		args = append(args, "--pdb-id", pdbID)
	}

	cmd := exec.Command("/opt/anaconda3/bin/python", args...)
	
	// 作業ディレクトリを python-engine に設定
	cmd.Dir = "../python-engine"

	// 標準出力・エラー出力を取得
	output, err := cmd.CombinedOutput()
	if err != nil {
		errorMsg := fmt.Sprintf("Python analysis failed: %v\nOutput: %s", err, string(output))
		s.updateJobStatus(statusPath, jobID, "failed", errorMsg, 0)
		return fmt.Errorf(errorMsg)
	}

	// 成功
	s.updateJobStatus(statusPath, jobID, "completed", "Analysis completed successfully", 100)
	return nil
}

// AnalyzeUniProt はUniProt IDを使って自動解析
func (s *AnalyzerService) AnalyzeUniProt(jobID, uniprotID string, maxStructures int) error {
	// 結果ファイルパス（絶対パスに変換）
	absStorageDir, _ := filepath.Abs(s.StorageDir)
	resultPath := filepath.Join(absStorageDir, "results", fmt.Sprintf("%s.json", jobID))

	// ジョブステータスファイル作成
	statusPath := filepath.Join(absStorageDir, "results", fmt.Sprintf("%s.status.json", jobID))
	s.updateJobStatus(statusPath, jobID, "processing", "UniProt analysis in progress", 10)

	// flex-analyzeコマンド実行（UniProtモード）
	args := []string{
		"-m", "flex_analyzer.cli",
		"--uniprot", uniprotID,
		"--max-structures", fmt.Sprintf("%d", maxStructures),
		"-o", resultPath,
	}

	cmd := exec.Command("/opt/anaconda3/bin/python", args...)
	
	// 作業ディレクトリを python-engine に設定
	cmd.Dir = "../python-engine"

	// 進捗更新
	s.updateJobStatus(statusPath, jobID, "processing", "Downloading PDB structures...", 30)

	// 標準出力・エラー出力を取得
	output, err := cmd.CombinedOutput()
	if err != nil {
		errorMsg := fmt.Sprintf("UniProt analysis failed: %v\nOutput: %s", err, string(output))
		s.updateJobStatus(statusPath, jobID, "failed", errorMsg, 0)
		return fmt.Errorf(errorMsg)
	}

	// 成功
	s.updateJobStatus(statusPath, jobID, "completed", "UniProt analysis completed successfully", 100)
	return nil
}

// GetResult は解析結果を取得
func (s *AnalyzerService) GetResult(jobID string) (*models.AnalysisResult, error) {
	resultPath := filepath.Join(s.StorageDir, "results", fmt.Sprintf("%s.json", jobID))

	// ファイルが存在するか確認
	if _, err := os.Stat(resultPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("result not found for job_id: %s", jobID)
	}

	// JSONファイル読み込み
	data, err := os.ReadFile(resultPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read result file: %v", err)
	}

	// JSONパース
	var result models.AnalysisResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("failed to parse result JSON: %v", err)
	}

	return &result, nil
}

// GetUniProtResult はUniProt解析結果を取得
func (s *AnalyzerService) GetUniProtResult(jobID string) (*models.UniProtLevelResult, error) {
	resultPath := filepath.Join(s.StorageDir, "results", fmt.Sprintf("%s.json", jobID))

	// ファイルが存在するか確認
	if _, err := os.Stat(resultPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("result not found for job_id: %s", jobID)
	}

	// JSONファイル読み込み
	data, err := os.ReadFile(resultPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read result file: %v", err)
	}

	// JSONパース
	var result models.UniProtLevelResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("failed to parse UniProt result JSON: %v", err)
	}

	return &result, nil
}

// GetJobStatus はジョブステータスを取得
func (s *AnalyzerService) GetJobStatus(jobID string) (*models.JobStatus, error) {
	statusPath := filepath.Join(s.StorageDir, "results", fmt.Sprintf("%s.status.json", jobID))

	// ファイルが存在するか確認
	if _, err := os.Stat(statusPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("status not found for job_id: %s", jobID)
	}

	// JSONファイル読み込み
	data, err := os.ReadFile(statusPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read status file: %v", err)
	}

	// JSONパース
	var status models.JobStatus
	if err := json.Unmarshal(data, &status); err != nil {
		return nil, fmt.Errorf("failed to parse status JSON: %v", err)
	}

	return &status, nil
}

// updateJobStatus はジョブステータスを更新
func (s *AnalyzerService) updateJobStatus(statusPath, jobID, status, message string, progress int) error {
	now := time.Now().Format(time.RFC3339)

	jobStatus := models.JobStatus{
		JobID:     jobID,
		Status:    status,
		Message:   message,
		Progress:  progress,
		UpdatedAt: now,
	}

	// 既存のステータスファイルがあれば CreatedAt を保持
	if existingData, err := os.ReadFile(statusPath); err == nil {
		var existing models.JobStatus
		if json.Unmarshal(existingData, &existing) == nil {
			jobStatus.CreatedAt = existing.CreatedAt
		}
	}

	// 新規作成の場合
	if jobStatus.CreatedAt == "" {
		jobStatus.CreatedAt = now
	}

	// JSON書き込み
	data, err := json.MarshalIndent(jobStatus, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(statusPath, data, 0644)
}

// SaveUploadedFile はアップロードされたファイルを保存
func (s *AnalyzerService) SaveUploadedFile(fileData []byte, filename string) (string, error) {
	uploadDir := filepath.Join(s.StorageDir, "uploads")

	// ディレクトリ作成（存在しない場合）
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create upload directory: %v", err)
	}

	// ファイルパス生成（タイムスタンプ付き）
	timestamp := time.Now().Unix()
	safeName := filepath.Base(filename)
	filePath := filepath.Join(uploadDir, fmt.Sprintf("%d_%s", timestamp, safeName))

	// ファイル書き込み
	if err := os.WriteFile(filePath, fileData, 0644); err != nil {
		return "", fmt.Errorf("failed to save file: %v", err)
	}

	return filePath, nil
}
