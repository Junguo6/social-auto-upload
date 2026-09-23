package auth

import (
	"fmt"
	"strings"
	"testing"
)

func TestDeviceIdentityAndOverview(t *testing.T) {
	identity, err := GetDeviceIdentity()
	if err != nil {
		t.Fatalf("GetDeviceIdentity failed: %v", err)
	}

	fmt.Printf("生成的设备识别码 NewSN: %s, MachineID: %s\n", identity.NewSN, identity.MachineID)
	if len(identity.NewSN) != 16 {
		t.Fatalf("NewSN length must be 16, got %d (%s)", len(identity.NewSN), identity.NewSN)
	}

	// 测试请求 Overview
	client := NewClient()
	overview, err := client.FetchOverview(identity, "")
	if err != nil {
		fmt.Printf("Overview 请求注意 (可能网络或新设备尚未注册): %v\n", err)
	} else {
		fmt.Printf("Overview 请求成功: UserId=%s, IsActivated=%v, M122Activated=%v, DaysRemaining=%d, Deadline=%s\n",
			overview.UserId, overview.IsActivated, overview.M122Activated, overview.DaysRemaining, overview.Deadline)
	}

	// 测试输入错误激活码，应当抛出错误而不是成功
	_, err = client.ApplyActiveCode(identity, "INVALID_CODE_123456", overview.UserId)
	if err == nil {
		t.Fatalf("输入无效激活码应当报错，但却成功了！")
	} else {
		fmt.Printf("输入无效激活码预期报错拦截成功: %v\n", err)
	}
}

// TestGenerateDeviceID_UsesBase58Charset 识别码只允许 Base58 字符：
// 不能出现易混字符 0 / O / I / l
func TestGenerateDeviceID_UsesBase58Charset(t *testing.T) {
	const allowed = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
	for i := 0; i < 500; i++ {
		id := GenerateDeviceID(fmt.Sprintf("machine-%d", i), fmt.Sprintf("seed-%d", i))
		if len(id) != 16 {
			t.Fatalf("识别码长度应为 16，实际 %d（%s）", len(id), id)
		}
		for _, ch := range id {
			if !strings.ContainsRune(allowed, ch) {
				t.Fatalf("识别码 %s 出现非 Base58 字符 %q（易混字符 0/O/I/l 必须被排除）", id, ch)
			}
		}
	}
}
