package upgrade

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"unicode/utf8"

	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/transform"
)

// ExtractZip 解压 zip 文件到指定目录
func ExtractZip(zipFile, destDir string) error {
	r, err := zip.OpenReader(zipFile)
	if err != nil {
		return fmt.Errorf("打开升级包失败: %w", err)
	}
	defer r.Close()

	for _, f := range r.File {
		var decodeName string
		// 边界防护：仅当明确不是合法 UTF-8 时（如旧 Windows 工具使用 GBK 打包），才尝试 GBK/GB18030 转码；
		// 绝不将 macOS/Linux 下原本合法的 UTF-8 文件名错误转码为乱码 (如 灏忔槧鍒嗗彂鍔╂墜.app)
		if (f.Flags&0x800 == 0) && !utf8.ValidString(f.Name) {
			reader := bytes.NewReader([]byte(f.Name))
			decoder := transform.NewReader(reader, simplifiedchinese.GB18030.NewDecoder())
			if content, err := io.ReadAll(decoder); err == nil && len(content) > 0 {
				decodeName = string(content)
			} else {
				decodeName = f.Name
			}
		} else {
			decodeName = f.Name
		}

		targetPath := filepath.Join(destDir, decodeName)
		rel, err := filepath.Rel(destDir, targetPath)
		if err != nil || strings.HasPrefix(rel, "..") {
			continue // 忽略非法相对路径，防 Zip Slip
		}

		if f.FileInfo().IsDir() {
			_ = os.MkdirAll(targetPath, 0755)
			continue
		}

		if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
			return err
		}

		inFile, err := f.Open()
		if err != nil {
			return err
		}

		_ = os.Remove(targetPath) // 解除旧 inode 绑定，防止 macOS 覆盖正在运行的二进制抛错
		outFile, err := os.OpenFile(targetPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			inFile.Close()
			return err
		}

		_, err = io.Copy(outFile, inFile)
		inFile.Close()
		outFile.Close()
		if err != nil {
			return err
		}
	}

	return nil
}
