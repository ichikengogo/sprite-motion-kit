# 原画から歩行を作る：描き起こしセル／登録リグ

## 新しいキャラの共通入口

まず [CHARACTER_WORKFLOW.md](CHARACTER_WORKFLOW.md) と `character_workflow.py` で3原画を保存し、元絵を実見して体格・衣装境界・小物・手の接触・左右所有・viewごとの方式をprofileに記録します。未決定を止め、実際の確認後にprovider中立の作画要求を出します。要求生成と画像生成は別工程で、実素材と登録ができてから各viewをbindして3方向を書き出します。特定キャラの完成例を別キャラの設定として流用しません。

元絵の顔・体格を固定尺度で保ち、自由腕／把持腕はview固有条件に従います。位相の違うポーズが混ざったりコマ間で跳ぶ場合は、元絵と前後の実コマを同時参照して区間だけ作り直します。足裏の移動距離÷実時間と顔・髪・胴体の時系列を人が確認し、時間延長を中割りと呼ばないでください。詳細は共通入口のtransition/art gate手順を参照してください。

実時間の動画確認は独立した必須ゲートです。確認者・手段・正確な対象ハッシュ・通常速度1×・原寸と128px・実観察周回数・連続性所見を残します。静止画／抽出コマ／時間情報／数値検査では代用できません。観察手段がなければ **BLOCKED / UNREVIEWED** とし、見たとは書かないでください。顔・体格の時系列揺れが残る版は不合格であり、「改善した試作」という表現で受入を代用しません。

## 制作方式を選ぶ

腰・太もも・衣服を別々に変形して崩れが繰り返す場合は、その版への継ぎ足しを止め、[描き起こしセルの実行手順](DRAWN_CEL_WORKFLOW.md)と `drawn_cel.py` を使います。元絵基準の接地・沈み・通過・蹴り出しから、近脚／遠脚の役割が本当に交代する周期を作り、顔・髪・小物など動かさない部分は、元絵の姿勢が許せば共通セルで維持できます。腰後端の元布を胴裾の背面へ重ね、水平切断で尻を浮かせないこと、元衣装の全周・丈・肌との境界を守ることが必須です。

これはリグの追加プリセットではなく独立したセル組立経路です。既定のリグ描画は変更しません。承認済みの私有例は再現テストに使い、他キャラへ座標・体型・品質保証を転用しません。数値検査と人の視覚判断は分け、10枚のセルを24枚の新しい中割りと偽って扱いません。

以下は従来の登録リグによる3方向制作手順です。原画に適した方式を方向ごとに選び、変更不要な方向は保持してください。

3方向それぞれの原画で歩行DRAFTを作り、全コマを確認する再利用フローです。横絵の反転で前後を代用しません。**自動切り抜き・自動関節登録・隠れ面復元・完成品質の自動認定はしません。**

## 1. 素材と同一キャラクターを確認

透過PNGを正面・横・背面で1枚ずつ用意します。切り分ける前に、顔（見える方向）、髪・服・配色・小物・靴が同じキャラか比較します。別の顔や説明できない違いがあれば、正しい原画を確認してから進めます。ファイル検査だけではこの判断はできません。

```sh
cd sprite-motion-lab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python workflow.py init --front /path/front.png --side /path/side.png --back /path/back.png --out work/my-character
# 実際に3原画を比較し、証拠画像を保存してから記録
python workflow.py identity work/my-character/manifest.json --evidence review/three-originals.png --note '顔・髪・服・小物・靴と中立体型を3原画で比較し、同一キャラと確認した'
python server.py
```

`identity`は原画ハッシュに結び付いた人の確認記録で、`bind`前に必須です。自動顔認識ではありません。

`init`は原画をそのまま保存しハッシュを記録します。出力先は新規フォルダが必要です。ブラウザはサーバー実行機の http://127.0.0.1:8765 を開きます。

## 2. 各方向を手動登録

