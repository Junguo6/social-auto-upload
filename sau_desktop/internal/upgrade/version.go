package upgrade

import (
	"strconv"
	"strings"
)

// CleanVersion 清理版本号前缀与空格 (如 " v1.2.0 " -> "1.2.0")
func CleanVersion(ver string) string {
	ver = strings.TrimSpace(ver)
	ver = strings.TrimPrefix(ver, "v")
	ver = strings.TrimPrefix(ver, "V")
	return ver
}

// CompareVersion 严格对比两个三段式 (x.y.z) 或多段版本号
// 返回值：
//
//	 1: v1 > v2 (v1 版本更新)
//	-1: v1 < v2 (v1 版本更旧)
//	 0: v1 == v2 (版本相同)
func CompareVersion(v1, v2 string) int {
	s1 := CleanVersion(v1)
	s2 := CleanVersion(v2)

	if s1 == s2 {
		return 0
	}

	parts1 := strings.Split(s1, ".")
	parts2 := strings.Split(s2, ".")

	maxLen := len(parts1)
	if len(parts2) > maxLen {
		maxLen = len(parts2)
	}

	for i := 0; i < maxLen; i++ {
		var n1, n2 int
		if i < len(parts1) {
			if num, err := strconv.Atoi(strings.TrimSpace(parts1[i])); err == nil {
				n1 = num
			}
		}
		if i < len(parts2) {
			if num, err := strconv.Atoi(strings.TrimSpace(parts2[i])); err == nil {
				n2 = num
			}
		}

		if n1 > n2 {
			return 1
		} else if n1 < n2 {
			return -1
		}
	}

	return 0
}
