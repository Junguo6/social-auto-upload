package storage

// Driver 抽象存储驱动接口，使物理文件、嵌入式KV（如Badger/bbolt）、或内存存储可平滑替换
type Driver interface {
	// Read 读取指定键的数据内容；若不存在应返回空字节切片且 err == nil
	Read(key string) ([]byte, error)
	// Write 将数据原子写入指定键
	Write(key string, data []byte) error
	// Delete 删除指定键的数据
	Delete(key string) error
	// Exists 检查指定键是否存在
	Exists(key string) bool
}
