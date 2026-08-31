package engine

import (
	"strconv"
)

// TaskArgsBuilder 负责将结构化矩阵任务组装为各大平台 CLI 命令行参数
type TaskArgsBuilder struct {
	WorkDir string
}

func NewTaskArgsBuilder(workDir string) *TaskArgsBuilder {
	return &TaskArgsBuilder{WorkDir: workDir}
}

// BuildTaskArgs 针对单个全景矩阵任务组装精准的平台命令行参数
func (b *TaskArgsBuilder) BuildTaskArgs(task AccountPublishTask) []string {
	action := task.Action
	if action == "" {
		action = "upload-video"
	}

	absFilePath := ResolveToAbsPath(b.WorkDir, task.FilePath)
	absThumbnail := ResolveToAbsPath(b.WorkDir, task.Thumbnail)
	absThumbLand := ResolveToAbsPath(b.WorkDir, task.ThumbnailLandscape)
	absThumbPort := ResolveToAbsPath(b.WorkDir, task.ThumbnailPortrait)
	absNotef := ResolveToAbsPath(b.WorkDir, task.Notef)

	var absImages []string
	for _, img := range task.Images {
		if abs := ResolveToAbsPath(b.WorkDir, img); abs != "" {
			absImages = append(absImages, abs)
		}
	}

	args := []string{
		task.Platform, action,
		"--account", task.Account,
	}

	// 基础媒体与文本参数
	if absFilePath != "" && action == "upload-video" {
		args = append(args, "--file", absFilePath)
	}
	if len(absImages) > 0 && action == "upload-note" {
		args = append(args, "--images")
		args = append(args, absImages...)
	}
	if task.Title != "" {
		args = append(args, "--title", task.Title)
	}
	if task.Desc != "" {
		args = append(args, "--desc", task.Desc)
	}
	if task.Tags != "" {
		args = append(args, "--tags", task.Tags)
	}

	// 封面图支持
	if absThumbnail != "" {
		args = append(args, "--thumbnail", absThumbnail)
	}
	// 横竖版封面: 仅 douyin 与 tencent 支持
	if (task.Platform == "douyin" || task.Platform == "tencent") && action == "upload-video" {
		if absThumbLand != "" {
			args = append(args, "--thumbnail-landscape", absThumbLand)
		}
		if absThumbPort != "" {
			args = append(args, "--thumbnail-portrait", absThumbPort)
		}
	}

	// 定时发布: 仅 douyin, kuaishou, xiaohongshu, bilibili, tencent 支持
	if task.Schedule != "" {
		switch task.Platform {
		case "douyin", "kuaishou", "xiaohongshu", "bilibili", "tencent":
			args = append(args, "--schedule", task.Schedule)
		}
	}

	// 合规/原创/AI声明
	if task.Declaration != "" {
		switch task.Platform {
		case "douyin", "xiaohongshu", "bilibili":
			args = append(args, "--declaration", task.Declaration)
		}
	}

	// 专栏/合集
	if task.Collection != "" && action == "upload-video" {
		switch task.Platform {
		case "douyin", "kuaishou", "tencent", "alipay", "weibo", "baijiahao":
			args = append(args, "--collection", task.Collection)
		}
	}

	// B站特定分区 (TID)
	if task.Platform == "bilibili" && task.Tid > 0 && action == "upload-video" {
		args = append(args, "--tid", strconv.Itoa(task.Tid))
	}

	// 微信视频号特定选项
	if task.Platform == "tencent" && action == "upload-video" {
		if task.ShortTitle != "" {
			args = append(args, "--short-title", task.ShortTitle)
		}
		if task.Category != "" {
			args = append(args, "--category", task.Category)
		}
		if task.Draft {
			args = append(args, "--draft")
		}
	}

	// 抖音/视频号特定带货
	if action == "upload-video" {
		if task.ProductLink != "" {
			args = append(args, "--product-link", task.ProductLink)
		}
		if task.ProductTitle != "" {
			args = append(args, "--product-title", task.ProductTitle)
		}
	}

	// YouTube 特定可见性与播放列表
	if task.Platform == "youtube" && action == "upload-video" {
		if task.Visibility != "" {
			args = append(args, "--visibility", task.Visibility)
		}
		if task.Playlist != "" {
			args = append(args, "--playlist", task.Playlist)
		}
	}

	// 图文特有参数
	if action == "upload-note" {
		if task.Platform == "douyin" && task.Bgm != "" {
			args = append(args, "--bgm", task.Bgm)
		}
		if task.Note != "" {
			args = append(args, "--note", task.Note)
		}
		if task.Platform == "douyin" && absNotef != "" {
			args = append(args, "--notef", absNotef)
		}
	}

	// 运行模式 (bilibili 命令行封装不接收 --headless/--headed 参数)
	if task.Platform != "bilibili" {
		if task.Headless {
			args = append(args, "--headless")
		} else {
			args = append(args, "--headed")
		}
	}

	return args
}
