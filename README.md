# 黑熊市長 TestFlight 上傳流程

這個公開專案只放上傳流程，不放遊戲。遊戲原始碼在私人專案；公開專案可以免費使用 GitHub 的雲端 Mac。

## 流程

1. 私人專案的 `Tools/Publish-TestFlight.ps1` 在 Windows 上用 Unity 匯出 iOS 的 Xcode 專案。
2. 匯出結果以 AES-256 加密，附加到這裡的 release。公開的只有加密檔，沒有密碼打不開。
3. `.github/workflows/ios-testflight.yml` 在雲端 Mac 上執行：
   - 解密 Xcode 專案；
   - 用 App Store Connect API 金鑰建立暫時的簽署憑證；
   - 編譯、上傳 TestFlight，並把新版本交給內部測試員；
   - 刪除暫時憑證。

## 需要的 Secrets（Settings → Secrets and variables → Actions）

| 名稱 | 內容 |
|---|---|
| `APPLE_ASC_KEY_ID` | App Store Connect API 金鑰的 Key ID |
| `APPLE_ASC_ISSUER_ID` | App Store Connect API 的 Issuer ID |
| `APPLE_ASC_KEY_P8` | `.p8` 金鑰檔的完整內容 |
| `BUILD_PASSPHRASE` | 加密 Xcode 專案用的密碼，必須和本機密碼檔相同 |

Bundle ID：`tw.blackbearmayor.game`。Workflow 的 `action=register` 會註冊 Bundle ID，並檢查 App Store Connect 的 App 紀錄。

## 九命夢境

同一套流程也上傳《九命夢境》：`.github/workflows/ninelives-testflight.yml`，共用上面四個 Secrets（同一個 Apple 開發者團隊和 API 金鑰、同一個加密密碼）。
遊戲端是九命夢境專案的 `Tools/Publish-TestFlight.ps1`，release 的標籤是 `nld-ios-<build>`。Bundle ID：`tw.ninelivesdream.game`。
