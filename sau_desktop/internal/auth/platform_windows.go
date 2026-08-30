//go:build windows

package auth

import (
	"os"
	"path/filepath"

	"golang.org/x/sys/windows/registry"
)

func getSeedBackupTargets() []seedTarget {
	appdata := os.Getenv("APPDATA")
	userProfile := os.Getenv("USERPROFILE")

	p1 := filepath.Join(appdata, ExecutableName, "conf", "seed.json")
	p2 := `Software\` + ExecutableName
	p3 := filepath.Join(userProfile, "Documents", ".sau_seed_backup.json")

	return []seedTarget{
		{Path: p1, Kind: seedTargetFile},
		{Path: p2, Kind: seedTargetRegistry},
		{Path: p3, Kind: seedTargetFile},
	}
}

func writeSeedTarget(t seedTarget, data string) error {
	switch t.Kind {
	case seedTargetRegistry:
		key, _, err := registry.CreateKey(registry.CURRENT_USER, t.Path, registry.WRITE)
		if err != nil {
			return err
		}
		defer key.Close()
		return key.SetStringValue("RandomSeed", data)
	default:
		dir := filepath.Dir(t.Path)
		if dir != "" {
			_ = os.MkdirAll(dir, 0755)
		}
		return os.WriteFile(t.Path, []byte(data), 0644)
	}
}

func readSeedTarget(t seedTarget) (string, error) {
	switch t.Kind {
	case seedTargetRegistry:
		key, err := registry.OpenKey(registry.CURRENT_USER, t.Path, registry.READ)
		if err != nil {
			return "", err
		}
		defer key.Close()
		val, _, err := key.GetStringValue("RandomSeed")
		return val, err
	default:
		b, err := os.ReadFile(t.Path)
		if err != nil {
			return "", err
		}
		return string(b), nil
	}
}
