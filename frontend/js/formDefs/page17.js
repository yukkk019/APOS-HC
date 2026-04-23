const medicineRows = [
  "①風邪・ｲﾝﾌﾙｴﾝｻﾞ･ｺﾛﾅ",
  "②熱/痛みの薬",
  "③花粉症/呼吸器の薬",
  "④皮膚の薬",
  "⑤胃腸の薬",
  "⑥肝・胆・膵の薬",
  "⑦血圧と脳卒中",
  "⑧心臓の薬",
  "⑨腎臓・泌尿・痔",
  "⑩脳に働く薬",
  "⑪心の薬",
  "⑫脂質異常の薬",
  "⑬糖尿病の薬",
  "⑭痛風と甲状腺",
  "⑮骨の薬",
  "⑯血液と血管",
  "⑰膠原病とリュウマチ",
  "⑱眼の薬",
  "⑲耳と鼻の薬",
  "⑳細菌感染症薬",
  "㉑女性の薬",
  "㉒ﾋﾞﾀﾐﾝ･ﾐﾈﾗﾙ･栄養",
  "㉓漢方薬",
  "㉔その他(売薬・塗布薬含む)",
];

// page17: 関節可動域・麻痺等の評価と写真項目を含むJSON定義。
const page17 = {
  id: 17,
  formTitle: "APOS-HC 調査票",
  badge: "No.17",
  fields: [
    {
      type: "group",
      key: "medicationUsage",
      label: "Ⅰ　使用している薬と服薬の管理",
      fields: [
        {
          type: "photo_slots",
          key: "medication_photos",
          label: "薬の写真（最大3枚）",
          slotCount: 3,
        },
        { type: "text", key: "med_photo_1", label: "薬写真1（ファイル名）" },
        { type: "text", key: "med_photo_2", label: "薬写真2（ファイル名）" },
        { type: "text", key: "med_photo_3", label: "薬写真3（ファイル名）" },
        { type: "text", key: "med_photo_1_url", label: "薬写真1（URL）" },
        { type: "text", key: "med_photo_2_url", label: "薬写真2（URL）" },
        { type: "text", key: "med_photo_3_url", label: "薬写真3（URL）" },
        {
          type: "table",
          key: "medicine_categories",
          label: "薬分類ごとの有無",
          columns: [
            { key: "category", label: "薬の分類", type: "text", readonly: true },
            {
              key: "has_medicine",
              label: "服薬の有無",
              type: "select",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "なし" },
                { value: "1", label: "あり" },
              ],
            },
            {
              key: "image_filename",
              label: "写真ファイル名",
              type: "text",
            },
            {
              key: "image_url",
              label: "写真URL",
              type: "text",
            },
          ],
          defaultRows: medicineRows.map((label) => ({
            category: label,
            has_medicine: "",
            image_filename: "",
            image_url: "",
          })),
        },
        {
          type: "select",
          key: "side_effect",
          label: "1 副作用",
          options: [
            { value: "", label: "選択してください" },
            { value: "なし", label: "なし" },
            { value: "あり", label: "あり" },
          ],
        },
        {
          type: "text",
          key: "side_effect_detail",
          label: "（具体的に記入）",
          visibleIf: { field: "side_effect", equals: "あり" },
        },
        {
          type: "select",
          key: "medicine_usage",
          label: "薬の飲み方",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0：処方通りに自分で管理し使用できる" },
            { value: "0a", label: "0-a：医師からの処方無し" },
            { value: "1", label: "1：自分で管理し使用できない" },
          ],
        },
        {
          type: "multi",
          key: "medicine_detail",
          label: "使用できない場合の内容（複数選択可）",
          visibleIf: { field: "medicine_usage", equals: "1" },
          options: [
            { value: "a", label: "a. 薬の飲み方を自己判断でやめたり、薬をためている、複数受診や売薬が多数ある" },
            { value: "b", label: "b. 薬剤数調整（ポリファーマシー）未調整" },
            { value: "c", label: "c. 不安や抵抗感があるが相談していない" },
            { value: "d", label: "d. 拘縮・変形・嚥下困難で1人では使用困難" },
            { value: "e", label: "e. 一包化したり、飲みにくい薬や塗布薬を、負担にならない様に調整されていない" },
            { value: "f", label: "f. 症状別薬剤の分包調整がされていない" },
            { value: "g", label: "g. 服用忘れ・誤薬がある" },
            { value: "h", label: "h. 売薬の長期連用・過剰摂取が懸念される" },
          ],
        },
      ],
    },
  ],
};

export default page17;
