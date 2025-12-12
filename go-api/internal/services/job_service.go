package services

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
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
	// デバッグ: 受け取ったパラメータをログ出力
	fmt.Printf("[DEBUG] CreateJob - Received params:\n")
	fmt.Printf("  UniProtIDs: %s\n", params.UniProtIDs)
	if params.Method != nil {
		fmt.Printf("  Method: %s (pointer)\n", *params.Method)
	} else {
		fmt.Printf("  Method: nil\n")
	}
	if params.SeqRatio != nil {
		fmt.Printf("  SeqRatio: %f (pointer)\n", *params.SeqRatio)
	} else {
		fmt.Printf("  SeqRatio: nil\n")
	}
	if params.NegativePDBID != nil {
		fmt.Printf("  NegativePDBID: %s (pointer)\n", *params.NegativePDBID)
	} else {
		fmt.Printf("  NegativePDBID: nil\n")
	}
	if params.CisThreshold != nil {
		fmt.Printf("  CisThreshold: %f (pointer)\n", *params.CisThreshold)
	} else {
		fmt.Printf("  CisThreshold: nil\n")
	}
	if params.Export != nil {
		fmt.Printf("  Export: %t (pointer)\n", *params.Export)
	} else {
		fmt.Printf("  Export: nil\n")
	}
	if params.Heatmap != nil {
		fmt.Printf("  Heatmap: %t (pointer)\n", *params.Heatmap)
	} else {
		fmt.Printf("  Heatmap: nil\n")
	}
	if params.ProcCis != nil {
		fmt.Printf("  ProcCis: %t (pointer)\n", *params.ProcCis)
	} else {
		fmt.Printf("  ProcCis: nil\n")
	}
	if params.Overwrite != nil {
		fmt.Printf("  Overwrite: %t (pointer)\n", *params.Overwrite)
	} else {
		fmt.Printf("  Overwrite: nil\n")
	}

	// デフォルト値設定
	if params.Method == nil || *params.Method == "" {
		defaultMethod := "X-ray"
		params.Method = &defaultMethod
		fmt.Printf("[DEBUG] CreateJob - Set default Method: %s\n", defaultMethod)
	}
	if params.SeqRatio == nil || *params.SeqRatio <= 0 || *params.SeqRatio > 1 {
		defaultSeqRatio := 0.2
		params.SeqRatio = &defaultSeqRatio
		fmt.Printf("[DEBUG] CreateJob - Set default SeqRatio: %f\n", defaultSeqRatio)
	}
	if params.CisThreshold == nil || *params.CisThreshold <= 0 {
		defaultCisThreshold := 3.3
		params.CisThreshold = &defaultCisThreshold
		fmt.Printf("[DEBUG] CreateJob - Set default CisThreshold: %f\n", defaultCisThreshold)
	}
	if params.NegativePDBID == nil {
		emptyStr := ""
		params.NegativePDBID = &emptyStr
		fmt.Printf("[DEBUG] CreateJob - Set default NegativePDBID: (empty)\n")
	}
	if params.Export == nil {
		defaultExport := true
		params.Export = &defaultExport
		fmt.Printf("[DEBUG] CreateJob - Set default Export: %t\n", defaultExport)
	}
	if params.Heatmap == nil {
		defaultHeatmap := true
		params.Heatmap = &defaultHeatmap
		fmt.Printf("[DEBUG] CreateJob - Set default Heatmap: %t\n", defaultHeatmap)
	}
	if params.ProcCis == nil {
		defaultProcCis := true
		params.ProcCis = &defaultProcCis
		fmt.Printf("[DEBUG] CreateJob - Set default ProcCis: %t\n", defaultProcCis)
	}
	if params.Overwrite == nil {
		defaultOverwrite := true
		params.Overwrite = &defaultOverwrite
		fmt.Printf("[DEBUG] CreateJob - Set default Overwrite: %t\n", defaultOverwrite)
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
	// デバッグ: ジョブIDをログ出力
	fmt.Printf("[DEBUG] GetResult - JobID: %s\n", jobID)

	// ステータス確認
	status, err := s.GetJobStatus(jobID)
	if err != nil {
		fmt.Printf("[DEBUG] GetResult - Failed to get job status: %v\n", err)
		return nil, err
	}

	fmt.Printf("[DEBUG] GetResult - Job status: %s\n", status.Status)

	if status.Status != "completed" {
		return nil, fmt.Errorf("job not completed: %s", status.Status)
	}

	// Notebook DSAはsummary.csvを出力するため、まずsummary.csvを確認
	summaryPath := filepath.Join(s.storageDir, jobID, "summary.csv")
	resultPath := filepath.Join(s.storageDir, jobID, "result.json")

	// result.jsonが存在する場合はそれを読み込む
	if _, err := os.Stat(resultPath); err == nil {
		fmt.Printf("[DEBUG] GetResult - Found result.json at: %s\n", resultPath)
		data, err := os.ReadFile(resultPath)
		if err != nil {
			fmt.Printf("[DEBUG] GetResult - Failed to read result.json: %v\n", err)
			return nil, fmt.Errorf("failed to read result: %w", err)
		}

		var result models.NotebookDSAResult
		if err := json.Unmarshal(data, &result); err != nil {
			fmt.Printf("[DEBUG] GetResult - Failed to parse result.json: %v\n", err)
			return nil, fmt.Errorf("failed to parse result: %w", err)
		}

		fmt.Printf("[DEBUG] GetResult - Successfully loaded result.json\n")
		return &result, nil
	}

	// result.jsonが存在しない場合は、summary.csvから結果を構築
	if _, err := os.Stat(summaryPath); err == nil {
		fmt.Printf("[DEBUG] GetResult - Found summary.csv at: %s (converting to NotebookDSAResult)\n", summaryPath)
		return s.convertSummaryCSVToResult(jobID, summaryPath)
	}

	// どちらも存在しない場合
	fmt.Printf("[DEBUG] GetResult - Neither result.json nor summary.csv found\n")
	return nil, fmt.Errorf("result file not found. Checked: %s and %s", resultPath, summaryPath)
}

