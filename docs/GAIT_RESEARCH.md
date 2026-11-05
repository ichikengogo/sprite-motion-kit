# v0.6: research-informed gait（完成品質ではない）

`gaitProfile: "evidence-v1"` をrig JSONで明示すると有効。既定のlegacyは変えない。人物の体格・骨長はrig由来であり、成人の測定値をキャラクターへ移植しない。

## 調査→実装の対応
- [Oklahoma大学 gait introduction](https://www.ouhsc.edu/bserdac/dthompso/web/gait/intro.htm): 歩行の支持約60%/遊脚40%、左右位相差50%。実装はstance=.60、二重支持区間あり。24コマでは時間が量子化されるため、コマ数の割合と連続時間の割合は一致しない。
- [同 gait phases](https://www.ouhsc.edu/bserdac/dthompso/web/gait/terms.htm) / [Alberta大学](https://engcourses-uofa.ca/books/ortho/gait-analysis/): 踵接地→足底→前足部、約35%から踵上昇、60%で離地。walkのheel/flat/toeモードと足回転に対応。角度は絵柄に合わせた実験値であり測定値ではない。
- [歩行・走行の上下運動の一次研究](https://journals.physiology.org/doi/full/10.1152/jn.00081.2006): walkは支持中盤で上昇、dashは支持中に沈み浮遊で上昇する反対のroot波形。これは骨盤/root代理であり、質量を積分したCOMシミュレーションではない。preserveReach補正が波形を変えるため実キャラクターでも検査が必要。
- dash stance=.34は本試作のスタイル選択（普遍的測定値ではない）。左右位相差.5から連続時間で32%の両足非支持期間。足を早めに持ち上げ、終盤に下ろして後方へ引き戻すHermite軌道を使用。walkの再生速度変更だけではない。
- [腕の曲げ方の一次研究](https://pubmed.ncbi.nlm.nih.gov/31289110/) / [走行の腕振り](https://pubmed.ncbi.nlm.nih.gov/25031455/): 脚と逆位相の腕振り、dashで肘を深く曲げる。体幹の動力学は未実装。
- [加速時の姿勢](https://pmc.ncbi.nlm.nih.gov/articles/PMC4133722/): スタート直後の深い前傾を定常走行へ流用せず、dashは控えめな一定前傾。

## 靴底と支持面
`forefootContact`, `heelContact` は正規化座標の手動/画像由来目印で、足圧測定ではない。任意の `soleOutline`（3〜100点）はalpha輪郭の凸包を登録する。回転後の最下点を支持面に合わせ、靴底の突き抜けを防ぐ。遊脚には最大4pxの最小クリアランス曲線を足す（384pxキャンバスでのラスタ対策、研究値ではない）。骨長は不変、画像の変形なし。

この支持輪郭補正は転がる靴底の接点を変えるため、目印のY位置は固定ではない。`maxContactStepSlipPx` は同じモード内の目印移動量で、実際のラスタ靴底の接触・摩擦を証明しない。各足の元画像上の靴底高さは別々の投影面であり、単一の3D地面は復元していない。別途全コマのalpha>64最下点を検査する。

`render_neutral` は動きのない配置比較用。元画像と同一スケールで頭/体/服の裾と靴底を比較する。既存ソースの頭を保持した測定値と、独立したシルエット測定を混同しない。服に隠れた股・膝は推定で、比率の一致は解剖学的正しさを保証しない。

## 未達
衣服の境目、手首・肘の絵の連続性、遠側パーツのデザインは人の確認が必要。静止画1枚からの完全自動化、正確な人体復元、物理COM/足圧/3D接地、制作完成品質を主張しない。実キャラクターとAI補完素材は配布ソースに含めない。


## v0.9 purposeful walking style
The walking phase evidence stays unchanged:60%stance, opposite phase, double support, noflight. Stride100/lift10/bob1.3 before motionScale are artistic preset choices, not universal biomechanical measurements. Compared with coupled-v2 cautious walk, larger horizontal stride is deliberately decoupled from reduced lift and bob. Toe/heel rolls are.18/.06rad, also artistic calibration. A continuous periodic.15–.30px reach margin softens maximum extension without changing bone length. Cycle duration remains1.0s; a more purposeful pose is not simulated by speeding playback. `walkStyle` is opt-in and action-local; dash/neutral output is unchanged. Virtual root speed is derived from stride/(stance*duration), not an unrelated scrolling background.
