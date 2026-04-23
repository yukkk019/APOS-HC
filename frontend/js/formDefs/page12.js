const scoreOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0" },
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
];

// page12: 移動・姿勢・補助具関連のJSON定義。
const page12 = {
  id: 12,
  formTitle: "APOS-HC 調査票",
  badge: "No.12",
  fields: [
    {
      type: "group",
      key: "psyScreening",
      label: "Ⅰ　精神症状の状況(特異行動と重症度)",
      fields: [
        {
          type: "select",
          key: "has_psy",
          label: "認知症・精神疾患はありますか。",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "なし" },
            { value: "1", label: "あり" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "npiq",
      label: "１.　NPI-Q(BPSD：行動・心理障害評価)の項目",
      visibleIf: { field: "has_psy", equals: "1" },
      fields: [
        {
          type: "select",
          key: "information_provider",
          label: "情報提供者",
          options: [
            { value: "", label: "選択してください" },
            { value: "1", label: "1. 配偶者" },
            { value: "2", label: "2. 子供" },
            { value: "3", label: "3. 子供の配偶者" },
            { value: "4", label: "4. 介護福祉士・ヘルパー" },
            { value: "5", label: "5. 訪問看護師" },
            { value: "6", label: "6. その他" },
          ],
        },
        {
          type: "text",
          key: "information_provider_other",
          label: "情報提供者（その他）",
          visibleIf: { field: "information_provider", equals: "6" },
        },
        { type: "select", key: "npiq_delusion", label: "① 妄想", options: scoreOptions },
        { type: "select", key: "npiq_hallucination", label: "② 幻覚・幻視", options: scoreOptions },
        { type: "select", key: "npiq_agitation", label: "③ 興奮", options: scoreOptions },
        { type: "select", key: "npiq_depression", label: "④ うつ", options: scoreOptions },
        { type: "select", key: "npiq_anxiety", label: "⑤ 不安", options: scoreOptions },
        { type: "select", key: "npiq_euphoria", label: "⑥ 多幸", options: scoreOptions },
        { type: "select", key: "npiq_apathy", label: "⑦ 無関心", options: scoreOptions },
        { type: "select", key: "npiq_disinhibition", label: "⑧ 脱抑制", options: scoreOptions },
        { type: "select", key: "npiq_irritability", label: "⑨ 易刺激性", options: scoreOptions },
        { type: "select", key: "npiq_abnormal_behavior", label: "⑩ 異常行動", options: scoreOptions },
        { type: "select", key: "npiq_night_behavior", label: "⑪ 夜間行動", options: scoreOptions },
        { type: "select", key: "npiq_eating_behavior", label: "⑫ 食の行動", options: scoreOptions },
        {
          type: "text",
          key: "npiq_total_score",
          label: "NPI-Q合計点",
          inputType: "number",
        },
        {
          type: "textarea",
          key: "npiq_score_note",
          label: "総特異行動の詳細/上記以外の特異行動",
          rows: 4,
          placeholder: "補足や特記事項があればご記入ください",
        },
      ],
    },
  ],
};

export default page12;