各原画の部品・関節・描画順・隠れた部分を整え、実画素を確認します。候補生成は下書きです。前後は手動の`projectedWalk`登録が必要で、画像を入れるだけでは完成しません。原画座標と正規化座標、画面左右と人物の左右を区別してください。隠れ面の追加生成は別途許可・確認が必要です。

中立姿勢の体型を決め、各方向の表示尺度を固定します。**毎フレームの外接矩形を同じ高さへ引き伸ばさない**でください。既存私有例の脚比率・身長・肉付きを新キャラへ自動適用しません。歩幅と反対位相の腕振りを調整し、保存JSONを再読込して確認します。

横の原画で手が鞄の紐などを握っている場合、歩行中もその姿勢を保つにはリグへ任意の `armPose: "held-source"` を設定します。原画の上腕・前腕を胴体に追従させる横歩行専用の設定で、既定の腕振り・ダッシュは変えません。自由な腕振りを無理に与えず、元の肩・肘・手首の登録と手／紐／鞄の画素所有を確認してください。全周期で把持位置を目視し、隠れた部分が自動復元されたとは扱いません。

原画の股関節を左右それぞれ保持する必要がある横・simple歩行では、任意の `walkHipRegistration: "source"` を使用できます。既定は従来の横座標平均化です。支点はそのキャラの原画から登録し、骨長や体型変更で不自然な付け根を隠さないでください。`walkGarment` の原画切抜きパネルでは、`hemConnection` と組み合わせた `sourceHemMode: "preserve-x"` により、元の裾x座標を保って脚へ接続できます。矩形素材向けの既定幅登録とは用途が異なります。共通腰・股・脚口の画素所有と全周期の輪郭確認は引き続き必要で、どちらも自動補完や万能修正ではありません。

```sh
python workflow.py bind work/my-character/manifest.json saved-project.json
```

登録時の原画一致チェックは、3枚のキャラ同一性の目視確認を代行しません。

## 3. まず3方向DRAFTを書き出す

各方向の原画対応と中立体型を実際に確認し、証拠画像とメモを登録します。次は正面の例です。横・背面もそれぞれの証拠で行います。

```sh
python workflow.py attest work/my-character/manifest.json --view front --action walk --gate source_correspondence --evidence review/front-source.png --note '切り分け前に3原画の同一性を確認。正面の顔・服と登録元画像、補完箇所を照合した'
python workflow.py attest work/my-character/manifest.json --view front --action walk --gate proportions --evidence review/front-neutral.png --note '原画と中立姿勢を固定尺度で比較し、脚・頭・靴と裾位置を確認した'
python workflow.py export work/my-character/manifest.json --view all --action walk --mode draft --out work/walk-draft
```

`review/*.png`は自分の実際の確認画像を指定します。未確認のまま例文を記録しないでください。出力は`front/ side/ back/`別の透過PNGコマ・シート＋JSON、黒／シアン／マゼンタ／チェッカー背景の検査画像、24中間姿勢と確認記録です。各方向の`preview.gif`と3方向同時の`comparison.gif`も出ます。GIFは薄い灰色の背景付きプレビューで、ゲーム用透過素材はPNGです。実際の周期に合わせて再生します（GIFの時間単位の制約で、8コマ／1秒では120・130msへ丸め、JSONは125msを保持）。

## 4. 全コマ確認後に確認付きDRAFTへ

各方向で、原画対応・画素所有・関節・隠れ部品・体型・輪郭・衣服全周・踵・全周期の9項目を確認して記録します。通常色と高コントラスト背景、実寸とゲーム表示サイズで、全キーと中間姿勢を見てください。顔の維持、膝／すねの潰れ、腕と脚の逆位相、裾の穴、靴と足首、接地も確認します。

```sh
python workflow.py status work/my-character/manifest.json
python workflow.py export work/my-character/manifest.json --view all --action walk --mode reviewed-draft --out work/walk-reviewed-draft
```

**どちらもDRAFTです。** `reviewed-draft`は9項目の確認記録がある意味で、自動承認ではありません。原画・保存JSON・manifest内に保存された証拠を変更したら再確認します（証拠は`evidence/`へ複製されます）。前後は2D投影歩行で、3D再構成や任意素材での品質保証ではありません。前後ダッシュは未対応です。

