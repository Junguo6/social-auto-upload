package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// ============================================================================
// 素材文件夹结构扫描
//
// 约定结构（最多两层）：
//
//	根目录/
//	  ├── 父文件夹A/
//	  │     ├── 视频1.mp4              → parent=父文件夹A, child=""
//	  │     └── 子文件夹A1/
//	  │           └── 视频2.mp4        → parent=父文件夹A, child=子文件夹A1
//	  └── 父文件夹B/
//	        └── 视频3.mp4
//
// 不符合约定的情况（返回 Valid=false + Warnings）：
//   - 视频直接放在根目录下（没有父文件夹）
//   - 目录嵌套超过两层
//   - 没有找到任何视频
// ============================================================================

// scanVideoExts 可识别的视频扩展名
var scanVideoExts = map[string]bool{
	".mp4": true, ".mov": true, ".mkv": true, ".flv": true,
	".avi": true, ".webm": true, ".wmv": true, ".m4v": true,
	".3gp": true, ".mpeg": true, ".mpg": true, ".ts": true,
}

// ScannedMediaItem 扫描到的单个视频及其文件夹归属
type ScannedMediaItem struct {
	FilePath     string   `json:"filePath"`     // 绝对路径
	FileName     string   `json:"fileName"`     // 文件名
	ParentFolder string   `json:"parentFolder"` // 父文件夹名（第一层，向后兼容）
	ChildFolder  string   `json:"childFolder"`  // 子文件夹名（第二层，向后兼容；可能为空）
	// Folders 是相对扫描根目录的完整目录层级（从最外层到最内层，不含文件名），
	// 供前端做"逐层进入"式浏览；ParentFolder/ChildFolder 仅作兼容保留。
	// 散装视频（直接落在根目录下）该字段为 nil。
	Folders      []string `json:"folders"`
	SizeBytes    int64    `json:"sizeBytes"`    // 字节大小
	FileSizeText string   `json:"fileSizeText"` // 易读大小，如 "126.3 MB"
	Episode      int      `json:"episode"`      // 从文件名解析的集数（0=未识别）
}

// FolderScanResult 文件夹结构扫描结果
type FolderScanResult struct {
	Root        string             `json:"root"`        // 所选根目录
	Valid       bool               `json:"valid"`       // 结构是否符合约定
	Message     string             `json:"message"`     // 校验提示（直接展示给用户）
	Warnings    []string           `json:"warnings"`    // 具体问题清单
	ParentCount int                `json:"parentCount"` // 父文件夹数量
	ChildCount  int                `json:"childCount"`  // 子文件夹数量
	VideoCount  int                `json:"videoCount"`  // 视频数量
	Items       []ScannedMediaItem `json:"items"`       // 视频清单（已按 父/子/集数 排序）
}

// ScanMediaFolder 弹出原生文件夹选择框，解析两层文件夹结构并返回视频清单
// 前端调用：ScanMediaFolder("选择素材文件夹")
func (a *App) ScanMediaFolder(title string) (*FolderScanResult, error) {
	if strings.TrimSpace(title) == "" {
		title = "选择素材文件夹（会自动解析文件夹结构）"
	}
	root, err := runtime.OpenDirectoryDialog(a.ctx, runtime.OpenDialogOptions{Title: title})
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(root) == "" {
		// 用户取消，返回空结果而非错误
		return &FolderScanResult{Valid: false, Message: "未选择文件夹", Items: []ScannedMediaItem{}}, nil
	}
	return ScanFolderStructure(root)
}

