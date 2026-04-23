// page2: 生活背景・利用状況関連のJSON定義。
const page2 = {
  id: 2,
  formTitle: "APOS-HC 調査票",
  badge: "No.2",
  fields: [
    {
      type: "group",
      key: "lifeAndEducation",
      label: "3 これまでの生活歴や教育歴",
      fields: [
        {
          type: "group",
          label: "これまでの生活歴",
          fields: [
            {
              type: "textarea",
              key: "lifeHistory",
              label: "これまでの生活歴についてご記入ください",
              rows: 4,
              readonly: true,
            },
          ],
        },
        {
          type: "group",
          label: "教育歴",
          fields: [
            {
              type: "textarea",
              key: "educationHistory",
              label: "教育歴についてご記入ください",
              rows: 3,
              readonly: true,
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "dailyRhythm",
      label: "4 ご利用者さまの1日の生活のしかた/リズム",
      fields: [
        {
          type: "group",
          label: "1日の生活リズム",
          fields: [
            {
              type: "textarea",
              key: "activityDaily",
              label: "1日の生活・訪問日前・３日間での活動を記入",
              rows: 6,
              placeholder:
                "例：起床〜就寝までの流れ、食事・入浴・外出・就寝時刻などを自由にご記入ください",
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "publicAndEconomic",
      label: "5 公費制度利用・経済的状況",
      fields: [
        {
          type: "group",
          key: "expensiveCost",
          label: "高額費用の利用",
          fields: [
            {
              type: "select",
              key: "usage",
              label: "高額費用の利用",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. 必要なし" },
                { value: "1a", label: "1a. 必要で利用あり（介護制度）" },
                { value: "1b", label: "1b. 必要で利用あり（医療制度）" },
                { value: "2a", label: "2a. 必要で利用無し（介護制度）" },
                { value: "2b", label: "2b. 必要で利用無し（医療制度）" },
              ],
            },
            {
              type: "text",
              key: "noReason",
              label: "利用しない理由",
              visibleIf: {
                any: [
                  { field: "usage", equals: "2a" },
                  { field: "usage", equals: "2b" },
                ],
              },
            },
          ],
        },
        {
          type: "group",
          key: "publicMedical",
          label: "公費医療の利用",
          fields: [
            {
              type: "select",
              key: "usage",
              label: "公費医療の利用",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. 必要で利用あり" },
                { value: "2", label: "2. 必要で利用無し" },
              ],
            },
            {
              type: "text",
              key: "reason",
              label: "理由",
              visibleIf: { field: "usage", equals: "2" },
            },
            {
              type: "group",
              key: "detail",
              label: "利用あり詳細",
              visibleIf: { field: "usage", equals: "1" },
              fields: [
                {
                  type: "multi",
                  key: "category1",
                  label: "① 公費負担医療",
                  options: [
                    { value: "a", label: "a. 結核医療" },
                    { value: "b", label: "b. 感染症医療費" },
                    { value: "c", label: "c. 肝炎 / HIV / エイズ医療費" },
                    { value: "d", label: "d. その他" },
                  ],
                },
                {
                  type: "text",
                  key: "category1OtherReason",
                  label: "① その他理由",
                },
                {
                  type: "multi",
                  key: "category2",
                  label: "② 自立支援",
                  options: [
                    { value: "flag", label: "② 自立支援" },
                    { value: "a", label: "a. 更生医療" },
                    { value: "b", label: "b. 精神通院医療" },
                    { value: "c", label: "c. その他" },
                  ],
                },
                {
                  type: "text",
                  key: "category2OtherReason",
                  label: "② その他理由",
                },
                {
                  type: "multi",
                  key: "category3to5",
                  label: "③〜⑤",
                  options: [
                    { value: "3", label: "③ 特定疾患" },
                    { value: "4", label: "④ 原子爆弾被爆者援護" },
                    { value: "5", label: "⑤ 指定難病" },
                  ],
                },
                {
                  type: "text",
                  key: "diseaseName",
                  label: "⑤ 指定難病 病名",
                },
              ],
            },
          ],
        },
        {
          type: "group",
          key: "publicSystem",
          label: "3. 公費制度の利用",
          fields: [
            {
              type: "select",
              key: "usage",
              label: "公費制度の利用",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. 必要で利用あり" },
                { value: "2", label: "2. 必要で利用無し" },
              ],
            },
            {
              type: "group",
              key: "detail",
              label: "利用あり詳細",
              visibleIf: { field: "usage", equals: "1" },
              fields: [
                {
                  type: "group",
                  key: "disabilityNotebook",
                  label: "① 身障手帳",
                  fields: [
                    { type: "select", key: "enabled", label: "利用", options: [{ value: "", label: "未選択" }, { value: "1", label: "あり" }] },
                    { type: "text", key: "shu", label: "種" },
                    { type: "text", key: "kyu", label: "級" },
                  ],
                },
                {
                  type: "group",
                  key: "rehabilitationNotebook",
                  label: "② 療育手帳",
                  fields: [
                    { type: "select", key: "enabled", label: "利用", options: [{ value: "", label: "未選択" }, { value: "1", label: "あり" }] },
                    { type: "text", key: "degree", label: "程度" },
                  ],
                },
                {
                  type: "group",
                  key: "mentalHealthNotebook",
                  label: "③ 精神障害者保健福祉手帳",
                  fields: [
                    { type: "select", key: "enabled", label: "利用", options: [{ value: "", label: "未選択" }, { value: "1", label: "あり" }] },
                    { type: "text", key: "kyu", label: "級" },
                  ],
                },
                {
                  type: "multi",
                  key: "others",
                  label: "④〜⑥",
                  options: [
                    { value: "4", label: "④ 障害者福祉サービス受給者証" },
                    { value: "5", label: "⑤ 生活保護" },
                    { value: "6", label: "⑥ 障害者年金" },
                  ],
                },
              ],
            },
            {
              type: "text",
              key: "noUseReason",
              label: "必要で利用無しの理由",
              placeholder: "理由を入力してください",
              visibleIf: { field: "usage", equals: "2" },
            },
          ],
        },
        {
          type: "group",
          key: "economicStatus",
          label: "4. 経済的状況",
          fields: [
            {
              type: "select",
              key: "householdDifficulty",
              label: "1. この1年で家計に困ったことは？",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. 年1回" },
                { value: "2", label: "2. 年2〜3回" },
                { value: "3", label: "3. 年4〜5回" },
                { value: "4", label: "4. 年6回以上" },
              ],
            },
            {
              type: "select",
              key: "beforePaydayDifficulty",
              label: "2. 給与日前に困ったことは？",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. 年1回" },
                { value: "2", label: "2. 年2〜3回" },
                { value: "3", label: "3. 年4〜5回" },
                { value: "4", label: "4. 年6回以上" },
              ],
            },
            {
              type: "multi",
              key: "hardshipItems",
              label: "3. 苦しい家計（複数選択可）",
              options: [
                { value: "food", label: "食料" },
                { value: "medical", label: "医療" },
                { value: "care", label: "介護" },
                { value: "transport", label: "交通･電話" },
                { value: "housing", label: "住宅" },
                { value: "utilities", label: "光熱水" },
                { value: "leisure", label: "教養娯楽" },
                { value: "other_flag", label: "その他" },
              ],
            },
            {
              type: "text",
              key: "hardshipOtherText",
              label: "その他の内容",
            },
          ],
        },
      ],
    },
  ],
};

export default page2;
