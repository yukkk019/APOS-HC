// page1: 住宅/保険/家族テーブルなど初期生活情報のJSON定義。
const page1 = {
  id: 1,
  formTitle: "APOS-HC 調査票",
  badge: "No.1",
  fields: [
    {
      type: "group",
      id: "section1_contact_insurance_public",
      label: "1 本人等の連絡先・保険・公費制度",
      fields: [
        {
      type: "group",
      key: "currentAddress",
      label: "1 現住所",
      fields: [
        { type: "text", key: "zipcode", label: "郵便番号", readonly: true },
        { type: "text", key: "address", label: "住所", readonly: true },
        { type: "text", key: "mobile", label: "携帯番号", readonly: true },
        { type: "text", key: "tel", label: "電話番号", readonly: true },
        { type: "text", key: "email", label: "メールアドレス", inputType: "email", readonly: true },
      ],
    },
    {
      type: "group",
      key: "residenceInfo",
      label: "2 本人住宅",
      fields: [
        {
          type: "select",
          key: "housingType",
          label: "住宅種類",
          options: [
            { value: "", label: "選択してください" },
            { value: "自宅", label: "1. 自宅" },
            { value: "アパート", label: "2. アパート" },
            { value: "一般マンション", label: "3. 一般マンション" },
            { value: "高齢者マンション", label: "4. 高齢者マンション" },
            { value: "グループホーム", label: "5. グループホーム" },
            { value: "借間", label: "6. 借間" },
            { value: "福祉施設", label: "7. 福祉施設" },
            { value: "生活訓練施設", label: "8. 生活訓練施設" },
            { value: "入所授産施設", label: "9. 入所授産施設" },
            { value: "その他", label: "10. その他" },
          ],
        },
        {
          type: "text",
          key: "housingTypeOther",
          label: "住宅種類（その他詳細）",
          placeholder: "その他の場合は階数をご記入ください",
          visibleIf: {
            field: "housingType",
            equals: "その他",
          },
        },
      ],
    },
    {
      type: "group",
      key: "emergencyContact",
      label: "3. 緊急連絡者",
      fields: [
        { type: "text", key: "name", label: "氏名", readonly: true },
        { type: "text", key: "relation", label: "続柄", readonly: true },
        { type: "text", key: "email", label: "メールアドレス", inputType: "email", readonly: true },
        { type: "text", key: "mobile", label: "携帯番号", readonly: true },
        { type: "text", key: "tel", label: "電話番号", readonly: true },
      ],
    },
    {
      type: "group",
      key: "mainConsultant",
      label: "4. 本人の主な相談者",
      fields: [
        { type: "text", key: "name", label: "氏名", readonly: true },
        { type: "text", key: "relation", label: "本人との間柄", readonly: true },
        { type: "text", key: "address", label: "住所", readonly: true },
        { type: "text", key: "tel", label: "電話番号", readonly: true },
        { type: "text", key: "mobile", label: "携帯番号", readonly: true },
      ],
    },
    {
      type: "group",
      key: "careInsurance",
      label: "5. 介護保険の給付情報",
      fields: [
        { type: "text", key: "insurerName", label: "保険者名" },
        {
          type: "select",
          key: "userBurdenRatio",
          label: "利用者負担割合",
          options: [
            { value: "", label: "選択してください" },
            { value: "1割", label: "1. 1割" },
            { value: "2割", label: "2. 2割" },
            { value: "3割", label: "3. 3割" },
          ],
        },
        {
          type: "date_triplet",
          key: "certificationDate",
          label: "① 要介護認定日",
        },
        {
          type: "group",
          key: "validPeriod",
          label: "② 有効期間",
          fields: [
            { type: "date_triplet", key: "startDate", label: "開始日" },
            { type: "date_triplet", key: "endDate", label: "終了日" },
          ],
        },
        {
          type: "group",
          key: "careStatus",
          label: "③ 要介護状態区分",
          fields: [
            {
              type: "select",
              key: "support",
              label: "支援",
              options: [
                { value: "", label: "選択してください" },
                { value: "要支援1", label: "要支援1" },
                { value: "要支援2", label: "要支援2" },
              ],
            },
            {
              type: "select",
              key: "nursing",
              label: "介護",
              options: [
                { value: "", label: "選択してください" },
                { value: "要介護1", label: "要介護1" },
                { value: "要介護2", label: "要介護2" },
                { value: "要介護3", label: "要介護3" },
                { value: "要介護4", label: "要介護4" },
                { value: "要介護5", label: "要介護5" },
              ],
            },
          ],
        },
        {
          type: "text",
          key: "benefitLimit",
          label: "④ 支給限度額",
          placeholder: "単位",
          inputType: "number",
        },
        {
          type: "select",
          key: "dementiaLevel",
          label: "⑤ 認知症の自立度",
          options: [
            { value: "", label: "選択してください" },
            { value: "自立", label: "自立" },
            { value: "Ⅰ", label: "Ⅰ" },
            { value: "Ⅱa", label: "Ⅱa" },
            { value: "Ⅱb", label: "Ⅱb" },
            { value: "Ⅲa", label: "Ⅲa" },
            { value: "Ⅲb", label: "Ⅲb" },
            { value: "Ⅳ", label: "Ⅳ" },
            { value: "M", label: "M" },
          ],
        },
        {
          type: "select",
          key: "elderlyIndependenceLevel",
          label: "⑥ 高齢者の自立度",
          options: [
            { value: "", label: "選択してください" },
            { value: "自立", label: "自立" },
            { value: "J1", label: "J1" },
            { value: "J2", label: "J2" },
            { value: "A1", label: "A1" },
            { value: "A2", label: "A2" },
            { value: "B1", label: "B1" },
            { value: "B2", label: "B2" },
            { value: "C1", label: "C1" },
            { value: "C2", label: "C2" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "medicalInsurance",
      label: "6. 医療保険情報",
      fields: [
        { type: "text", key: "insurerName", label: "医療保険者名" },
        {
          type: "radio",
          key: "insuranceType",
          label: "区分",
          options: [
            { value: "本人", label: "本人" },
            { value: "家族", label: "家族" },
          ],
        },
        {
          type: "radio",
          key: "insuranceCategory",
          label: "保険種別",
          options: [
            { value: "国保", label: "①国保" },
            { value: "社保", label: "②社保(健保)" },
            { value: "共済", label: "③共済" },
            { value: "労災", label: "④労災" },
            { value: "後期高齢者医療", label: "⑤後期高齢者医療(75歳以上)" },
            { value: "その他", label: "⑥その他" },
          ],
        },
        {
          type: "select",
          key: "koukiKoureiBurden",
          label: "後期高齢者医療 負担割合",
          options: [
            { value: "", label: "負担割合を選択" },
            { value: "1割", label: "1割負担" },
            { value: "2割", label: "2割負担" },
            { value: "3割", label: "3割負担" },
          ],
          visibleIf: {
            field: "insuranceCategory",
            equals: "後期高齢者医療",
          },
        },
        {
          type: "text",
          key: "insuranceOtherDetail",
          label: "保険種別（その他詳細）",
          placeholder: "その他の詳細を入力",
          visibleIf: {
            field: "insuranceCategory",
            equals: "その他",
          },
        },
        {
          type: "radio",
          key: "myNumberCard",
          label: "マイナンバーカード",
          options: [
            { value: "なし", label: "0.なし" },
            { value: "あり", label: "1.あり" },
          ],
        },
        {
          type: "textarea",
          key: "doctorOpinion",
          label: "審査委員会の意見/主治医の意見",
          rows: 6,
          placeholder: "審査委員会の意見や主治医の意見を記入してください",
          readonly: true,
        },
      ],
    },
      ],
    },
    {
      type: "group",
      id: "section2_family_support",
      label: "2 家族（別居含む）等支援者の状況",
      fields: [
        {
      type: "group",
      id: "familyTableIntro",
      label: "親族（同居、別居含む）がいないものは、独居となる",
      fields: [],
    },
        {
      type: "group",
      key: "familySupport",
      label: "家族（別居含む）等支援者の状況",
      fields: [
        {
          type: "table",
          key: "familyRows",
          label: "家族（別居含む）等支援者の状況",
          columns: [
            { key: "name", label: "1 氏名・協力者 ※1", type: "text", readonly: true },
            { key: "contact", label: "連絡先", type: "text", readonly: true },
            {
              key: "supportType",
              label: "2 介護家事支援内容（複数選択可） ※2",
              type: "multi",
              options: [
                { value: "キーパーソン", label: "①キーパーソン" },
                { value: "主介護者", label: "②主介護者" },
              ],
            },
            {
              key: "careSharing",
              label: "介護・家事の分担内容",
              type: "text",
              placeholder: "介護・家事の分担内容",
            },
            {
              key: "livingStatus",
              label: "3 同居/別居 ※3",
              type: "radio",
              options: [
                { value: "", label: "0.未選択（クリア）" },
                { value: "同居", label: "1.同居" },
                { value: "同居日中不在", label: "2.同居日中不在" },
                { value: "別居", label: "3.別居" },
              ],
            },
            {
              key: "careBurden",
              label: "4 介護負担:就労/就学等",
              type: "select",
              options: [
                { value: "", label: "選択" },
                { value: "就労中", label: "1.就労中" },
                { value: "就学中", label: "2.就学中" },
                { value: "高齢", label: "3.高齢" },
                { value: "要介護等", label: "4.要介護状態・病弱・認知症・身体障碍等" },
                { value: "妊娠", label: "5.妊娠" },
                { value: "育児中", label: "6.育児中" },
              ],
            },
          ],
          defaultRows: [
            { name: "", contact: "", supportType: [], careSharing: "", livingStatus: "", careBurden: "" },
            { name: "", contact: "", supportType: [], careSharing: "", livingStatus: "", careBurden: "" },
            { name: "", contact: "", supportType: [], careSharing: "", livingStatus: "", careBurden: "" },
            { name: "", contact: "", supportType: [], careSharing: "", livingStatus: "", careBurden: "" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "freeText",
      fields: [
        {
          type: "group",
          label: "5. ご利用者の希望・相談内容",
          fields: [
            {
              type: "textarea",
              key: "userRequests",
              label: "ご希望・ご相談内容を自由にご記入ください",
              rows: 4,
              placeholder: "例：今後の生活について相談したい、支援制度について知りたい など",
            },
          ],
        },
        {
          type: "group",
          label: "6. ご家族の希望・相談内容",
          fields: [
            {
              type: "textarea",
              key: "familyRequests",
              label:
                "ご希望・ご相談内容を自由にご記入ください ※ご家族がいない独居者は入力しないでください",
              rows: 4,
              placeholder: "例：今後の生活について相談したい、支援制度について知りたい など",
            },
          ],
        },
      ],
    },
      ],
    },
  ],
};

export default page1;
