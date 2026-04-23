const binaryOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. なし" },
  { value: "1", label: "1. あり" },
];

const respirationOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. 成人12～20回/分　高齢者14～20回/分程度" },
  { value: "1", label: "1. 平均値より頻回・少ない回数" },
];

const spo2Options = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. 96％～99％" },
  { value: "1", label: "1. 平均値より高値・低値" },
];

const tempOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. 36～37℃　高齢者35.0～36.5℃台" },
  { value: "1", label: "1. 高温・低値（悪寒・戦慄）" },
];

const bpOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0：収縮120/80mmHg以下　75歳以上130/80mmHg以下" },
  { value: "1", label: "1. 平均値より高値・低値" },
];

const pulseOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. 51～90回/分" },
  { value: "1", label: "1. 50以下、91以上" },
];

// page15: 精神心理・行動面の評価項目JSON定義。
const page15 = {
  id: 15,
  formTitle: "APOS-HC 調査票",
  badge: "No.15",
  fields: [
    {
      type: "group",
      key: "diseaseSigns",
      label: "Ⅰ　疾病の兆候",
      fields: [
        {
          type: "select",
          key: "vital_change_overall",
          label: "1. 何かが変だ",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 特に変化を感じない／状態に変化がない" },
            { value: "1", label: "1. いつもと表情が違う・視線が違う・声の調子が違う・体の動き・動作が普段と違う等" },
          ],
        },
        {
          type: "textarea",
          key: "vital_change_overall_detail",
          label: "具体的な症状",
          rows: 3,
          visibleIf: { field: "vital_change_overall", equals: "1" },
          placeholder: "例）表情が硬い、視線が合わない、声がかすれる、動作が緩慢 など",
        },
      ],
    },
    {
      type: "group",
      key: "vitalSigns",
      label: "バイタルサインの変化",
      fields: [
        { type: "select", key: "respiration_rate", label: "1. 呼吸数", options: respirationOptions },
        { type: "select", key: "vital_spo2", label: "2. SpO2", options: spo2Options },
        { type: "select", key: "vital_temp", label: "3. 体温", options: tempOptions },
        { type: "select", key: "vital_bp", label: "4. 血圧", options: bpOptions },
        { type: "select", key: "vital_pulse", label: "5. 脈拍", options: pulseOptions },
        {
          type: "select",
          key: "consciousness_level",
          label: "6. 意識レベル",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 覚醒" },
            { value: "1", label: "1. 覚醒だが変化あり" },
            { value: "2", label: "2. 意識なし" },
          ],
        },
        {
          type: "select",
          key: "skin_changes",
          label: "7. 皮膚の変化",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. なし" },
            { value: "1", label: "1. 冷汗・湿潤・末梢冷汗・チアノーゼ" },
          ],
        },
        {
          type: "image_display",
          key: "news_reference_image",
          label: "NEWS基準表",
          src: "../Vital.png",
          alt: "バイタルサイン基準表",
          caption: "早期警告スコア(NEWS)",
        },
      ],
    },
    {
      type: "group",
      key: "respiratoryGrade",
      label: "呼吸・心機能評価",
      fields: [
        {
          type: "select",
          key: "breath_grade",
          label: "3. 呼吸（グレード分類）",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 激しい運動時のみ息切れ" },
            { value: "1", label: "1. 早足や上り坂で息切れ" },
            { value: "2", label: "2. 平坦路でも息切れしやすい" },
            { value: "3", label: "3. 少し歩くと立ち止まる" },
            { value: "4", label: "4. 安静時も息切れ" },
          ],
        },
        {
          type: "select",
          key: "nyha_class",
          label: "4. NYHA心機能分類",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 心疾患なし" },
            { value: "I", label: "I" },
            { value: "II", label: "II" },
            { value: "III", label: "III" },
            { value: "IV", label: "IV" },
          ],
        },
      ],
    },
  ],
};

export default page15;