// convertSummaryCSVToResult はsummary.csvからNotebookDSAResultを構築
func (s *JobService) convertSummaryCSVToResult(jobID string, summaryPath string) (*models.NotebookDSAResult, error) {
	fmt.Printf("[DEBUG] convertSummaryCSVToResult - Reading summary.csv from: %s\n", summaryPath)

	// summary.csvを読み込む
	file, err := os.Open(summaryPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open summary.csv: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("failed to read summary.csv: %w", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("summary.csv has insufficient rows: %d", len(records))
	}

	// ヘッダーとデータ行を取得
	headers := records[0]
	data := records[1]

	// ヘッダーからインデックスを取得
	headerMap := make(map[string]int)
	for i, h := range headers {
		headerMap[strings.TrimSpace(h)] = i
	}

	// データを取得
	getString := func(key string) string {
		if idx, ok := headerMap[key]; ok && idx < len(data) {
			return strings.TrimSpace(data[idx])
		}
		return ""
	}

	getInt := func(key string) int {
		val := getString(key)
		if val == "" {
			return 0
		}
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
		return 0
	}

	getFloat := func(key string) float64 {
		val := getString(key)
		if val == "" {
			return 0.0
		}
		if f, err := strconv.ParseFloat(val, 64); err == nil {
			return f
		}
		return 0.0
	}

	uniprotID := getString("uniprotid")
	seqRatio := getFloat("seq_ratio")
	entries := getInt("Entries")
	chains := getInt("Chains")
	length := getInt("Length")
	lengthPercent := getFloat("Length(%)")
	resolution := getFloat("Resolution")
	umf := getFloat("UMF")
	meanCisDist := getFloat("mean_cisDist")
	stdCisDist := getFloat("std_cisDist")
	meanCisScore := getFloat("mean_cisScore")
	cisNum := getInt("cis")
	mix := getInt("mix")

	fmt.Printf("[DEBUG] convertSummaryCSVToResult - Parsed data: uniprotID=%s, entries=%d, chains=%d, length=%d\n", 
		uniprotID, entries, chains, length)

	// 距離データとcisデータを読み込んでPairScoreを構築
	jobDir := filepath.Dir(summaryPath)
	distancePath := filepath.Join(jobDir, fmt.Sprintf("distance_%s.csv", uniprotID))
	
	// cisファイルを検索（パターン: {uniprotID}_{seqRatio}_cis_nor+sub.csv）
	// seqRatioは0.2の場合、ファイル名は "C6H0Y9_0.2_cis_nor+sub.csv" のようになる
	cisPath := ""
	cisPattern := fmt.Sprintf("%s_%.1f_cis_nor+sub.csv", uniprotID, seqRatio)
	cisPath = filepath.Join(jobDir, cisPattern)
	
	// ファイルが存在しない場合は、ワイルドカードで検索
	if _, err := os.Stat(cisPath); err != nil {
		// ディレクトリ内のファイルを検索
		if entries, err := os.ReadDir(jobDir); err == nil {
			for _, entry := range entries {
				if !entry.IsDir() && strings.Contains(entry.Name(), uniprotID) && 
				   strings.Contains(entry.Name(), "_cis_") && strings.HasSuffix(entry.Name(), ".csv") {
					cisPath = filepath.Join(jobDir, entry.Name())
					fmt.Printf("[DEBUG] convertSummaryCSVToResult - Found cis file: %s\n", cisPath)
					break
				}
			}
		}
	}
	
	trimsequencePath := filepath.Join(jobDir, fmt.Sprintf("trimsequence_%s.csv", uniprotID))

	// PairScoreを構築（cisデータから）
	var pairScores []models.PairScore
	var cisPairs []string

	if _, err := os.Stat(cisPath); err == nil {
		fmt.Printf("[DEBUG] convertSummaryCSVToResult - Reading cis data from: %s\n", cisPath)
		cisFile, err := os.Open(cisPath)
		if err == nil {
			defer cisFile.Close()
			cisReader := csv.NewReader(cisFile)
			cisRecords, err := cisReader.ReadAll()
			if err == nil && len(cisRecords) > 1 {
				// ヘッダーをスキップしてデータを読み込む
				for i := 1; i < len(cisRecords); i++ {
					row := cisRecords[i]
					if len(row) < 3 {
						continue
					}

					// 最初の列から残基ペアを取得（"1, 2"形式）
					pairStr := strings.Trim(row[0], `"`)
					parts := strings.Split(pairStr, ", ")
					if len(parts) != 2 {
						continue
					}

					iIdx, err1 := strconv.Atoi(parts[0])
					jIdx, err2 := strconv.Atoi(parts[1])
					if err1 != nil || err2 != nil {
						continue
					}

					// 残基ペア名を取得
					residuePair := ""
					if len(row) > 1 {
						residuePair = strings.Trim(row[1], `"`)
					}

					// distance mean, distance std, scoreを取得
					var distanceMean, distanceStd, score float64
					if len(row) > 15 {
						if f, err := strconv.ParseFloat(row[15], 64); err == nil {
							distanceMean = f
						}
					}
					if len(row) > 16 {
						if f, err := strconv.ParseFloat(row[16], 64); err == nil {
							distanceStd = f
						}
					}
					if len(row) > 17 {
						if f, err := strconv.ParseFloat(row[17], 64); err == nil {
							score = f
						}
					}

					// cis_cntを確認（全構造でcisの場合はcisPairsに追加）
					cisCnt := 0
					if len(row) > 18 {
						if i, err := strconv.Atoi(row[18]); err == nil {
							cisCnt = i
						}
					}
					transCnt := 0
					if len(row) > 19 {
						if i, err := strconv.Atoi(row[19]); err == nil {
							transCnt = i
						}
					}

					// 全構造でcisの場合（trans_cnt == 0）
					if transCnt == 0 && cisCnt > 0 {
						cisPairs = append(cisPairs, pairStr)
					}

					pairScores = append(pairScores, models.PairScore{
						I:            iIdx,
						J:            jIdx,
						ResiduePair:  residuePair,
						DistanceMean: distanceMean,
						DistanceStd:  distanceStd,
						Score:        score,
					})
				}
			}
		}
	}

	// 距離データからもPairScoreを構築（cisデータにないペアも含める）
	if _, err := os.Stat(distancePath); err == nil {
		fmt.Printf("[DEBUG] convertSummaryCSVToResult - Reading distance data from: %s\n", distancePath)
		// 距離データはheaderなしなので、手動でパース
		// フォーマット: residue_num1,residue_num2,distance1,distance2,...
		distanceFile, err := os.Open(distancePath)
		if err == nil {
			defer distanceFile.Close()
			distanceReader := csv.NewReader(distanceFile)
			distanceRecords, err := distanceReader.ReadAll()
			if err == nil {
				// 既存のpairScoresのマップを作成（重複チェック用）
				pairMap := make(map[string]bool)
				for _, ps := range pairScores {
					key := fmt.Sprintf("%d,%d", ps.I, ps.J)
					pairMap[key] = true
				}

				// 距離データから平均と標準偏差を計算
				for _, row := range distanceRecords {
					if len(row) < 2 {
						continue
					}

					iIdx, err1 := strconv.Atoi(row[0])
					jIdx, err2 := strconv.Atoi(row[1])
					if err1 != nil || err2 != nil {
						continue
					}

					key := fmt.Sprintf("%d,%d", iIdx, jIdx)
					if pairMap[key] {
						continue // 既にcisデータから追加済み
					}

					// 距離値を取得（3列目以降）
					var distances []float64
					for i := 2; i < len(row); i++ {
						if f, err := strconv.ParseFloat(row[i], 64); err == nil {
							distances = append(distances, f)
						}
					}

					if len(distances) == 0 {
						continue
					}

					// 平均と標準偏差を計算
					var sum float64
					for _, d := range distances {
						sum += d
					}
					mean := sum / float64(len(distances))

					var variance float64
					for _, d := range distances {
						variance += (d - mean) * (d - mean)
					}
					std := math.Sqrt(variance / float64(len(distances)))

					// scoreを計算（mean / std、stdが0の場合は0.0001）
					score := mean / std
					if std == 0 {
						score = mean / 0.0001
					}

					// 残基ペア名を取得（trimsequenceから推測するか、デフォルト値を使用）
					residuePair := fmt.Sprintf("RES-%d, RES-%d", iIdx, jIdx)

					pairScores = append(pairScores, models.PairScore{
						I:            iIdx,
						J:            jIdx,
						ResiduePair:  residuePair,
						DistanceMean: mean,
						DistanceStd:  std,
						Score:        score,
					})
				}
			}
		}
	}

	// PerResidueScoreを構築（trimsequenceから）
	var perResidueScores []models.PerResidueScore
	if _, err := os.Stat(trimsequencePath); err == nil {
		fmt.Printf("[DEBUG] convertSummaryCSVToResult - Reading trimsequence from: %s\n", trimsequencePath)
		trimFile, err := os.Open(trimsequencePath)
		if err == nil {
			defer trimFile.Close()
			trimReader := csv.NewReader(trimFile)
			trimRecords, err := trimReader.ReadAll()
			if err == nil && len(trimRecords) > 0 {
				// 最初の列がUniProt配列
				for idx, row := range trimRecords {
					if len(row) == 0 {
						continue
					}
					residueName := strings.TrimSpace(row[0])
					// 3文字コードから1文字コードに変換（簡易版）
					residueName1 := residueName
					if len(residueName) == 3 {
						// 簡易変換（完全な変換テーブルは実装しない）
						residueName1 = residueName
					}

					// この残基に関連するペアスコアの平均を計算
					var scores []float64
					for _, ps := range pairScores {
						if ps.I == idx+1 || ps.J == idx+1 {
							if !math.IsNaN(ps.Score) && !math.IsInf(ps.Score, 0) {
								scores = append(scores, ps.Score)
							}
						}
					}

					avgScore := 0.0
					if len(scores) > 0 {
						var sum float64
						for _, s := range scores {
							sum += s
						}
						avgScore = sum / float64(len(scores))
					}

					perResidueScores = append(perResidueScores, models.PerResidueScore{
						Index:         idx,
						ResidueNumber: idx + 1,
						ResidueName:   residueName1,
						Score:         avgScore,
					})
				}
			}
		}
	}

	// PDB IDリストを取得（distanceデータの列名から、またはatom_coordディレクトリから）
	var pdbIDs []string
	atomCoordDir := filepath.Join(jobDir, "atom_coord")
	if entries, err := os.ReadDir(atomCoordDir); err == nil {
		for _, entry := range entries {
			if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".csv") {
				pdbID := strings.TrimSuffix(entry.Name(), ".csv")
				pdbIDs = append(pdbIDs, strings.ToUpper(pdbID))
			}
		}
	}
	if len(pdbIDs) == 0 {
		// フォールバック: デフォルト値
		pdbIDs = []string{}
	}

	// ヒートマップを構築（簡易版：pairScoresから）
	heatmapSize := length
	if heatmapSize == 0 {
		heatmapSize = 100 // デフォルト値
	}
	// NaNを表現するために、nil可能なfloat64ポインタスライスを使用
	heatmapValues := make([][]*float64, heatmapSize)
	for i := range heatmapValues {
		heatmapValues[i] = make([]*float64, heatmapSize)
		// 初期値はnil（JSONではnullとして表現される）
	}

	// pairScoresからヒートマップを構築
	for _, ps := range pairScores {
		i := ps.I - 1 // 0-based
		j := ps.J - 1 // 0-based
		if i >= 0 && i < heatmapSize && j >= 0 && j < heatmapSize {
			if !math.IsNaN(ps.Score) && !math.IsInf(ps.Score, 0) {
				scoreVal := ps.Score
				heatmapValues[i][j] = &scoreVal
			}
			// NaNまたはInfの場合はnilのまま（JSONではnull）
		}
	}

	// 統計を計算
	pairScoreMean := 0.0
	pairScoreStd := 0.0
	if len(pairScores) > 0 {
		var scores []float64
		for _, ps := range pairScores {
			if !math.IsNaN(ps.Score) && !math.IsInf(ps.Score, 0) {
				scores = append(scores, ps.Score)
			}
		}
		if len(scores) > 0 {
			var sum float64
			for _, s := range scores {
				sum += s
			}
			pairScoreMean = sum / float64(len(scores))

			var variance float64
			for _, s := range scores {
				variance += (s - pairScoreMean) * (s - pairScoreMean)
			}
			pairScoreStd = math.Sqrt(variance / float64(len(scores)))
		}
	}

	// フル配列長を計算（length / lengthPercent * 100）
	fullSequenceLength := 0
	if lengthPercent > 0 {
		fullSequenceLength = int(float64(length) / lengthPercent * 100.0)
	}

	// 分解能を設定
	var top5ResolutionMean *float64
	if resolution > 0 {
		top5ResolutionMean = &resolution
	}

	// CisInfoを構築
	cisInfo := models.CisInfo{
		CisDistMean:  meanCisDist,
		CisDistStd:   stdCisDist,
		CisScoreMean: meanCisScore,
		CisNum:       cisNum,
		Mix:          mix,
		CisPairs:     cisPairs,
		Threshold:    3.3, // デフォルト値（実際の値は取得できない場合がある）
	}

	// NotebookDSAResultを構築
	result := &models.NotebookDSAResult{
		UniProtID:            uniprotID,
		NumStructures:        entries,
		NumResidues:          length,
		PDBIDs:               pdbIDs,
		ExcludedPDBs:         []string{},
		SeqRatio:             seqRatio,
		Method:               "X-ray", // デフォルト値
		FullSequenceLength:   fullSequenceLength,
		ResidueCoveragePercent: lengthPercent,
		NumChains:            chains,
		Top5ResolutionMean:   top5ResolutionMean,
		UMF:                  umf,
		PairScoreMean:        pairScoreMean,
		PairScoreStd:         pairScoreStd,
		PairScores:           pairScores,
		PerResidueScores:     perResidueScores,
		Heatmap: &models.Heatmap{
			Size:   heatmapSize,
			Values: heatmapValues,
		},
		CisInfo: cisInfo,
	}

	fmt.Printf("[DEBUG] convertSummaryCSVToResult - Successfully converted summary.csv to NotebookDSAResult\n")
	fmt.Printf("[DEBUG] convertSummaryCSVToResult - Result: uniprotID=%s, numStructures=%d, numResidues=%d, pairScores=%d\n",
		result.UniProtID, result.NumStructures, result.NumResidues, len(result.PairScores))

	return result, nil
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

	// Notebook DSA CLIコマンド構築
	args := []string{
		"-m", "flex_analyzer.cli", "notebook",
		"--uniprot-ids", params.UniProtIDs,
		"--method", *params.Method,
		"--seq-ratio", fmt.Sprintf("%.2f", *params.SeqRatio),
		"--cis-threshold", fmt.Sprintf("%.2f", *params.CisThreshold),
		"--output-dir", filepath.Dir(absResultPath),
		"--pdb-dir", filepath.Join(filepath.Dir(absResultPath), "pdb_files"),
	}
	
	// negative_pdbidが指定されている場合のみ追加
	if params.NegativePDBID != nil && *params.NegativePDBID != "" {
		args = append(args, "--negative-pdbid", *params.NegativePDBID)
	}
	
	// オプションフラグ
	if *params.Export {
		args = append(args, "--export")
	} else {
		args = append(args, "--no-export")
	}
	if *params.Heatmap {
		args = append(args, "--heatmap")
	} else {
		args = append(args, "--no-heatmap")
	}
	if *params.ProcCis {
		args = append(args, "--proc-cis")
	} else {
		args = append(args, "--no-proc-cis")
	}
	if *params.Overwrite {
		args = append(args, "--overwrite")
	} else {
		args = append(args, "--no-overwrite")
	}
	args = append(args, "--verbose")

	// デバッグ: 実行するコマンドをログ出力
	fmt.Printf("[DEBUG] executeDSAAnalysis - Command: %s %v\n", s.pythonBin, args)
	fmt.Printf("[DEBUG] executeDSAAnalysis - Working directory: %s\n", "/Users/kondoubyakko/Desktop/protein-flexibility-platform/python-engine")

	// タイムアウト設定（30分 = 1800秒）
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	
	cmd := exec.CommandContext(ctx, s.pythonBin, args...)
	cmd.Dir = "/Users/kondoubyakko/Desktop/protein-flexibility-platform/python-engine"
	env := os.Environ()
	env = append(env, "PYTHONPATH=./src")
	cmd.Env = env

	// 標準出力/エラー出力をキャプチャ
	fmt.Printf("[DEBUG] executeDSAAnalysis - Starting Python command execution...\n")
	output, err := cmd.CombinedOutput()

	// デバッグ: 出力をログ出力（最初の1000文字のみ）
	outputStr := string(output)
	if len(outputStr) > 1000 {
		fmt.Printf("[DEBUG] executeDSAAnalysis - Output (first 1000 chars): %s\n", outputStr[:1000])
		fmt.Printf("[DEBUG] executeDSAAnalysis - Output length: %d\n", len(outputStr))
	} else {
		fmt.Printf("[DEBUG] executeDSAAnalysis - Full output: %s\n", outputStr)
	}

	if err != nil {
		var errorMsg string
		// タイムアウトエラーのチェック
		if ctx.Err() == context.DeadlineExceeded {
			errorMsg = "Python CLI execution timed out after 30 minutes"
			fmt.Printf("[DEBUG] executeDSAAnalysis - Timeout error: %v\n", err)
			s.updateJobStatus(jobID, "failed", 0, errorMsg)
		} else {
			// その他のエラー
			outputPreview := outputStr
			if len(outputStr) > 2000 {
				outputPreview = outputStr[len(outputStr)-2000:]
			}
			errorMsg = fmt.Sprintf("Python CLI failed: %v\nOutput (last 2000 chars): %s", err, outputPreview)
			fmt.Printf("[DEBUG] executeDSAAnalysis - Execution error: %v\n", err)
			s.updateJobStatus(jobID, "failed", 0, errorMsg)
		}

		// エラーファイル保存
		errorData := models.ErrorResponse{
			Error: errorMsg,
			PartialResult: map[string]interface{}{
				"output": outputStr,
			},
		}
		errorJSON, _ := json.MarshalIndent(errorData, "", "  ")
		_ = os.WriteFile(filepath.Join(jobDir, "error.json"), errorJSON, 0o644)

		return
	}

	fmt.Printf("[DEBUG] executeDSAAnalysis - Python command completed successfully\n")

	// Notebook DSAはsummary.csvを出力するため、result.jsonが存在しない可能性がある
	// summary.csvから結果を読み込んでresult.jsonに変換するか、summary.csvの存在を確認
	summaryPath := filepath.Join(filepath.Dir(absResultPath), "summary.csv")
	if _, err := os.Stat(summaryPath); err == nil {
		fmt.Printf("[DEBUG] executeDSAAnalysis - Found summary.csv at: %s\n", summaryPath)
		// summary.csvが存在する場合は、それをresult.jsonとして保存するか、
		// またはGetResult関数でsummary.csvを読み込むように変更する必要がある
		// ここでは、summary.csvの存在を確認してログ出力するだけ
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
