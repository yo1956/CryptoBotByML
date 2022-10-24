# 機械学習によるビットコイン自動売買ボット(Bybit用) -richmanbtcさんチュートリアル版- 

richmanbtcさん作成の機械学習ボットチュートリアルで作成されたモデルを利用したビットコインの自動売買ボットです。  
https://github.com/richmanbtc/mlbot_tutorial

mlbotの初心者向けチュートリアル(Bybit版)で作成したモデルを利用しており、BybitのBTC/USDTのペアで動作する自動売買ボットとなります。
https://gist.github.com/amdapsi/a2731d45720ec0aba89959bb4f5ad5ce

ポジションモードとしてはワンウェイモードにのみ対応しています。
設定のボタンからポジションモードを選択することができます。
デフォルトではヘッジモードになっているためワンウェイモードに切り替えをおこないます。

## 起動方法

### 前提条件

mlbotの初心者向けチュートリアル(Bybit版)が実行できていること  
Bybitにアカウントがあること

### BybitでAPIキーとシークレットキーを取得

APIについては以下を参照  
https://help.bybit.com/hc/ja/articles/360039749613-API%E7%AE%A1%E7%90%86

### モデルの作成と配置

mlbotの初心者向けチュートリアル(Bybit版)で作成したLightGBMのモデルである model_y_buy_bybit.xzとmodel_y_sell_bybit.xz をmodelフォルダに格納。

### 以下の形式で本フォルダ直下に.envファイルを作成

```
API_KEY={Bybitで取得したAPIキー}
SECRET_KEY={Bybitで取得したシークレットキー}
LOT=0.01 //発注ロット
MAX_LOT=0.03 //最大ロット
INTERVAL=15(売買間隔)
TESTNET=TRUE //テストネットで動作させる場合に追加(任意)
```

### dockerビルド
```bash
docker build . -t paibot-bybit
```

### dockerコンテナ起動
```bash
docker run -d -it --env-file=.env --name=paibot-bybit paibot-bybit
```

### 起動状況確認
```bash
docker container logs -t paibot-bybit
```

### dockerコンテナの停止・削除
```bash
docker stop paibot-bybit
docker container prune
```
