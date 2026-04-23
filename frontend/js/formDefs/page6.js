// page6: 生活習慣（喫煙含む）とブリンクマン指数関連のJSON定義。
const page6 = {
  id: 6,
  formTitle: "APOS-HC 調査票",
  badge: "No.6",
  fields: [
    {
      type: "group",
      key: "lifestyleHealth",
      label: "1　生活習慣・健康状態",
      fields: [
        {
          type: "select",
          key: "alcoholProblem",
          label: "飲酒による問題",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. なし" },
            { value: "1", label: "1. 過去にトラブル有" },
            { value: "2", label: "2. 現在トラブル有" },
            { value: "3", label: "3. 10年以上の多量飲酒" },
          ],
        },
        {
          type: "multi",
          key: "whoAlcoholCriteria",
          label: "WHO飲酒診断基準（該当する症状）",
          options: [
            { value: "1", label: "１．お酒を飲めない状況でも強い飲酒欲求を感じたことがある" },
            { value: "2", label: "2. 意思に反して予定以上に飲み続けたことがある" },
            { value: "3", label: "３．酒の量を減らしたり、やめた時に手が震える・冷汗をかく・寝汗・不眠・幻覚などの症状が出たことがある" },
            { value: "4", label: "4. 同じ効果に必要な飲酒量が増えた" },
            { value: "5", label: "5. 飲酒のため大切な活動を減らした/やめた" },
            { value: "6", label: "6. 病気の原因と知りつつ飲み続けた" },
          ],
        },
        {
          type: "select",
          key: "whoAlcoholResult",
          label: "WHO判定",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 該当なし" },
            { value: "1", label: "1. 1〜2項目あり（生活指導）" },
            { value: "2", label: "2. 3項目以上あり（治療等の勧め）" },
          ],
        },
        {
          type: "group",
          key: "smoking",
          label: "喫煙習慣",
          fields: [
            {
              type: "select",
              key: "habit",
              label: "喫煙の有無",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり（ブリンクマン指数計算可）" },
              ],
            },
            {
              type: "group",
              key: "brinkman",
              label: "ブリンクマン指数",
              visibleIf: { field: "habit", equals: "1" },
              fields: [
                {
                  type: "text",
                  key: "amount",
                  label: "1日あたり本数",
                  inputType: "number",
                  min: 1,
                  placeholder: "1日あたりの本数",
                },
                {
                  type: "text",
                  key: "years",
                  label: "喫煙年数",
                  inputType: "number",
                  min: 1,
                  placeholder: "喫煙年数",
                },
                {
                  type: "text",
                  key: "index",
                  label: "ブリンクマン指数",
                  inputType: "number",
                  readonly: true,
                },
                {
                  type: "text",
                  key: "judgement",
                  label: "判定",
                  readonly: true,
                },
              ],
            },
            {
              type: "textarea",
              key: "familyImpact",
              label: "家族への影響/注意している事",
              rows: 2,
              placeholder: "家族への影響や注意していることがあればご記入ください",
            },
          ],
        },
        {
          type: "select",
          key: "sleepQuality",
          label: "睡眠と休息",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 適切に日中/夜間の睡眠をとっており休息感がある" },
            { value: "1", label: "1. 睡眠はとれているが休息感がない" },
            { value: "2", label: "2. 睡眠がとれず休息感がない" },
            { value: "3", label: "3. 睡眠パターンがなく休息感がない" },
          ],
        },
        {
          type: "group",
          key: "fatigue",
          label: "疲労感",
          fields: [
            {
              type: "select",
              key: "exists",
              label: "疲労感の有無",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり（身体や精神的に）" },
              ],
            },
            {
              type: "select",
              key: "detail",
              label: "疲労感の詳細",
              visibleIf: { field: "exists", equals: "1" },
              options: [
                { value: "", label: "該当するものを選択" },
                { value: "だるい", label: "1. だるい" },
                { value: "疲れやすい", label: "2. 疲れやすい" },
                { value: "疲れが残ってる", label: "3. 疲れが残ってる" },
                { value: "慢性的に疲れている", label: "4. 慢性的に疲れている" },
              ],
            },
          ],
        },
        {
          type: "group",
          key: "allergy",
          label: "アレルギー",
          fields: [
            {
              type: "select",
              key: "exists",
              label: "アレルギーの有無",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり" },
              ],
            },
            {
              type: "multi",
              key: "details",
              label: "アレルギー詳細",
              visibleIf: { field: "exists", equals: "1" },
              options: [
                { value: "食物", label: "1. 食物" },
                { value: "薬", label: "2. 薬" },
                { value: "植物花粉", label: "3. 植物/花粉" },
                { value: "金属", label: "4. 金属" },
                { value: "ハウスダスト", label: "5. ハウスダスト" },
                { value: "衣類", label: "6. 衣類" },
                { value: "その他", label: "7. その他" },
              ],
            },
            {
              type: "text",
              key: "otherText",
              label: "アレルギー（その他）",
              placeholder: "その他の場合はご記入ください",
              visibleIf: { field: "exists", equals: "1" },
            },
          ],
        },
        {
          type: "group",
          key: "physicalActivity",
          label: "身体活動・運動",
          fields: [
            {
              type: "select",
              key: "status",
              label: "身体活動・運動の状況",
              options: [
                { value: "", label: "選択してください" },
                {
                  value: "0",
                  label: "0．動くようにしている・手足を動かしている・散歩する・TV体操・関節運動などをしている",
                },
                {
                  value: "1",
                  label: "1. ねたきり・動きたくない・運動習慣がない",
                },
              ],
            },
            {
              type: "text",
              key: "detail",
              label: "身体活動の内容",
              placeholder: "内容を記入してください",
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "infectionPrevention",
      label: "2　感染症の予防",
      fields: [
        {
          type: "group",
          key: "diseaseWithinYear",
          label: "1年以内のり患",
          fields: [
            {
              type: "radio",
              key: "exists",
              label: "1年以内のり患有無",
              options: [
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり" },
              ],
            },
            {
              type: "group",
              key: "detail",
              label: "り患した感染症（複数選択可）",
              visibleIf: { field: "exists", equals: "1" },
              fields: [
                {
                  type: "multi",
                  key: "types",
                  label: "感染症の種類",
                  options: [
                    { value: "a.肺炎", label: "a. 肺炎" },
                    { value: "b.鼻咽炎", label: "b. 真菌症（水虫・たむし・カンジダ・毛包炎など）" },
                    { value: "c.インフルエンザ", label: "c. インフルエンザ" },
                    { value: "d.新型コロナ", label: "d. 新型コロナ（COVID-19）" },
                    { value: "e.エイズ", label: "e. エイズ" },
                    { value: "f.ウイルス性肝炎", label: "f. ウイルス性肝炎" },
                    { value: "g.動物（ヒトやペンダー）に咬まれた", label: "g. 疥癬（ヒゼンダニ）" },
                    { value: "h.虫刺咬", label: "h. 食中毒" },
                    { value: "i.蜂毒", label: "i. 結核" },
                    { value: "j.その他", label: "j. その他" },
                  ],
                },
                {
                  type: "text",
                  key: "otherText",
                  label: "感染症（その他）",
                  placeholder: "その他の場合はご記入ください",
                },
              ],
            },
          ],
        },
        {
          type: "group",
          key: "vaccination",
          label: "予防接種",
          fields: [
            {
              type: "radio",
              key: "status",
              label: "接種状況",
              options: [
                { value: "0", label: "0. 接種あり" },
                { value: "1", label: "1. すべて未接種" },
              ],
            },
            {
              type: "group",
              key: "received",
              label: "接種済みワクチン",
              visibleIf: { field: "status", equals: "0" },
              fields: [
                {
                  type: "multi",
                  key: "vaccines",
                  label: "接種したもの（複数選択可）",
                  options: [
                    { value: "a.肺炎球菌", label: "a. 肺炎球菌" },
                    { value: "b.インフルエンザ", label: "b. インフルエンザ" },
                    { value: "c.新型コロナ", label: "c. 新型コロナ" },
                    { value: "d.三種混合", label: "d. 三種混合" },
                    { value: "e.帯状疱疹ワクチン", label: "e. 帯状疱疹ワクチン" },
                    { value: "f.B型肝炎ワクチン", label: "f. B型肝炎ワクチン" },
                    { value: "h.その他", label: "h. その他" },
                  ],
                },
                {
                  type: "text",
                  key: "otherText",
                  label: "ワクチン（その他）",
                },
              ],
            },
            {
              type: "textarea",
              key: "noneReason",
              label: "未接種の理由",
              rows: 2,
              placeholder: "理由を記入",
              visibleIf: { field: "status", equals: "1" },
            },
          ],
        },
        {
          type: "select",
          key: "infectionControl",
          label: "感染対策",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 感染症を理解し予防と適切な治療・感染管理を心がけている" },
            { value: "1", label: "1. やや理解し予防行動を取り治療を受けている" },
            { value: "2", label: "2. 自身の対策理解はあるが他者への感染予防は不十分" },
            { value: "3", label: "3. 指導は受けるが自ら治療や予防管理はしない" },
            { value: "4", label: "4. 治療計画や感染ガイドラインに従うことを拒否/困難" },
          ],
        },
      ],
    },
  ],
};

export default page6;
