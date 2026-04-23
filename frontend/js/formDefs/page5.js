// page5: サポート体制・関係者情報のJSON定義。
const page5 = {
  id: 5,
  formTitle: "APOS-HC 調査票",
  badge: "No.5",
  fields: [
    {
      type: "group",
      key: "socialParticipation",
      label: "Ⅰ　社会参加/日常の楽しみ",
      fields: [
        {
          type: "select",
          key: "motivation",
          label: "社会参加意欲（社会的孤立予防）",
          options: [
            { value: "", label: "選択してください" },
            {
              value:
                "週に3回以上は外出し家族や友人・支援・ネットワークなどと継続に連絡が取れている（デイケア・デイサービス、買物、近隣や親戚や知人等の付き合い、通勤、散歩、行楽、電話、ネット、手紙を含む）",
              label:
                "0 週に3回以上は外出し家族や友人・支援・ネットワークなどと頻繁に連絡が取れている（病院・デイケア・デイサービス、スーパー、近隣や親戚や知人等の付合い、運動、散歩、行楽、電話、ネット、手紙など含む）",
            },
            {
              value: "週に1〜2回は外出したり、家族や知人と連絡を取り社会参加している",
              label: "1 週に1回は外出したり、家族や知人と連絡を取り社会参加している",
            },
            {
              value: "月に数回外出するがそれ以外の時は1人でいる、家族や知人に会うのは月に何回かである。月に1〜2回",
              label: "2 月に1-2回外出するがそれ以外の時は1人でいる",
            },
            {
              value: "親戚や近隣・社会交流・社会的接触を全くしていない、デイケア等にも行っていない、昨年より外出が減った",
              label: "3 親戚や近隣・社会交流・社会的接触を全くしていない",
            },
          ],
        },
        {
          type: "group",
          key: "enjoyment",
          label: "楽しみ/社会活動",
          fields: [
            {
              type: "select",
              key: "community",
              label: "近所・知り合い・同窓会・訓練会などに出かけ楽しみたい",
              options: [
                { value: "", label: "選択してください" },
                { value: "なし", label: "なし" },
                { value: "あり", label: "あり" },
              ],
            },
            {
              type: "textarea",
              key: "communityNote",
              label: "どのようなことならやってみたいか（近所・知り合い等）",
              rows: 4,
              placeholder: "どのようなことならやってみたいですか：手引を参考にしてください",
              visibleIf: { field: "community", equals: "なし" },
            },
            {
              type: "select",
              key: "individual",
              label: "個人で楽しみたい",
              options: [
                { value: "", label: "選択してください" },
                { value: "なし", label: "なし" },
                { value: "あり", label: "あり" },
              ],
            },
            {
              type: "textarea",
              key: "individualNote",
              label: "どのようなことならやってみたいか（個人）",
              rows: 4,
              placeholder: "どのようなことならやってみたいですか：手引を参考にしてください",
              visibleIf: { field: "individual", equals: "なし" },
            },
            {
              type: "select",
              key: "family",
              label: "家族で楽しみたい",
              options: [
                { value: "", label: "選択してください" },
                { value: "なし", label: "なし" },
                { value: "あり", label: "あり" },
              ],
            },
            {
              type: "textarea",
              key: "familyNote",
              label: "どのようなことならやってみたいか（家族）",
              rows: 4,
              placeholder: "どのようなことならやってみたいですか：手引を参考にしてください",
              visibleIf: { field: "family", equals: "なし" },
            },
          ],
        },
        {
          type: "textarea",
          key: "reason",
          label: "楽しみやコミュニケーションを取りたくない理由",
          rows: 4,
          placeholder: "自由入力（例：体調・交通手段・人間関係など）",
        },
      ],
    },
    {
      type: "group",
      key: "relationshipConsultation",
      label: "Ⅱ　対人関係・困りごとの相談者",
      fields: [
        {
          type: "select",
          key: "relationshipStatus",
          label: "1. 対人関係①",
          options: [
            { value: "", label: "選択してください" },
            { value: "1", label: "0.家族（身内）や友人、介護サービス関係者・近隣等の人と良好な関係" },
            { value: "2", label: "1. 家族または友人とは良好な関係" },
            { value: "3", label: "2. 関係を築くことを望んでいるができない" },
            { value: "4", label: "3. 関係を築くことを望んでいない" },
          ],
        },
        {
          type: "select",
          key: "consultationStatus",
          label: "2. 日常生活での相談②",
          options: [
            { value: "", label: "選択してください" },
            { value: "1", label: "0. 日常助けを求める相手・相談者がいる、特にいらない状況である" },
            { value: "2", label: "1. 相手・支援者がいないので日常生活に支障があり、支援者がいると助かる" },
          ],
        },
        {
          type: "group",
          key: "supporters",
          label: "支援をしてくれる人（複数選択可）",
          visibleIf: { field: "consultationStatus", equals: "2" },
          fields: [
            {
              type: "multi",
              key: "supporterList",
              label: "支援者",
              options: [
                { value: "家族（身内・親族）", label: "a. 家族（身内・親族）" },
                { value: "友人の支援者", label: "b. 友人の支援者" },
                { value: "民生委員", label: "c. 民生委員" },
                {
                  value: "地域包括支援センターや地域活動支援センター",
                  label: "d. 地域包括支援センターや地域活動支援センター",
                },
                { value: "介護保険サービスの担当者", label: "e. 介護保険サービスの担当者" },
                { value: "住民の役員・近隣者", label: "f. 住民の役員・近隣者" },
                { value: "ボランティア", label: "g. ボランティア" },
                { value: "成年後見人", label: "h. 成年後見人" },
                { value: "宅配業者", label: "i. 宅配業者" },
                { value: "郵便局・消防署・農協", label: "j. 郵便局・消防署・農協" },
                { value: "信仰関係者", label: "k. 信仰関係者" },
                { value: "その他", label: "l. その他" },
              ],
            },
            {
              type: "text",
              key: "supporterOther",
              label: "その他（自由記入）",
              placeholder: "その他の場合はご記入ください",
              visibleIf: { field: "supporterList", includes: "その他" },
            },
          ],
        },
      ],
    },
  ],
};

export default page5;
