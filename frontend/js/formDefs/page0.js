// page0: 表紙（基本属性・受付情報・面談情報など）のJSON定義。
const page0 = {
  id: 0,
  formTitle: "APOS-HC 調査票",
  badge: "表紙",
  fields: [
    {
      type: "group",
      key: "userInfo",
      label: "利用者情報",
      fields: [
        {
          type: "group",
          key: "name",
          label: "氏名・ふりがな",
          fields: [
            { type: "text", key: "lastName", label: "姓", readonly: true },
            { type: "text", key: "firstName", label: "名", readonly: true },
            { type: "text", key: "lastNameKana", label: "せい", readonly: true },
            { type: "text", key: "firstNameKana", label: "めい", readonly: true },
          ],
        },
        {
          type: "date_triplet",
          key: "birthDate",
          label: "生年月日（西暦）",
        },
        {
          type: "text",
          key: "age",
          label: "年齢",
          inputType: "number",
          min: 0,
          max: 120,
        },
        {
          type: "select",
          key: "sex",
          label: "性別",
          options: [
            { value: "", label: "選択" },
            { value: "男", label: "男性" },
            { value: "女", label: "女性" },
            { value: "指定なし", label: "指定なし" },
            { value: "NA", label: "NA" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "requestInfo",
      label: "依頼情報",
      fields: [
        {
          type: "select",
          key: "requestRoute",
          label: "依頼者",
          options: [
            { value: "", label: "選択" },
            { value: "CM", label: "1.CM" },
            { value: "MSW", label: "2.MSW" },
            { value: "病院医師", label: "3.病院医師" },
            { value: "病院NS", label: "4.病院NS" },
            { value: "開業医師", label: "5.開業医師" },
            { value: "福祉職員", label: "6.福祉職員" },
            { value: "保健所・保健センター職員", label: "7.保健所・保健センター職員" },
            { value: "家族", label: "8.家族" },
            { value: "その他", label: "9.その他" },
          ],
        },
        { type: "text", key: "organization", label: "依頼機関名", readonly: true },
        { type: "text", key: "requestorName", label: "依頼者名（担当者）", readonly: true },
        { type: "text", key: "requestorTel", label: "依頼者電話番号", readonly: true },
        { type: "text", key: "requestorFax", label: "依頼者Fax", readonly: true },
        { type: "text", key: "requestorEmail", label: "依頼者mail", inputType: "email", readonly: true },
      ],
    },
    {
      type: "group",
      key: "receptionInfo",
      label: "受付情報",
      fields: [
        { type: "date_triplet", key: "receptionDate", label: "受付日" },
        {
          type: "group",
          key: "receptionTime",
          label: "受付時刻",
          fields: [
            { type: "text", key: "hour", label: "時", inputType: "number", min: 0, max: 23 },
            { type: "text", key: "minute", label: "分", inputType: "number", min: 0, max: 59 },
          ],
        },
        {
          type: "select",
          key: "method",
          label: "受付方法",
          options: [
            { value: "", label: "選択" },
            { value: "書面", label: "書面" },
            { value: "Fax", label: "Fax" },
            { value: "面会", label: "面会" },
            { value: "mail", label: "mail" },
            { value: "電話", label: "電話" },
            { value: "その他", label: "その他" },
          ],
        },
        { type: "text", key: "staff", label: "対応者", readonly: true },
        {
          type: "textarea",
          key: "reason",
          label: "依頼理由",
          rows: 3,
          placeholder: "依頼・相談の理由や内容を記入してください",
        },
      ],
    },
    {
      type: "group",
      key: "assessment",
      label: "アセスメント理由/年月日",
      fields: [
        {
          type: "table",
          key: "events",
          label: "アセスメント履歴",
          columns: [
            { key: "reason", label: "理由", type: "text", readonly: true },
            { key: "date", label: "年月日", type: "date_triplet" },
          ],
          defaultRows: [
            { reason: "初回", date: "" },
            { reason: "定期継続評価", date: "" },
            { reason: "状態悪化", date: "" },
            { reason: "退院", date: "" },
            { reason: "入院", date: "" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "interview",
      label: "面談情報",
      fields: [
        {
          type: "multi",
          key: "participants",
          label: "参加者",
          options: [
            { value: "1", label: "1.本人" },
            { value: "2", label: "2.息子" },
            { value: "3", label: "3.娘" },
            { value: "4", label: "4.妻/夫・パートナー" },
            { value: "5", label: "5.父母（義理含む）" },
            { value: "6", label: "6.CM" },
            { value: "7", label: "7.MSW" },
            { value: "8", label: "8.医師" },
            { value: "9", label: "9.医療・施設Ns" },
            { value: "10", label: "10.その他" },
          ],
        },
        {
          type: "select",
          key: "location",
          label: "面談場所",
          readonly: true,
          options: [
            { value: "", label: "選択してください" },
            { value: "1", label: "1.自宅" },
            { value: "2", label: "2.入院施設内" },
            { value: "3", label: "3.その他" },
          ],
        },
        {
          type: "text",
          key: "locationOther",
          label: "面談場所（その他）",
          placeholder: "その他の場合はご記入ください",
          readonly: true,
        },
        {
          type: "group",
          key: "response24h",
          label: "24時間対応",
          fields: [
            {
              type: "select",
              key: "cm",
              label: "CM",
              options: [
                { value: "", label: "選択" },
                { value: "0", label: "0.要望なし" },
                { value: "1", label: "1.要望あり" },
              ],
            },
            {
              type: "select",
              key: "care",
              label: "介護",
              options: [
                { value: "", label: "選択" },
                { value: "0", label: "0.要望なし" },
                { value: "1", label: "1.要望あり" },
              ],
            },
            {
              type: "select",
              key: "nurse",
              label: "看護",
              options: [
                { value: "", label: "選択" },
                { value: "0", label: "0.要望なし" },
                { value: "1", label: "1.要望あり" },
              ],
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "closing",
      label: "終了情報",
      fields: [
        { type: "date_triplet", key: "endDate", label: "終了年月日" },
        {
          type: "text",
          key: "summaryRecorder",
          label: "サマリー記録者",
          placeholder: "記録者名を入力",
        },
        {
          type: "textarea",
          key: "exitSummary",
          label: "終了時サマリー",
          rows: 4,
          placeholder: "調査期間中に訪問が終了になった時のみ、終了理由を入力ください",
        },
      ],
    },
  ],
};

export default page0;
