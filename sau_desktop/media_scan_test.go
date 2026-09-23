package main

import (
	"os"
	"path/filepath"
	"testing"
)

// mkfile 创建空文件
func mkfile(t *testing.T, path string) {
	t.Helper()
	if err := os.WriteFile(path, []byte("x"), 0o644); err != nil {
		t.Fatalf("创建文件失败 %s: %v", path, err)
	}
}

func mkdir(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("创建目录失败 %s: %v", path, err)
	}
}

// TestScanFolderStructure_Normal 标准两层结构：根/短剧A/第1-10集/、根/短剧A/第11-20集/、根/短剧B/
// 层级：[rootName, 短剧A/短剧B, 第1-10集/第11-20集, 001.mp4/...]
func TestScanFolderStructure_Normal(t *testing.T) {
	root := t.TempDir()
	rootName := filepath.Base(root)

	// 根/短剧A/第1-10集/001.mp4、002.mp4
	mkdir(t, filepath.Join(root, "短剧A", "第1-10集"))
	mkfile(t, filepath.Join(root, "短剧A", "第1-10集", "001.mp4"))
	mkfile(t, filepath.Join(root, "短剧A", "第1-10集", "002.mp4"))
	// 根/短剧A/第11-20集/011.mp4
	mkdir(t, filepath.Join(root, "短剧A", "第11-20集"))
	mkfile(t, filepath.Join(root, "短剧A", "第11-20集", "011.mp4"))
	// 根/短剧B/b01.mp4（父文件夹直接放视频，无子文件夹）
	mkdir(t, filepath.Join(root, "短剧B"))
	mkfile(t, filepath.Join(root, "短剧B", "b01.mp4"))

	res, err := ScanFolderStructure(root)
	if err != nil {
		t.Fatalf("扫描失败: %v", err)
	}

	if !res.Valid {
		t.Fatalf("结构应校验通过，实际 message=%s warnings=%v", res.Message, res.Warnings)
	}
	if res.VideoCount != 4 {
		t.Errorf("视频数应为 4，实际 %d", res.VideoCount)
	}
	if res.ParentCount != 1 {
		t.Errorf("父文件夹数应为 1（rootName），实际 %d", res.ParentCount)
	}
	if res.ChildCount != 2 {
		t.Errorf("子文件夹数应为 2（短剧A/短剧B），实际 %d", res.ChildCount)
	}

	// 校验排序：rootName → 短剧A 的 001 应排在 短剧B 之前
	first := res.Items[0]
	if first.ParentFolder != rootName || first.ChildFolder != "短剧A" || first.FileName != "001.mp4" {
		t.Errorf("排序不正确，首项应为 %s/短剧A/001.mp4，实际 %s/%s/%s", rootName, first.ParentFolder, first.ChildFolder, first.FileName)
	}
	if first.Episode != 1 {
		t.Errorf("集数解析应为 1，实际 %d", first.Episode)
	}
	if got := res.Items[3]; got.ChildFolder != "短剧B" {
		t.Errorf("末项应为 rootName/短剧B，实际 %s/%s", got.ParentFolder, got.ChildFolder)
	}

	// 根层文件夹名一定是 Folders[0]
	for _, it := range res.Items {
		if len(it.Folders) == 0 || it.Folders[0] != rootName {
			t.Errorf("%s/%s 的 Folders[0] 应为 rootName(%q)，实际 %v", it.ParentFolder, it.FileName, rootName, it.Folders)
		}
	}

	// 短剧B 的视频无子文件夹层级
	for _, it := range res.Items {
		if it.ChildFolder == "短剧B" && it.Folders[len(it.Folders)-1] != "短剧B" {
			t.Errorf("短剧B 的视频层级末位应为短剧B，实际 %v", it.Folders)
		}
	}
}

// TestScanFolderStructure_SingleLevelFolder 单层文件夹结构（每个父文件夹内直接放视频，无子文件夹混放）应通过校验
func TestScanFolderStructure_SingleLevelFolder(t *testing.T) {
	root := t.TempDir()
	rootName := filepath.Base(root)

	// 父文件夹内直接放视频，无子文件夹：根层只有子文件夹，无混合
	mkdir(t, filepath.Join(root, "短剧A"))
	mkfile(t, filepath.Join(root, "短剧A", "001.mp4"))
	mkfile(t, filepath.Join(root, "短剧A", "002.mp4"))
	mkdir(t, filepath.Join(root, "短剧B"))
	mkfile(t, filepath.Join(root, "短剧B", "b01.mp4"))

	res, err := ScanFolderStructure(root)
	if err != nil {
		t.Fatalf("扫描失败: %v", err)
	}
	if !res.Valid {
		t.Errorf("单层文件夹结构应校验通过，实际 message=%s warnings=%v", res.Message, res.Warnings)
	}
	if res.VideoCount != 3 {
		t.Errorf("应统计全部 3 个视频，实际 %d", res.VideoCount)
	}
	if res.ParentCount != 1 {
		t.Errorf("父文件夹数应为 1（rootName），实际 %d", res.ParentCount)
	}
	if res.ChildCount != 2 {
		t.Errorf("子文件夹数应为 2（短剧A/短剧B），实际 %d", res.ChildCount)
	}
	// 根层文件夹名一定是 Folders[0]
	for _, it := range res.Items {
		if len(it.Folders) == 0 || it.Folders[0] != rootName {
			t.Errorf("%s/%s 的 Folders[0] 应为 rootName(%q)，实际 %v", it.ParentFolder, it.FileName, rootName, it.Folders)
		}
	}
}

