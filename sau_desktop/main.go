package main

import (
	"embed"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	// Create an instance of the app structure
	app := NewApp()

	// Create application with options
	err := wails.Run(&options.App{
		Title:     "小映分发助手",
		Width:     1680,
		Height:    1020,
		MinWidth:  1280,
		MinHeight: 800,
		AssetServer: &assetserver.Options{
			Assets:  assets,
			// 暴露本机视频只读通道，供前端预览缩略图/播放
			Handler: mediaPreviewHandler(),
		},
		BackgroundColour: &options.RGBA{R: 15, G: 23, B: 42, A: 1},
		OnStartup:        app.startup,
		// 启用原生文件/文件夹拖拽（Wails v2.10+）：拖入后返回绝对路径，
		// 由 app.go 的 OnFileDrop 回调解析文件夹结构
		DragAndDrop: &options.DragAndDrop{
			EnableFileDrop: true,
			// 阻止 WebView 自己处理拖放：
			// Wails 抢到拖放并回调路径后，若不禁用 WebView 的拖放，事件仍会交还给 WKWebView/WebView2，
			// 后者按默认行为"打开被拖入的文件" → 拖入视频会整页变成全屏播放器、拖入文件夹变成文件列表。
			// 开启后，拖放事件止步于 Wails，状态栏光标仍显示为常规拖放样式。
			DisableWebViewDrop: true,
		},
		Bind: []interface{}{
			app,
		},
		Mac: &mac.Options{
			TitleBar:             mac.TitleBarDefault(),
			Appearance:           mac.DefaultAppearance,
			WebviewIsTransparent: false,
			WindowIsTranslucent:  false,
		},
	})

	if err != nil {
		println("Error:", err.Error())
	}
}