// ScanFolderStructure 解析指定根目录的文件夹结构（纯函数，便于单独测试）
func ScanFolderStructure(root string) (*FolderScanResult, error) {
	info, err := os.Stat(root)
	if err != nil {
		return nil, fmt.Errorf("无法访问文件夹: %w", err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("所选路径不是文件夹: %s", root)
	}

	result := &FolderScanResult{
		Root:     root,
		Valid:    true,
		Warnings: []string{},
		Items:    []ScannedMediaItem{},
	}

	// 被拖入的文件夹本身作为层级的第一层（父文件夹）。
	// 例：拖入「短剧发布计划_副本」→ 视频路径的层级变为 [短剧发布计划_副本, 帐号1, 短剧1, 001.mp4]
	rootName := filepath.Base(filepath.Clean(root))

	parentSet := map[string]struct{}{}
	childSet := map[string]struct{}{} // 第二层唯一组合数（仅用于统计展示）

	// 递归扫描：不再限制层级深度。
	// 归属规则：父文件夹 = 第 1 层目录名（即被拖入的文件夹），
	//          子文件夹 = 第 2 层目录名（账号名），深层统一折叠进父文件夹
	err = filepath.WalkDir(root, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return nil // 跳过无权限目录
		}
		if d.IsDir() || !IsVideoFile(d.Name()) {
			return nil
		}

		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			return nil
		}
		parts := strings.Split(filepath.ToSlash(rel), "/")

		// 把「被拖入的文件夹本身」作为第一层
		if rootName != "" && rootName != "." && rootName != string(filepath.Separator) {
			parts = append([]string{rootName}, parts...)
		}

		parent := parts[0]
		child := ""
		if len(parts) >= 3 {
			child = parts[1]
			childSet[parent+"/"+child] = struct{}{}
		}

		// 完整目录层级（去掉最后的文件名），供前端逐层进入式浏览
		folders := parts[:len(parts)-1]

		result.Items = append(result.Items, buildScannedItem(path, d.Name(), parent, child, folders))
		parentSet[parent] = struct{}{}
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("遍历文件夹失败: %w", err)
	}

	// ---- 排序：父文件夹 → 子文件夹 → 集数 → 文件名 ----
	sort.SliceStable(result.Items, func(i, j int) bool {
		x, y := result.Items[i], result.Items[j]
		if x.ParentFolder != y.ParentFolder {
			return x.ParentFolder < y.ParentFolder
		}
		if x.ChildFolder != y.ChildFolder {
			return x.ChildFolder < y.ChildFolder
		}
		if x.Episode != y.Episode {
			return x.Episode < y.Episode
		}
		return x.FileName < y.FileName
	})

	result.ParentCount = len(parentSet)
	result.ChildCount = len(childSet)
	result.VideoCount = len(result.Items)

	// ---- 结构校验：同一目录下不允许「既放子文件夹、又直接放视频」----
	// 这种混合结构无法确定分组层级（哪一层才代表一个分组？），直接判为不合规
	var mixedDirs []string
	_ = filepath.WalkDir(root, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil || !d.IsDir() {
			return nil
		}
		entries, readErr := os.ReadDir(path)
		if readErr != nil {
			return nil
		}

		hasVideo, hasSubDir := false, false
		for _, e := range entries {
			if e.IsDir() {
				hasSubDir = true
			} else if IsVideoFile(e.Name()) {
				hasVideo = true
			}
		}

		if hasVideo && hasSubDir {
			rel, relErr := filepath.Rel(root, path)
			name := "根目录"
			if relErr == nil && rel != "." {
				name = filepath.ToSlash(rel)
			}
			mixedDirs = append(mixedDirs, name)
		}
		return nil
	})

	if len(mixedDirs) > 0 {
		result.Valid = false
		shown := mixedDirs
		if len(shown) > 3 {
			shown = shown[:3]
		}
		msg := fmt.Sprintf(
			"文件夹「%s」下同时存在视频和子文件夹，无法确定分组层级。请保证每一层只包含一种内容：要么全是子文件夹，要么全是视频文件",
			strings.Join(shown, "」、「"),
		)
		if len(mixedDirs) > 3 {
			msg += fmt.Sprintf("（共 %d 处）", len(mixedDirs))
		}
		result.Warnings = append(result.Warnings, msg)
	}

	// ---- 结构校验 ----
	if result.VideoCount == 0 {
		result.Valid = false
		result.Warnings = append(result.Warnings, "该文件夹下没有找到视频文件（支持 mp4/mov/mkv/avi 等常见格式）")
	}

	if result.Valid {
		result.Message = fmt.Sprintf("结构校验通过：%d 个父文件夹 · %d 个子文件夹 · %d 个视频",
			result.ParentCount, result.ChildCount, result.VideoCount)
	} else {
		result.Message = strings.Join(result.Warnings, "；")
	}

	return result, nil
}

// IsVideoFile 判断是否为支持的视频文件
func IsVideoFile(name string) bool {
	return scanVideoExts[strings.ToLower(filepath.Ext(name))]
}

