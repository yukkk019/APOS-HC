// page11: 排泄・清潔など日常ケア領域のJSON定義。
const page11 = {
  id: 11,
  formTitle: "APOS-HC 調査票",
  badge: "No.11",
  fields: [
    {
      type: "group",
      key: "cognitiveStatus",
      label: "Ⅰ　認知の状態",
      fields: [
        {
          type: "select",
          key: "independenceRank",
          label: "認知症高齢者の日常生活自立度",
          options: [
            { value: "", label: "上記から選択してください" },
            { value: "nutrition_self_management_a", label: "0 自立" },
            { value: "nutrition_self_management_b", label: "Ⅰ" },
            { value: "nutrition_self_management_c", label: "Ⅱa" },
            { value: "nutrition_self_management_d", label: "Ⅱb" },
            { value: "nutrition_self_management_e", label: "Ⅲa" },
            { value: "nutrition_self_management_f", label: "Ⅲb" },
            { value: "nutrition_self_management_g", label: "Ⅳ" },
            { value: "nutrition_self_management_h", label: "M" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "healthLiteracy",
      label: "Ⅱ　病気のとらえ方：ヘルスリテラシー",
      fields: [
        {
          type: "select",
          key: "emotionLevel",
          label: "病気のとらえ方",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 自分の病気や治療を良く理解して自発的に行動している" },
            { value: "1", label: "1. 自分の病気や治療に解らないことがあれば医師や看護師にたずねることができる" },
            { value: "2", label: "2. 自分の病名や治療に疑問を感じているが　医師や看護師にたずねないまま治療している" },
            { value: "3", label: "3. 自分の疾患や治療に対して理解が乏しく、医師に確認しないまま治療を中断している" },
            { value: "4", label: "4. 治療が本人に効果ないと拒否している/あきらめ治療を受け入れていない/不満を表している" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "depressiveState",
      label: "Ⅲ　うつ的状態",
      fields: [
        {
          type: "radio",
          key: "q1",
          label: "A.1 毎日の生活に充実感がありますか",
          options: [
            { value: "m_health_1_1", label: "はい" },
            { value: "m_health_1_2", label: "いいえ" },
          ],
        },
        {
          type: "radio",
          key: "q2",
          label: "A.2 これまで楽しんでいたことが今も楽しめますか",
          options: [
            { value: "m_health_2_1", label: "はい" },
            { value: "m_health_2_2", label: "いいえ" },
          ],
        },
        {
          type: "radio",
          key: "q3",
          label: "A.3 以前楽にできたことが今はおっくうに感じられますか",
          options: [
            { value: "m_health_3_1", label: "はい" },
            { value: "m_health_3_2", label: "いいえ" },
          ],
        },
        {
          type: "radio",
          key: "q4",
          label: "A.4 自分が役に立つと考えられますか",
          options: [
            { value: "m_health_4_1", label: "はい" },
            { value: "m_health_4_2", label: "いいえ" },
          ],
        },
        {
          type: "radio",
          key: "q5",
          label: "A.5 わけもなく疲れたような感じがしますか",
          options: [
            { value: "m_health_5_1", label: "はい" },
            { value: "m_health_5_2", label: "いいえ" },
          ],
        },
        {
          type: "text",
          key: "aPositiveCount",
          label: "A項目陰性回答数",
          inputType: "number",
        },
        {
          type: "select",
          key: "q6",
          label: "B.6 「死（自殺に結びつくような死）」について何度も考えることがありますか",
          visibleIf: { field: "aPositiveCount", equals: "2" },
          options: [
            { value: "", label: "選択してください" },
            { value: "m_health_6_1", label: "はい" },
            { value: "m_health_6_2", label: "いいえ" },
          ],
        },
        {
          type: "select",
          key: "q7",
          label: "B.7 気分がひどく落ち込んで、自殺について考えることがありますか",
          visibleIf: { field: "aPositiveCount", equals: "2" },
          options: [
            { value: "", label: "選択してください" },
            { value: "m_health_7_1", label: "はい" },
            { value: "m_health_7_2", label: "いいえ" },
          ],
        },
        {
          type: "select",
          key: "q8",
          label: "C.8 最近ひどく困ったことやつらいと思ったことがありますか",
          options: [
            { value: "", label: "選択してください" },
            { value: "m_health_8_1", label: "はい" },
            { value: "m_health_8_2", label: "いいえ" },
          ],
        },
        {
          type: "textarea",
          key: "q8Detail",
          label: "C.8 詳細",
          rows: 5,
          placeholder: "どういうことがあったのか、お話しいただけますか",
          visibleIf: { field: "q8", equals: "m_health_8_1" },
        },
      ],
    },
  ],
};

export default page11;