設定・全コマの確認基準・正面の任意`legInterpolation: "linear"`と腕振り設定は、[skill手順](../.agents/skills/sprite-motion-workflow/references/workflow.md)と[目視確認基準](../.agents/skills/sprite-motion-workflow/references/quality.md)を参照してください。linearはすねの表面変形の選択肢で、全キャラへの万能修正ではありません。

## 次回の依頼例／配布

「この正面・背面・横の3枚を同一キャラか確認して、`$sprite-motion-workflow`で各方向の歩行を作って。体型の基準を固定し、全コマと中間姿勢を確認。未解決点はDRAFTとして残して」

skill単体ZIPは制作手順です。実行には同じ版のSprite Motion Labプロジェクト一式とPython依存が別途必要です。私有原画・画像入り保存JSON・確認画像は汎用ソースやskillへ混ぜません。グローバル導入・Macへの導入・公開・アップロードはこの手順に含みません。

### 腰から送り出す横歩行（任意の `walkHipDrive`）

`view: "side"`・`walkStyle: "simple"`・`walkHipRegistration: "source"` の手動登録済みリグに限り、`walkHipDrive` を明示できます。必須フィールドは `confirmed: true`、`pelvisShift`（0–8px）、`pelvisTilt`（0–0.12rad）、`torsoCounter`（0–0.05rad）、`swingLead`（0–0.35rad）。値は原画ごとに校正し、既存キャラの設定を転用しないでください。

- 腰の前後移動・傾きと控えめな胴体の逆運動を加え、遊脚では股関節を中心に太もも・すね全体を回転します。追加回転は遊脚端で角度・角速度がゼロとなる `sin²` 包絡です。骨長・靴倍率は変更せず、接地中の足目標は維持します。これは測定済み生体力学モデルではなく、手動調整する2D歩行です。
- 原画の近脚／遠脚に奥行き差がある場合は、任意の `gaitCenter: "source-ankles"` で各足の登録済み足首x座標を歩幅の中心にできます。省略時は従来の共通足首中心です。各脚の歩幅・接地速度、原画の股関節と足首高さは維持しますが、見かけの足間隔と到達補正は変わるので、左右半周期の沈み込み・接地・足の交差を必ず比較してください。
- `armPose: "held-source"` は引き続き胴体に追従します。腰周りの布は支点・所有領域・接続を別途登録し、動きを強めた結果の透けやゴム状の曲がりを隠さないでください。

最初に実時間GIFと接地→沈み→通過→上昇の連続姿勢を原寸／128pxで確認し、「腰から太ももが出る」運動が読めるかを判断します。全キー＋24中間姿勢で腰・脚口・膝・靴下・足首を対照背景確認し、保存JSON再生成と既定キャラ回帰も検査します。数値が合っていても動作や輪郭の合格にはなりません。設定なし・ダッシュ・中立原画は変更しません。

### Optional source cuff normals (side/simple walk)

A `jointMeshes[]` thigh/shin pair with `walkContour: "centerline"` may opt into
`walkCuffNormal: {"startY": ..., "endY": ...}`. Register these positive, increasing
Y coordinates (at most384) on that character's upright source material: the
cross-section normal smoothly follows the shin through this band, reaching the
shin normal at `endY`. This changes sampled material geometry only, not the
hip/knee/ankle trajectories, centerline, contacts, or source RGB. It is walk-only;
omission preserves the existing mapping. Values are not transferable anatomy
presets. This is not fabric synthesis or automatic clothing recognition.

Inspect the **entire original garment boundary and outer cloth coverage**, not
just knee-center alignment or opaque alpha. Compare source contours and all8 keys
plus24 phases at native/128px on contrasting backgrounds; check skin exposure,
cloth continuity, active mesh folds/compression, and foot continuity. A fully
opaque image or a centerline inside black material can still omit intended cloth
on the outside of a bent knee. Reject that semantic loss.
