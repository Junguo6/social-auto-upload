//go:build darwin

package auth

import (
	"os"
	"path/filepath"
)

func getSeedBackupTargets() []seedTarget {
	home := os.Getenv("HOME")
	mainPath := filepath.Join(home, "Library", "Application Support", ExecutableName, "conf", "seed.json")
	plistPath := filepath.Join(home, "Library", "Preferences", "com.socialautoupload.matrix.seed.plist")

	return []seedTarget{
		{Path: mainPath, Kind: seedTargetFile},
		{Path: plistPath, Kind: seedTargetFile},
	}
}

func writeSeedTarget(t seedTarget, data string) error {
	dir := filepath.Dir(t.Path)
	if dir != "" {
		_ = os.MkdirAll(dir, 0755)
	}
	return os.WriteFile(t.Path, []byte(data), 0644)
}

func readSeedTarget(t seedTarget) (string, error) {
	b, err := os.ReadFile(t.Path)
	if err != nil {
		return "", err
	}
	return string(b), nil
}
