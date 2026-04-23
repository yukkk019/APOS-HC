const yesNoOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. なし" },
  { value: "1", label: "1. あり" },
];

const riskDetailOptions = [
  { value: "a", label: "a. 過去にあり" },
  { value: "b", label: "b. 現在兆候あり" },
  { value: "c", label: "c. 緊急対応状態" },
];

// page19: 最終確認・不安要因・内部判定関連のJSON定義。
const page19 = {
  id: 19,
  formTitle: "APOS-HC 調査票",
  badge: "No.19",
  fields: [
    {
      type: "group",
      key: "riskManagement",
      label: "ⅩⅢ. リスク管理",
      fields: [
        {
          type: "group",
          key: "fallRisk",
          label: "① 転倒・転落",
          fields: [
            { type: "select", key: "fall", label: "転倒・転落", options: yesNoOptions },
            {
              type: "text",
              key: "fall_count",
              label: "回数（過去1年間）",
              inputType: "number",
              visibleIf: { field: "fall", equals: "1" },
            },
            {
              type: "text",
              key: "fall_detail",
              label: "転倒日とその理由、場所",
              visibleIf: { field: "fall", equals: "1" },
            },
            {
              type: "select",
              key: "fall_anxiety",
              label: "転倒の不安",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり" },
                { value: "2", label: "2. 不安ありで閉じこもっている" },
              ],
            },
            {
              type: "multi",
              key: "anxiety_reason",
              label: "転倒不安の要因（複数選択可）",
              visibleIf: {
                any: [
                  { field: "fall_anxiety", equals: "1" },
                  { field: "fall_anxiety", equals: "2" },
                ],
              },
              options: [
                { value: "aging_muscle", label: "内的要因: 加齢による機能低下" },
                { value: "disease", label: "内的要因: 疾患の影響" },
                { value: "medicine", label: "内的要因: 薬物（眠剤・向精神薬）" },
                { value: "internal_other", label: "内的要因: その他" },
                { value: "environment_external", label: "外的要因: 段差・床・照明等" },
              ],
            },
            {
              type: "text",
              key: "internal_other_text",
              label: "内的要因: その他（具体）",
              visibleIf: {
                all: [
                  {
                    any: [
                      { field: "fall_anxiety", equals: "1" },
                      { field: "fall_anxiety", equals: "2" },
                    ],
                  },
                  { field: "anxiety_reason", includes: "internal_other" },
                ],
              },
            },
          ],
        },
        {
          type: "group",
          key: "fractureRisk",
          label: "骨折・その可能性",
          fields: [
            { type: "select", key: "fracture", label: "骨折・その可能性", options: yesNoOptions },
            {
              type: "radio",
              key: "fracture_cause",
              label: "骨折要因",
              visibleIf: { field: "fracture", equals: "1" },
              options: [
                { value: "fall", label: "① 転倒による" },
                { value: "other", label: "② 非転倒性" },
              ],
            },
            {
              type: "select",
              key: "fracture_count_check",
              label: "a. 40歳以降の過去の骨折回数の確認",
              visibleIf: { field: "fracture", equals: "1" },
              options: [
                { value: "", label: "選択してください" },
                { value: "1", label: "確認する" },
              ],
            },
            {
              type: "text",
              key: "fracture_count",
              label: "骨折回数",
              inputType: "number",
              visibleIf: { field: "fracture", equals: "1" },
            },
            {
              type: "text",
              key: "fracture_location",
              label: "骨折部位",
              visibleIf: { field: "fracture", equals: "1" },
            },
            {
              type: "select",
              key: "height_decrease_check",
              label: "b. 身長低下の確認",
              visibleIf: { field: "fracture", equals: "1" },
              options: [
                { value: "", label: "選択してください" },
                { value: "1", label: "確認する" },
              ],
            },
            {
              type: "text",
              key: "height_decrease",
              label: "身長低下（cm）",
              inputType: "number",
              visibleIf: { field: "fracture", equals: "1" },
            },
            {
              type: "multi",
              key: "fracture_related_signs",
              label: "骨折関連所見（複数選択可）",
              visibleIf: { field: "fracture", equals: "1" },
              options: [
                { value: "back_curved", label: "c. 背中や腰が曲がってきた" },
                { value: "back_pain", label: "d. 背中や腰に痛みを感じる" },
              ],
            },
          ],
        },
        {
          type: "group",
          key: "drugAbuse",
          label: "薬物乱用/向精神薬過剰服用",
          fields: [
            { type: "select", key: "drug_abuse", label: "有無", options: yesNoOptions },
            {
              type: "radio",
              key: "drug_abuse_type",
              label: "詳細",
              visibleIf: { field: "drug_abuse", equals: "1" },
              options: riskDetailOptions,
            },
          ],
        },
        {
          type: "group",
          key: "temperatureSkinRisk",
          label: "体温調節機能（温度）・皮膚感覚の低下",
          fields: [
            {
              type: "select",
              key: "choking_risk",
              label: "有無",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり（低体温・高体温の傾向がある）" },
              ],
            },
            {
              type: "radio",
              key: "choking_detail_type",
              label: "詳細",
              visibleIf: { field: "choking_risk", equals: "1" },
              options: riskDetailOptions,
            },
          ],
        },
        {
          type: "group",
          key: "abuseOverall",
          label: "虐待総合評価",
          fields: [
            {
              type: "select",
              key: "abuse_evaluation",
              label: "虐待総合評価",
              options: yesNoOptions,
            },
            {
              type: "radio",
              key: "abuse_detail_type",
              label: "虐待リスクレベル",
              visibleIf: { field: "abuse_evaluation", equals: "1" },
              options: [
                { value: "a", label: "レベル１：すでに重大な結果にあり、差し迫った虐待の状況が見られる" },
                { value: "b", label: "レベル2：重大な結果が生じるおそれが高い" },
                { value: "c", label: "レベル3：虐待につながりやすい要因が見られる" },
              ],
            },
          ],
        },
        {
          type: "select",
          key: "kodokushi_feeling",
          label: "6. 孤立死",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 全く感じない" },
            { value: "1", label: "1. あまり感じない" },
            { value: "2", label: "2. 感じる" },
            { value: "3", label: "3. とても感じる" },
          ],
        },
        {
          type: "group",
          key: "fireWater",
          label: "7. 火や水道の不始末",
          fields: [
            { type: "select", key: "fire_water_negligence", label: "有無", options: yesNoOptions },
            {
              type: "radio",
              key: "fire_water_detail_type",
              label: "詳細",
              visibleIf: { field: "fire_water_negligence", equals: "1" },
              options: riskDetailOptions,
            },
          ],
        },
        {
          type: "select",
          key: "news_risk",
          label: "8. NEWS評価（バイタル評価）",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 低リスク（合計１～４点）" },
            { value: "1", label: "1. 中リスク（合計５～６点・もしくはred scoreが一つでもある場合）" },
            { value: "2", label: "2. 高リスク（合計７点以上・もしくはred scoreが一つでもある場合）" },
          ],
        },
        {
          type: "select",
          key: "dehydration_prevention",
          label: "9. 熱中症・脱水予防",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. なし" },
            { value: "1", label: "1. 食事をきちんととらない ・こまめな補水不足 ・運動・入浴前後の水分不足 ・発熱 ・過度の発汗 ・おう吐・下痢状態が 複数状態認められる" },
          ],
        },
        {
          type: "select",
          key: "abnormal_behavior_severity",
          label: "10. 特異行動の重症度評価：P12「精神症状の状況」の2.総合点の重症度評価により判断する",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. なし（0点）" },
            { value: "1", label: "1. 軽度（1〜5点）" },
            { value: "2", label: "2. 中等度（6〜14点）" },
            { value: "3", label: "3. 重度（15点以上）" },
          ],
        },
      ],
    },
  ],
};

export default page19;
