package auth

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"time"

	"github.com/denisbrodbeck/machineid"
	"github.com/zalando/go-keyring"
)

const (
	ExecutableName  = "SocialAutoUpload"
	keyringUsername = "device-seed-encrypt-key"
	base62Chars     = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)

var (
	keyringServiceName = ExecutableName
	seedLock           sync.Mutex
	cachedIdentity     *DeviceIdentity
	identityLock       sync.Mutex
)

// encodeBase62 将字节数组使用大整数算法编码为 Base62 字符串 (与小映/剪辑插件完全一致)
func encodeBase62(data []byte) string {
	if len(data) == 0 {
		return ""
	}

	bigInt := new(big.Int)
	bigInt.SetBytes(data)

	base := big.NewInt(62)
	zero := big.NewInt(0)
	result := ""

	for bigInt.Cmp(zero) > 0 {
		remainder := new(big.Int)
		bigInt.DivMod(bigInt, base, remainder)
		result = string(base62Chars[remainder.Int64()]) + result
	}

	return result
}

// GenerateDeviceID 生成新版识别码（16 位）：Base62(SHA256(machineid + random_seed)) 的前 16 位
func GenerateDeviceID(machineID, randomSeed string) string {
	sum := sha256.Sum256([]byte(machineID + randomSeed))
	full := encodeBase62(sum[:])
	if len(full) >= 16 {
		return full[:16]
	}
	return full
}

func generateSeedChecksum(rawSeed string) string {
	hash := sha256.Sum256([]byte(rawSeed))
	return hex.EncodeToString(hash[:])
}

func verifySeedChecksum(rawSeed, checksum string) bool {
	return generateSeedChecksum(rawSeed) == checksum
}

func encryptData(data []byte, keyStr string) (string, error) {
	key, err := base64.URLEncoding.DecodeString(keyStr)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	ciphertext := gcm.Seal(nonce, nonce, data, nil)
	return base64.URLEncoding.EncodeToString(ciphertext), nil
}

func decryptData(encryptedStr, keyStr string) ([]byte, error) {
	key, err := base64.URLEncoding.DecodeString(keyStr)
	if err != nil {
		return nil, err
	}

	data, err := base64.URLEncoding.DecodeString(encryptedStr)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return nil, fmt.Errorf("密文数据长度过短")
	}
	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	return gcm.Open(nil, nonce, ciphertext, nil)
}

// GetEncryptKeyFromKeyring 从系统密钥链获取加密密钥，不存在则生成并存储
func GetEncryptKeyFromKeyring() (string, error) {
	key, err := keyring.Get(keyringServiceName, keyringUsername)
	if err == nil && len(key) > 0 {
		return key, nil
	}

	// 读取失败，生成新的 32 字节 AES-256 密钥
	newKey := make([]byte, 32)
	if _, err := rand.Read(newKey); err != nil {
		return "", fmt.Errorf("生成加密密钥失败: %v", err)
	}
	keyStr := base64.URLEncoding.EncodeToString(newKey)

	if err := keyring.Set(keyringServiceName, keyringUsername, keyStr); err != nil {
		if runtime.GOOS == "linux" && errors.Is(err, keyring.ErrNotFound) {
			return keyStr, nil
		}
		// 若无法写入 keyring，尝试使用基于 machineID 的派生兜底密钥
		mid, _ := machineid.ID()
		if mid != "" {
			derived := sha256.Sum256([]byte("sau_fallback_salt_" + mid))
			return base64.URLEncoding.EncodeToString(derived[:]), nil
		}
		return keyStr, nil
	}
	return keyStr, nil
}

// GenerateRandomSeed 生成高熵随机种子（16 字节）
func GenerateRandomSeed() (string, error) {
	seed := make([]byte, 16)
	if _, err := rand.Read(seed); err != nil {
		return "", err
	}
	return base64.URLEncoding.EncodeToString(seed), nil
}

