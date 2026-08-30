//go:build !windows && !darwin

package auth

import (
	"os"
	"path/filepath"
)

func getSeedBackupTargets() []seedTarget {
	home, _ := os.UserHomeDir()
	p1 := filepath.Join(home, ".config", ExecutableName, "seed.json")
	p2 := filepath.Join(home, ".local", "share", ExecutableName, "seed.json")

	return []seedTarget{
		{Path: p1, Kind: seedTargetFile},
		{Path: p2, Kind: seedTargetFile},
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
