package upgrade

import (
	"archive/zip"
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

// Downloader 升级包下载器
type Downloader struct {
	httpClient *http.Client
	host       string
}

// NewDownloader 创建下载器
func NewDownloader(host ...string) *Downloader {
	h := ServerHost
	if len(host) > 0 && strings.TrimSpace(host[0]) != "" {
		h = strings.TrimRight(host[0], "/")
	}
	return &Downloader{
		httpClient: &http.Client{
			Timeout: 10 * time.Minute, // 支持大包下载
		},
		host: h,
	}
}

// GetCandidateURLs 构建平台升级包候选地址列表（按优先级依次尝试，含产品隔离目录与根目录兼容）
func (d *Downloader) GetCandidateURLs(latestVersion string) []string {
	vClean := CleanVersion(latestVersion)
	vNoDots := strings.ReplaceAll(vClean, ".", "")

	var names []string
	if runtime.GOOS == "windows" {
		names = []string{
			// 1. 分发助手独立子目录 (优先隔离，防止多产品共享 pkg/ 时冲突)
			fmt.Sprintf("zidongfabu/upgrade_win_%s.zip", vClean),
			fmt.Sprintf("zidongfabu/upgrade_win_%s.zip", vNoDots),
			"zidongfabu/upgrade_win.zip",
			// 2. 根目录带版本号包 (小映传统规范)
			fmt.Sprintf("upgrade_win_%s.zip", vClean),
			fmt.Sprintf("upgrade_win_%s.zip", vNoDots),
			// 3. 根目录兜底
			"upgrade_win.zip",
		}
	} else {
		names = []string{
			// 1. 分发助手独立子目录
			fmt.Sprintf("zidongfabu/upgrade_mac_%s.zip", vClean),
			fmt.Sprintf("zidongfabu/upgrade_mac_%s.zip", vNoDots),
			"zidongfabu/upgrade_mac.zip",
			// 2. 根目录带版本号包
			fmt.Sprintf("upgrade_mac_%s.zip", vClean),
			fmt.Sprintf("upgrade_mac_%s.zip", vNoDots),
			// 3. 根目录兜底
			"upgrade_mac.zip",
		}
	}

	urls := make([]string, 0, len(names))
	for _, name := range names {
		urls = append(urls, fmt.Sprintf("%s/pkg/%s", d.host, name))
	}
	return urls
}

// DownloadPackage 执行升级包原子下载
// targetDir: 保存目录（若为空则保存在临时目录）
// expectedMD5: 期望的文件 MD5 校验和（若提供则严格比对）
func (d *Downloader) DownloadPackage(
	ctx context.Context,
	latestVersion string,
	targetDir string,
	expectedMD5 string,
	onProgress func(DownloadProgress),
) (string, error) {
	if targetDir == "" {
		// 优先存放到系统临时目录下，避免程序安装在系统保护目录 (如 Program Files) 时无权限写入
		targetDir = filepath.Join(os.TempDir(), "sau_upgrade")
	}

	_ = os.MkdirAll(targetDir, 0755)

	finalZipPath := filepath.Join(targetDir, "upgrade.zip")
	tempZipPath := filepath.Join(targetDir, "upgrade.zip.tmp")

	// 清理此前残留的临时文件
	_ = os.Remove(tempZipPath)

	candidateURLs := d.GetCandidateURLs(latestVersion)
	var targetResp *http.Response
	var activeURL string
	var lastErr error

	// 依次尝试候选 URL
	for _, url := range candidateURLs {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			lastErr = err
			continue
		}

		resp, err := d.httpClient.Do(req)
		if err != nil {
			lastErr = err
			continue
		}

		if resp.StatusCode == http.StatusOK {
			targetResp = resp
			activeURL = url
			break
		}

		resp.Body.Close()
		lastErr = fmt.Errorf("HTTP %d on %s", resp.StatusCode, url)
	}

	if targetResp == nil {
		return "", fmt.Errorf("所有升级包下载地址均不可用: %v (已尝试: %s)", lastErr, strings.Join(candidateURLs, ", "))
	}
	defer targetResp.Body.Close()

	totalBytes := targetResp.ContentLength
	totalMB := roundMB(totalBytes)

	// 创建临时文件写入
	tmpFile, err := os.OpenFile(tempZipPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return "", fmt.Errorf("创建临时升级文件失败: %w", err)
	}

	var downloadedBytes int64
	buf := make([]byte, 64*1024) // 64KB 缓冲
	lastReportTime := time.Now()

	// 初始进度通知
	if onProgress != nil {
		onProgress(DownloadProgress{
			Percentage:   0,
			Downloaded:   0,
			Total:        totalBytes,
			DownloadedMB: 0,
			TotalMB:      totalMB,
			Status:       "downloading",
			Message:      fmt.Sprintf("正在从服务器下载升级包 (%s)...", filepath.Base(activeURL)),
		})
	}

	var readErr error
	for {
		// 检查上下文取消
		select {
		case <-ctx.Done():
			tmpFile.Close()
			_ = os.Remove(tempZipPath)
			return "", ctx.Err()
		default:
		}

		nr, rErr := targetResp.Body.Read(buf)
		if nr > 0 {
			nw, wErr := tmpFile.Write(buf[:nr])
			if wErr != nil {
				readErr = wErr
				break
			}
			downloadedBytes += int64(nw)

			// 限制更新频率避免 UI 阻塞 (每 100ms 或达到 100% 报告一次)
			if onProgress != nil && (time.Since(lastReportTime) > 100*time.Millisecond || (totalBytes > 0 && downloadedBytes == totalBytes)) {
				lastReportTime = time.Now()
				pct := 0
				if totalBytes > 0 {
					pct = int(float64(downloadedBytes) / float64(totalBytes) * 100)
				}
				onProgress(DownloadProgress{
					Percentage:   pct,
					Downloaded:   downloadedBytes,
					Total:        totalBytes,
					DownloadedMB: roundMB(downloadedBytes),
					TotalMB:      totalMB,
					Status:       "downloading",
					Message:      "正在下载升级包...",
				})
			}
		}

		if rErr != nil {
			if rErr != io.EOF {
				readErr = rErr
			}
			break
		}
	}

	tmpFile.Close()

	if readErr != nil {
		_ = os.Remove(tempZipPath)
		return "", fmt.Errorf("下载中断: %w", readErr)
	}

	// 长度校验
	if totalBytes > 0 && downloadedBytes != totalBytes {
		_ = os.Remove(tempZipPath)
		return "", fmt.Errorf("下载文件大小不完整: 预期 %d 字节, 实际 %d 字节", totalBytes, downloadedBytes)
	}

	// 原子替换: rename tmp -> upgrade.zip
	_ = os.Remove(finalZipPath) // 确保目标不存在
	if err := os.Rename(tempZipPath, finalZipPath); err != nil {
		_ = os.Remove(tempZipPath)
		return "", fmt.Errorf("重命名升级文件失败: %w", err)
	}

	// 完整性校验 1: 压缩包有效性与可读性测试 (防止网络抖动导致的半截损坏包)
	testReader, zipErr := zip.OpenReader(finalZipPath)
	if zipErr != nil {
		_ = os.Remove(finalZipPath)
		return "", fmt.Errorf("下载完成的升级包损坏，无法解压读取: %w", zipErr)
	}
	testReader.Close()

	// 完整性校验 2: 若服务端提供了 MD5，严格比对哈希值
	if cleanMD5 := strings.TrimSpace(expectedMD5); cleanMD5 != "" {
		actualMD5, hashErr := calculateFileMD5(finalZipPath)
		if hashErr != nil {
			_ = os.Remove(finalZipPath)
			return "", fmt.Errorf("计算升级包 MD5 失败: %w", hashErr)
		}
		if !strings.EqualFold(actualMD5, cleanMD5) {
			_ = os.Remove(finalZipPath)
			return "", fmt.Errorf("升级包完整性校验失败 (MD5 不匹配: 预期 %s, 实际 %s)", cleanMD5, actualMD5)
		}
	}

	if onProgress != nil {
		onProgress(DownloadProgress{
			Percentage:   100,
			Downloaded:   downloadedBytes,
			Total:        totalBytes,
			DownloadedMB: roundMB(downloadedBytes),
			TotalMB:      totalMB,
			Status:       "completed",
			Message:      "下载完成，准备安装更新",
		})
	}

	return finalZipPath, nil
}

func calculateFileMD5(filePath string) (string, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	h := md5.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func roundMB(bytes int64) float64 {
	if bytes <= 0 {
		return 0
	}
	mb := float64(bytes) / 1024.0 / 1024.0
	return math.Round(mb*100) / 100
}
