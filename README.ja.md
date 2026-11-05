# Sprite Motion Lab

正面・横・後ろの原画から、部品登録・歩行作成・検査・再現まで進めるローカル制作ツールとエージェント用スキルです。MITライセンスの実験的OSSです。

**3枚を入れれば完成アニメが出るモデルではありません。** 元絵の確認、見えない部分の作画、手足の所有関係、関節・服の境界の登録、実際の再生確認は人の判断が必要です。画像生成サービスは内蔵していません。

## 起動

Python 3.10以上を用意し、このフォルダで実行します。

```sh
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

同じコンピューターの http://127.0.0.1:8765 を開きます。三方向の幾何学デモ、手動マスク・関節編集、部品差し替え、再生、コマ送り、PNGシートとJSONの書き出しがあります。開発用サーバーなのでインターネットへ公開しないでください。

## 入口

- 新しいキャラ: [3原画からの制作手順](docs/CHARACTER_WORKFLOW.md)
- 描き起こした全身セル／共通上半身: [セルの登録と書き出し](docs/DRAWN_CEL_WORKFLOW.md)
- 手動登録したメッシュ／投影歩行: [既存エンジン手順](docs/REUSABLE_WORKFLOW.md)
- 固定した頭・胴と独立した手足: [明示的なレイヤー登録](docs/LAYERED_MOTION.md)
- 腕・服・継ぎ目・支持交換・再生確認: [制作チェック](docs/PRODUCTION_CHECKS.md)
- スキル: [.agents/skills/sprite-motion-workflow](.agents/skills/sprite-motion-workflow/SKILL.md)

元画像や私有キャラクター素材は含めません。デモはコードから新しく描く単純図形です。顔や体格をコマごとに描き直したり、拡大縮小で揃えたりしません。前後方向を横向きの反転で代用せず、実際の原画と視点から登録します。

数値・透過・全コマ静止画・再現テストの合格は、自然な動作を保証しません。通常速度の連続再生を観察できていない場合、動画品質は **UNREVIEWED（未確認）** と記録します。末尾の重複、往復の見え方、顔や胴の揺れ、支持交換での落下は別途確認します。

導入・テスト・ライセンスと制約の詳細は [English README](README.md)。自分で読み込んだ画像や外部で生成した画像の権利は、このソフトのMITライセンスとは別です。
