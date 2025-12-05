package services

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/yourusername/flex-api/internal/models"
)

type JobService struct {
	storageDir string
	mu         sync.RWMutex
	pythonBin  string
}

func NewJobService(storageDir, pythonBin string) *JobService {
	if pythonBin == "" {
		pythonBin = "python3"
	}
	return &JobService{
		storageDir: storageDir,
		pythonBin:  pythonBin,
	}
}

// ★ heatmap エンドポイント用：storageDir を公開
func (s *JobService) StorageDir() string {
	return s.storageDir
}

// CreateJob は新しいジョブを作成
func (s *JobService) CreateJob(params models.AnalysisParams) (*models.JobResponse, error) {
	// デフォルト値設定
	if params.MaxStructures <= 0 {
		params.MaxStructures = 5
	}
	if params.SeqRatio <= 0 || params.SeqRatio > 1 {
		params.SeqRatio = 0.9
	}
	if params.CisThreshold <= 0 {
		params.CisThreshold = 3.8
	}
	if params.Method == "" {
		params.Method = "X-ray diffraction"
	}

	// ジョブID生成
	jobID := uuid.New().String()

	// ジョブディレクトリ作成
	jobDir := filepath.Join(s.storageDir, jobID)
	if err := os.MkdirAll(jobDir, 0o755); err != nil {
		return nil, fmt.Errorf("failed to create job directory: %w", err)
	}

	// ステータス初期化
	status := models.JobStatus{
		JobID:     jobID,
		Status:    "pending",
		Progress:  0,
		Message:   "Job created",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := s.saveJobStatus(jobID, status); err != nil {
		return nil, err
	}

	// 非同期で解析実行
	go s.executeDSAAnalysis(jobID, params)

	return &models.JobResponse{
		JobID:     jobID,
		Status:    status.Status,
		CreatedAt: status.CreatedAt,
	}, nil
}

// GetJobStatus はジョブの状態を取得
func (s *JobService) GetJobStatus(jobID string) (*models.JobStatus, error) {
	statusPath := filepath.Join(s.storageDir, jobID, "status.json")

	data, err := os.ReadFile(statusPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("job not found: %s", jobID)
		}
		return nil, fmt.Errorf("failed to read status: %w", err)
	}

	var status models.JobStatus
	if err := json.Unmarshal(data, &status); err != nil {
		return nil, fmt.Errorf("failed to parse status: %w", err)
	}

	return &status, nil
}

// GetResult はジョブの結果を取得
func (s *JobService) GetResult(jobID string) (*models.NotebookDSAResult, error) {
	// ステータス確認
	status, err := s.GetJobStatus(jobID)
	if err != nil {
		return nil, err
	}

	if status.Status != "completed" {
		return nil, fmt.Errorf("job not completed: %s", status.Status)
	}

	// 結果ファイル読み込み
	resultPath := filepath.Join(s.storageDir, jobID, "result.json")
	data, err := os.ReadFile(resultPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read result: %w", err)
	}

	var result models.NotebookDSAResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("failed to parse result: %w", err)
	}

	return &result, nil
}

// executeDSAAnalysis はPython CLIを実行（非同期）
func (s *JobService) executeDSAAnalysis(jobID string, params models.AnalysisParams) {
	// ステータス更新: processing
	s.updateJobStatus(jobID, "processing", 0, "Starting analysis...")

	// 出力パス（結果 JSON と heatmap.png は同じ job ディレクトリに置く前提）
	jobDir := filepath.Join(s.storageDir, jobID)
	if err := os.MkdirAll(jobDir, 0o755); err != nil {
		s.updateJobStatus(jobID, "failed", 0, fmt.Sprintf("failed to create job dir: %v", err))
		return
	}

	resultPath := filepath.Join(jobDir, "result.json")

	// 絶対パス化（Python 側に cwd 依存しないパスを渡す）
	absResultPath, err := filepath.Abs(resultPath)
	if err != nil {
		s.updateJobStatus(jobID, "failed", 0, fmt.Sprintf("failed to resolve result path: %v", err))
		return
	}

	// ================================
	//  🔴 ここが「Python 実行環境あわせ」の肝
	// ================================
	// 1) python バイナリは起動時フラグ -python で /opt/anaconda3/bin/python を渡す
	// 2) PYTHON_ENGINE_DIR 環境変数に python-engine ディレクトリを設定しておく
	//    例: export PYTHON_ENGINE_DIR="/Users/xxx/Desktop/protein-flexibility-platform/python-engine"
	pythonWorkDir := os.Getenv("PYTHON_ENGINE_DIR")
	if pythonWorkDir == "" {
		// 一旦カレントのままでも動くようにフォールバック
		pythonWorkDir, _ = os.Getwd()
	}

	// Python CLIコマンド構築（手で叩いていたのと同じオプションを揃える）
	args := []string{
		"-m", "flex_analyzer.cli",
		"--uniprot", params.UniProtID,
		"--max-structures", strconv.Itoa(params.MaxStructures),
		"--seq-ratio", fmt.Sprintf("%.2f", params.SeqRatio),
		"--cis-threshold", fmt.Sprintf("%.2f", params.CisThreshold),
		"--method", params.Method,
		"--output", absResultPath,
		"--verbose",
	}

	cmd := exec.Command(s.pythonBin, args...)

	/// cwd と PYTHONPATH を Python 単体実行と揃える
	cmd.Dir = "/Users/kondoubyakko/Desktop/protein-flexibility-platform/python-engine"
	env := os.Environ()
	env = append(env, "PYTHONPATH=./src")
	cmd.Env = env


	// 標準出力/エラー出力をキャプチャ
	output, err := cmd.CombinedOutput()

	if err != nil {
		// エラー処理
		errorMsg := fmt.Sprintf("Python CLI failed: %v\nOutput: %s", err, string(output))
		s.updateJobStatus(jobID, "failed", 0, errorMsg)

		// エラーファイル保存
		errorData := models.ErrorResponse{
			Error: errorMsg,
			PartialResult: map[string]interface{}{
				"output": string(output),
			},
		}
		errorJSON, _ := json.MarshalIndent(errorData, "", "  ")
		_ = os.WriteFile(filepath.Join(jobDir, "error.json"), errorJSON, 0o644)

		return
	}

	// 完了
	s.updateJobStatus(jobID, "completed", 100, "Analysis completed")
}

// updateJobStatus はジョブステータスを更新
func (s *JobService) updateJobStatus(jobID, status string, progress int, message string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	jobStatus := models.JobStatus{
		JobID:     jobID,
		Status:    status,
		Progress:  progress,
		Message:   message,
		UpdatedAt: time.Now(),
	}

	// 既存のCreatedAtを保持
	existingStatus, err := s.GetJobStatus(jobID)
	if err == nil {
		jobStatus.CreatedAt = existingStatus.CreatedAt
	} else {
		jobStatus.CreatedAt = time.Now()
	}

	_ = s.saveJobStatus(jobID, jobStatus)
}

// saveJobStatus はジョブステータスをファイルに保存
func (s *JobService) saveJobStatus(jobID string, status models.JobStatus) error {
	statusPath := filepath.Join(s.storageDir, jobID, "status.json")

	data, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal status: %w", err)
	}

	if err := os.WriteFile(statusPath, data, 0o644); err != nil {
		return fmt.Errorf("failed to write status: %w", err)
	}

	return nil
}