// buildScannedItem 构造单个扫描结果
func buildScannedItem(fullPath, fileName, parent, child string, folders []string) ScannedMediaItem {
	item := ScannedMediaItem{
		FilePath:     fullPath,
		FileName:     fileName,
		ParentFolder: parent,
		ChildFolder:  child,
		Folders:      folders,
		Episode:      parseEpisodeFromName(fileName),
	}
	if fi, err := os.Stat(fullPath); err == nil {
		item.SizeBytes = fi.Size()
		item.FileSizeText = formatFileSize(fi.Size())
	}
	return item
}

var (
	// 第N集 / 第N话 / 第N期 / EPn / En
	episodeKeywordRe = regexp.MustCompile(`(?:第|EP|ep|Ep|E)\s*0*(\d+)`)
	// 文件名开头的数字，如 001.mp4
	episodeLeadingRe = regexp.MustCompile(`^0*(\d+)`)
	// 兜底：任意数字
	episodeAnyRe = regexp.MustCompile(`0*(\d+)`)
)

// parseEpisodeFromName 从文件名解析集数
// 优先级：「第N集/EPn」 > 开头数字 > 任意数字；解析不出返回 0
func parseEpisodeFromName(fileName string) int {
	base := strings.TrimSuffix(fileName, filepath.Ext(fileName))
	for _, re := range []*regexp.Regexp{episodeKeywordRe, episodeLeadingRe, episodeAnyRe} {
		if m := re.FindStringSubmatch(base); len(m) > 1 {
			if n, err := strconv.Atoi(m[1]); err == nil {
				return n
			}
		}
	}
	return 0
}

// formatFileSize 字节数转易读文本
func formatFileSize(size int64) string {
	const (
		kb = 1024
		mb = kb * 1024
		gb = mb * 1024
	)
	switch {
	case size >= gb:
		return fmt.Sprintf("%.2f GB", float64(size)/float64(gb))
	case size >= mb:
		return fmt.Sprintf("%.1f MB", float64(size)/float64(mb))
	case size >= kb:
		return fmt.Sprintf("%.1f KB", float64(size)/float64(kb))
	default:
		return fmt.Sprintf("%d B", size)
	}
}

// ============================================================================
// 原生拖拽入口（Wails v2.10+）
// ============================================================================

// DropScanPayload 拖拽导入的结果，通过 "media:file-drop" 事件推送给前端
type DropScanPayload struct {
	Folders []*FolderScanResult `json:"folders"` // 拖入的文件夹（已解析两层结构）
	Files   []ScannedMediaItem  `json:"files"`   // 拖入的散装视频文件
	Message string              `json:"message"` // 面向用户的提示文案
}

// handleNativeFileDrop 处理原生拖拽进来的路径
// 文件夹 → 解析两层结构；散装视频文件 → 直接收录
// 结果通过 runtime 事件 "media:file-drop" 推送给前端
func (a *App) handleNativeFileDrop(paths []string) {
	payload := &DropScanPayload{
		Folders: []*FolderScanResult{},
		Files:   []ScannedMediaItem{},
	}

	videoTotal := 0
	unreadable := 0

	for _, p := range paths {
		info, err := os.Stat(p)
		if err != nil {
			unreadable++
			continue
		}

		if info.IsDir() {
			res, scanErr := ScanFolderStructure(p)
			if scanErr != nil {
				unreadable++
				continue
			}
			payload.Folders = append(payload.Folders, res)
			videoTotal += res.VideoCount
			continue
		}

		if IsVideoFile(p) {
			payload.Files = append(payload.Files, buildScannedItem(p, filepath.Base(p), "", "", nil))
			videoTotal++
		}
	}

	switch {
	case videoTotal == 0:
		payload.Message = "未识别到视频文件（支持 mp4 / mov / mkv / avi 等常见格式）"
	case len(payload.Folders) > 0:
		payload.Message = fmt.Sprintf("已导入 %d 个视频（来自 %d 个文件夹）", videoTotal, len(payload.Folders))
	default:
		payload.Message = fmt.Sprintf("已导入 %d 个视频", videoTotal)
	}
	if unreadable > 0 {
		payload.Message += fmt.Sprintf("，另有 %d 个路径无法读取", unreadable)
	}

	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, "media:file-drop", payload)
	}
}
