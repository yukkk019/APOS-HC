// page8: 健康状態・既往歴関連のJSON定義。
const page8 = {
  id: 8,
  formTitle: "APOS-HC 調査票",
  badge: "No.8",
  fields: [
    {
      type: "group",
      key: "excretion",
      label: "1　スムーズな排泄",
      fields: [
        {
          type: "group",
          key: "urination",
          label: "1. 排尿（過去7日間）",
          fields: [
            {
              type: "select",
              key: "status",
              label: "尿の状態",
              options: [
                { value: "", label: "選択してください" },
                { value: "normal", label: "0. 問題なし" },
                { value: "abnormal", label: "1.問題あり（血が混じっている・濁っている・フワフワ浮いているものがある・強い尿臭あり）" },
              ],
            },
            {
              type: "select",
              key: "urge",
              label: "尿意",
              options: [
                { value: "", label: "選択してください" },
                { value: "no", label: "0. 尿意がない" },
                { value: "yes", label: "1. 尿意がある" },
              ],
            },
            {
              type: "select",
              key: "frequency",
              label: "尿の回数",
              options: [
                { value: "", label: "選択してください" },
                { value: "4-7", label: "0. 1日4〜7回" },
                { value: "1-2", label: "1. 1日1〜2回・昼間8回以上・夜間3回以上" },
                { value: "none", label: "2. 排尿がない" },
              ],
            },
            {
              type: "select",
              key: "control",
              label: "排尿のコントロール",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 自分でコントロールでき違和感なし" },
                { value: "1", label: "1. 咳やくしゃみで漏れる/間に合わない/違和感" },
                { value: "2", label: "2. いきみ排尿・残尿感・陰部のかゆみ" },
                { value: "3", label: "3. 昼夜失禁・排尿痛・下腹部痛" },
              ],
            },
          ],
        },
        {
          type: "group",
          key: "defecation",
          label: "2.排便（過去7日間）",
          fields: [
            {
              type: "select",
              key: "status",
              label: "便の状態",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 問題なし（軟らかいソーセージ状、バナナ状、半固形状の便）" },
                { value: "a", label: "1. コロコロ便" },
                { value: "b", label: "2. 凸凹した硬い便" },
                { value: "c", label: "3. 軟らかな泥状便" },
                { value: "d", label: "4. 水様便" },
                { value: "e", label: "5. 色異常便（赤/白/黒/黄/赤褐色など）" },
              ],
            },
            {
              type: "select",
              key: "frequency",
              label: "排便の周期",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 苦痛のない排便周期" },
                { value: "1", label: "1. 周期がなく腹部膨満・苦痛" },
                { value: "2", label: "2. 排便訓練不足で便秘" },
              ],
            },
            {
              type: "select",
              key: "control",
              label: "排便のコントロール",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 自分でコントロールできる" },
                { value: "1", label: "1. 通常は失禁しない（まれにある）" },
                { value: "2", label: "2. 月に数回失禁する" },
                { value: "3", label: "3. 週1回以上失禁する" },
                { value: "4", label: "4. 完全失禁状態" },
              ],
            },
            {
              type: "select",
              key: "adjustMethod",
              label: "排便の調整方法",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 食事/水分/運動/排便訓練で調整できている" },
                { value: "1", label: "1. 基本対策 + 時々下剤で調整" },
                { value: "2", label: "2. 下剤、敵便、浣腸等で主に調整。食事、運動、排便訓練はたまに行う" },
                { value: "3", label: "3. 一貫して下剤・摘便・浣腸で調整" },
                { value: "4", label: "4. 多剤下剤使用で基本対策なし" },
              ],
            },
          ],
        },
        {
          type: "multi",
          key: "excretionMethod",
          label: "3.排泄の仕方",
          options: [
            { value: "A", label: "A. 自力でトイレ" },
            { value: "B", label: "B. 介助でトイレ" },
            { value: "C", label: "C. ポータブルトイレ" },
            { value: "D", label: "D. 夜のみおむつ（失禁パッド等）" },
            { value: "E", label: "E. 1日中おむつ（失禁パッド等）" },
            { value: "F", label: "F. 差し込み便器・尿器" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "skinNailCare",
      label: "Ⅱ　皮膚・爪のケア",
      fields: [
        {
          type: "select",
          key: "cleanliness",
          label: "清潔・整容",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 定期的な清潔ケアができ清潔に保たれている" },
            { value: "1", label: "1. 時折ケアできるが時に汚れが目立つ" },
            { value: "2", label: "2. たまにケアできるが汚れが目立つ" },
            { value: "3", label: "3. ほとんどケアせず汚れている" },
          ],
        },
        {
          type: "select",
          key: "skinNailStatus",
          label: "皮膚・爪の状態",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 汚れ・発赤・湿疹等なくきれい" },
            { value: "1", label: "1. 汚れ・かゆみ・発汗・発赤等がある" },
            { value: "2", label: "2. 足色変化・冷感・動脈触知異常・痛み違和感がある" },
            { value: "3", label: "3. 爪白癬・巻き爪・胼胝・鶏眼・外反母趾などがある" },
          ],
        },
        {
          type: "select",
          key: "woundStatus",
          label: "創傷",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 観察できる傷はない" },
            { value: "1", label: "1. 治癒のための肉芽が形成されている" },
            { value: "2", label: "2. 肉芽形成が始まったばかり" },
            { value: "3", label: "3. 治療されず放置状態" },
          ],
        },
      ],
    },
  ],
};

export default page8;
