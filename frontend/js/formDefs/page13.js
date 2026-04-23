// page13: 疼痛・皮膚状態関連のJSON定義。
const page13 = {
  id: 13,
  formTitle: "APOS-HC 調査票",
  badge: "No.13",
  fields: [
    {
      type: "group",
      key: "gaf",
      label: "Ⅰ　メンタルの状態",
      fields: [
        {
          type: "text",
          key: "gaf_score",
          label: "1. GAF（全体的評定）",
          inputType: "number",
          min: 1,
          max: 100,
        },
        {
          type: "textarea",
          key: "gaf_note",
          label: "GAF評価に関するメモ・補足",
          rows: 4,
          placeholder: "GAF評価に関して補足や特記事項があればご記入ください",
        },
      ],
    },
  ],
};

export default page13;
