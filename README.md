# 好市多目擊情報

手機打開這個網頁，會列出今購百科「賣場目擊情報」的日期和星期。點進去只看該篇照片，沒有廣告、側欄和推薦文。

照片仍從 daybuy 的圖床載入。這個網站只保存圖片網址，不複製圖檔，也不轉載內文。

## 本機預覽

```powershell
python scripts/sync_posts.py
python -m http.server 8080
```

瀏覽器打開 http://localhost:8080/ 。不要直接用檔案總管開 `index.html`，否則讀不到 `data/posts.json`。

## 放到 GitHub Pages

1. 在 GitHub 建一個**公開**倉庫。免費的 GitHub Pages 需要公開倉庫。
2. 把這個資料夾推上去。
3. 到倉庫的 Settings → Pages。
4. Build and deployment 選 Deploy from a branch。
5. 分支選你推上去的那個（這個資料夾目前是 `master`），資料夾選 `/ (root)`，再按 Save。
6. 等一兩分鐘。網址會是 `https://<帳號>.github.io/<倉庫名>/`，手機開這個即可。

更新靠 GitHub Actions，大約每 2 小時抓一次最近 30 篇，有變動才會寫回 `data/posts.json`。也可以到 Actions 頁面手動跑 **Sync posts**。

若手動執行被拒絕寫入，到 Settings → Actions → General → Workflow permissions，選 **Read and write permissions**。

抓取失敗時腳本會停下來，不會用空資料蓋掉現有清單。

## 限制

- 不是即時。新文章最快大約 2 小時後出現，GitHub 的排程有時還會再晚一點。
- 若 daybuy 改掉 API，或不再允許其他網站載入圖片，清單或照片會失效，要再調整 `scripts/sync_posts.py`。
