package main

import (
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

// mediaPreviewHandler 通过 Wails AssetServer 暴露本机视频文件，供前端 <video> 预览。
//
// 背景：Wails 原生拖拽只返回绝对路径（string），前端拿不到 File 对象，
// 无法像浏览器那样用 URL.createObjectURL 播放本地视频，file:// 也被 WebView 限制。
// 因此后端开一条只读通道：
//
//	GET /local-media?path=<urlencoded 绝对路径>
//
// 内部走 http.ServeFile，自带 Range 支持（前端可拖进度条 seek）。
// 安全：仅放行视频扩展名 + 文件必须真实存在，避免变成任意文件读取通道。
func mediaPreviewHandler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || !strings.HasPrefix(r.URL.Path, "/local-media") {
			http.NotFound(w, r)
			return
		}

		raw := r.URL.Query().Get("path")
		if raw == "" {
			http.Error(w, "missing path", http.StatusBadRequest)
			return
		}

		filePath := raw
		if decoded, err := url.QueryUnescape(raw); err == nil {
			filePath = decoded
		}

		// 只允许读取视频文件
		if !IsVideoFile(filePath) {
			http.Error(w, "unsupported media type", http.StatusForbidden)
			return
		}

		info, err := os.Stat(filePath)
		if err != nil || info.IsDir() {
			http.Error(w, "file not found", http.StatusNotFound)
			return
		}

		w.Header().Set("Cache-Control", "no-store")
		http.ServeFile(w, r, filepath.Clean(filePath))
	})
}