// WriteSeedToAllPaths 写入种子到所有备份路径
func WriteSeedToAllPaths(seedInfo *SeedInfo) error {
	seedLock.Lock()
	defer seedLock.Unlock()

	seedInfo.Checksum = generateSeedChecksum(seedInfo.RandomSeed)
	seedInfo.LastBackupAt = time.Now().UTC().Format(time.RFC3339)

	encryptKey, err := GetEncryptKeyFromKeyring()
	if err != nil {
		return err
	}

	seedJson, err := json.Marshal(seedInfo)
	if err != nil {
		return err
	}
	encryptedSeed, err := encryptData(seedJson, encryptKey)
	if err != nil {
		return err
	}

	targets := getSeedBackupTargets()
	var lastErr error
	for _, target := range targets {
		if target.Kind == seedTargetFile {
			dir := filepath.Dir(target.Path)
			if err := os.MkdirAll(dir, 0755); err != nil {
				lastErr = err
				continue
			}
		}

		if err := writeSeedTarget(target, encryptedSeed); err != nil {
			lastErr = err
			continue
		}
	}

	if lastErr != nil {
		return fmt.Errorf("部分路径写入失败: %v", lastErr)
	}
	return nil
}

// ReadSeedFromBackup 从备份路径读取种子并自动自愈修补缺失路径
func ReadSeedFromBackup() (*SeedInfo, error) {
	seedLock.Lock()
	defer seedLock.Unlock()

	encryptKey, err := GetEncryptKeyFromKeyring()
	if err != nil {
		return nil, err
	}

	targets := getSeedBackupTargets()

	var recovered *SeedInfo
	var usedTarget *seedTarget
	var missingTargets []seedTarget

	for _, target := range targets {
		encryptedSeed, err := readSeedTarget(target)
		if err != nil || encryptedSeed == "" {
			missingTargets = append(missingTargets, target)
			continue
		}

		decryptedData, err := decryptData(encryptedSeed, encryptKey)
		if err != nil {
			missingTargets = append(missingTargets, target)
			continue
		}
		var seedInfo SeedInfo
		if err := json.Unmarshal(decryptedData, &seedInfo); err != nil {
			missingTargets = append(missingTargets, target)
			continue
		}

		if !verifySeedChecksum(seedInfo.RandomSeed, seedInfo.Checksum) {
			missingTargets = append(missingTargets, target)
			continue
		}

		recovered = &seedInfo
		usedTarget = &target
		break
	}

	if recovered == nil {
		return nil, fmt.Errorf("所有备份路径均未找到有效种子")
	}

	// 自愈回写到其他缺失/损坏的目标路径
	if len(missingTargets) > 0 {
		recovered.Checksum = generateSeedChecksum(recovered.RandomSeed)
		recovered.LastBackupAt = time.Now().UTC().Format(time.RFC3339)

		seedJson, err := json.Marshal(recovered)
		if err == nil {
			if encryptedSeed, err := encryptData(seedJson, encryptKey); err == nil {
				for _, t := range missingTargets {
					if usedTarget != nil && t.Path == usedTarget.Path && t.Kind == usedTarget.Kind {
						continue
					}
					if t.Kind == seedTargetFile {
						dir := filepath.Dir(t.Path)
						_ = os.MkdirAll(dir, 0755)
					}
					_ = writeSeedTarget(t, encryptedSeed)
				}
			}
		}
	}

	return recovered, nil
}

func generateMachineID() (string, error) {
	mid, err := machineid.ID()
	if err != nil {
		return "FALLBACK_HOST_" + runtime.GOOS, nil
	}
	return mid, nil
}

// GetDeviceIdentity 获取当前设备的机器识别码与硬件信息 (单例缓存)
func GetDeviceIdentity() (*DeviceIdentity, error) {
	identityLock.Lock()
	defer identityLock.Unlock()

	if cachedIdentity != nil && cachedIdentity.NewSN != "" {
		return cachedIdentity, nil
	}

	mid, err := generateMachineID()
	if err != nil {
		return nil, fmt.Errorf("获取机器 ID 失败: %w", err)
	}

	recoveredSeed, err := ReadSeedFromBackup()
	if err != nil || recoveredSeed == nil || recoveredSeed.RandomSeed == "" {
		rawSeed, err := GenerateRandomSeed()
		if err != nil {
			return nil, fmt.Errorf("生成随机种子失败: %w", err)
		}

		seedInfo := &SeedInfo{
			RandomSeed: rawSeed,
			CreatedAt:  time.Now().UTC().Format(time.RFC3339),
		}
		if err = WriteSeedToAllPaths(seedInfo); err != nil {
			fmt.Printf("警告: 备份种子失败: %v\n", err)
		}
		recoveredSeed = seedInfo
	}

	newSN := GenerateDeviceID(mid, recoveredSeed.RandomSeed)
	cachedIdentity = &DeviceIdentity{
		MachineID: mid,
		NewSN:     newSN,
	}

	return cachedIdentity, nil
}