// TestScanFolderStructure_TooDeep 多层级嵌套 → 折叠归入父文件夹（rootName），不再报错
func TestScanFolderStructure_TooDeep(t *testing.T) {
	root := t.TempDir()
	rootName := filepath.Base(root)

	mkdir(t, filepath.Join(root, "项目", "批次1", "第一组"))
	mkfile(t, filepath.Join(root, "项目", "批次1", "第一组", "001.mp4"))
	mkdir(t, filepath.Join(root, "项目", "批次1", "深层"))
	mkfile(t, filepath.Join(root, "项目", "批次1", "深层", "002.mp4"))

	res, err := ScanFolderStructure(root)
	if err != nil {
		t.Fatalf("扫描失败: %v", err)
	}
	if !res.Valid {
		t.Errorf("多层级应被接受（统一折叠进父文件夹），实际 message=%s warnings=%v", res.Message, res.Warnings)
	}
	if res.VideoCount != 2 {
		t.Errorf("应统计全部 2 个视频（含深层），实际 %d", res.VideoCount)
	}
	// 无论多深，父文件夹均为 rootName
	for _, it := range res.Items {
		if it.ParentFolder != rootName {
			t.Errorf("父文件夹应为 rootName(%q)，实际 %q", rootName, it.ParentFolder)
		}
	}
	if res.ParentCount != 1 {
		t.Errorf("父文件夹数应为 1（rootName），实际 %d", res.ParentCount)
	}
	// rootName 下只有一个子文件夹「项目」
	if res.ChildCount != 1 {
		t.Errorf("子文件夹数应为 1（项目），实际 %d", res.ChildCount)
	}
	// 根层文件夹名一定是 Folders[0]
	for _, it := range res.Items {
		if len(it.Folders) == 0 || it.Folders[0] != rootName {
			t.Errorf("%s/%s 的 Folders[0] 应为 rootName(%q)，实际 %v", it.ParentFolder, it.FileName, rootName, it.Folders)
		}
	}
}

// TestParseEpisodeFromName 集数解析
func TestParseEpisodeFromName(t *testing.T) {
	cases := []struct {
		name string
		want int
	}{
		{"001.mp4", 1},
		{"第5集.mp4", 5},
		{"短剧_第12集_完整版.mp4", 12},
		{"EP07.mp4", 7},
		{"b01.mp4", 1},
		{"没有数字.mp4", 0},
		{"短剧_20260920.mp4", 20260920}, // 兜底取任意数字
	}
	for _, c := range cases {
		if got := parseEpisodeFromName(c.name); got != c.want {
			t.Errorf("parseEpisodeFromName(%q) = %d, want %d", c.name, got, c.want)
		}
	}
}

// TestFormatFileSize 大小格式化
func TestFormatFileSize(t *testing.T) {
	cases := []struct {
		in   int64
		want string
	}{
		{512, "512 B"},
		{2048, "2.0 KB"},
		{132120576, "126.0 MB"},
	}
	for _, c := range cases {
		if got := formatFileSize(c.in); got != c.want {
			t.Errorf("formatFileSize(%d) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestScanFolderStructure_MixedLevel 同一目录下既放视频又放子文件夹 → 结构不合规
func TestScanFolderStructure_MixedLevel(t *testing.T) {
	root := t.TempDir()
	mkdir(t, filepath.Join(root, "短剧A", "第1集"))
	mkfile(t, filepath.Join(root, "短剧A", "第1集", "001.mp4"))
	mkfile(t, filepath.Join(root, "短剧A", "散落.mp4")) // ← 与子文件夹混放

	res, err := ScanFolderStructure(root)
	if err != nil {
		t.Fatalf("扫描失败: %v", err)
	}
	if res.Valid {
		t.Error("存在混合层级时，Valid 应为 false")
	}
	if len(res.Warnings) == 0 {
		t.Error("应给出警告说明")
	}
}
