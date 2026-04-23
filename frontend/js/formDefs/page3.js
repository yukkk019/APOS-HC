// page3: 住環境・写真スロット等を含むJSON定義。
const page3 = {
  id: 3,
  formTitle: "APOS-HC 調査票",
  badge: "No.3",
  fields: [
    {
      type: "group",
      key: "residentialEnvironment",
      label: "Ⅰ　住居環境と安全性",
      fields: [
        {
          type: "group",
          label: "① 住居",
          fields: [
            {
              type: "select",
              key: "residenceType",
              label: "住居の種類を選択してください",
              options: [
                { value: "", label: "選択してください" },
                { value: "house_1f", label: "1.1戸建て1階" },
                { value: "house_2f", label: "2.1戸建て2階" },
                { value: "apartment", label: "3.2階以上の集合住宅" },
              ],
            },
            {
              type: "text",
              key: "apartmentFloor",
              label: "集合住宅の場合は階数を入力してください：",
              inputType: "number",
              min: 2,
              max: 99,
              placeholder: "例：3",
              visibleIf: { field: "residenceType", equals: "apartment" },
            },
          ],
        },
        {
          type: "group",
          label: "② エレベーター",
          fields: [
            {
              type: "select",
              key: "elevator",
              label: "エレベーターの有無を選択してください",
              options: [
                { value: "", label: "選択してください" },
                { value: "あり", label: "0.あり・不要" },
                { value: "不要", label: "1.必要で無" },
              ],
            },
          ],
        },
        {
          type: "group",
          label: "③ 玄関から公道",
          fields: [
            {
              type: "select",
              key: "entranceToRoad",
              label: "車いすや杖歩行時に危険なく外出可能かを選択してください",
              options: [
                { value: "", label: "選択してください" },
                { value: "危険あり", label: "0.危険なし" },
                { value: "問題なし", label: "1.危険あり（バリアフリー化またはその代用用具が必要）" },
              ],
            },
          ],
        },
        {
          type: "photo_slots",
          key: "roomPhotos",
          label: "使用している部屋の見取図・安全性チェック・ケア用品の保管場所（任意）",
          slotCount: 3,
          helperText: "写真を保存するにはカメラで撮影または写真フォルダから選択してください。",
          defaultValue: [
            { filename: "", dataUrl: "" },
            { filename: "", dataUrl: "" },
            { filename: "", dataUrl: "" },
          ],
        },
        { type: "text", key: "room_photo1_image_filename", label: "部屋写真1（ローカルファイル名）" },
        { type: "text", key: "room_photo_image_1_filename", label: "部屋写真1（保存ファイル名）" },
        { type: "text", key: "room_photo2_image_filename", label: "部屋写真2（ローカルファイル名）" },
        { type: "text", key: "room_photo_image_2_filename", label: "部屋写真2（保存ファイル名）" },
        { type: "text", key: "room_photo3_image_filename", label: "部屋写真3（ローカルファイル名）" },
        { type: "text", key: "room_photo_image_3_filename", label: "部屋写真3（保存ファイル名）" },
        {
          type: "textarea",
          key: "roomSafetyNote",
          label:
            "補足事項や説明（福祉用具・医療機器等の保管場所、必要な手すり、転倒等の障害物、ペット周りの不備、災害/照明不良など）",
          rows: 4,
          placeholder:
            "例：福祉用具の保管場所、手すりの設置状況、障害物やペット、災害・照明の不備など",
        },
      ],
    },
    {
      type: "group",
      key: "cleanAndSafety",
      label: "Ⅱ　居室の清潔（家事）・住居環境の状況",
      fields: [
        {
          type: "group",
          label: "居室の清潔",
          fields: [
            {
              type: "select",
              key: "roomCleanliness",
              label: "在宅生活や療養室として適切ですか",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0．常に室内は一貫して清掃されており、ごみは適切に処分している" },
                { value: "1a", label: "1．本人が納得する清掃がされている、時々ごみ処分はできていない" },
                { value: "1b", label: "2．掃除はされず、ごみが散らかっている" },
                { value: "2a", label: "3．室内は汚く、ごみや排泄物で不衛生な状態" },
              ],
            },
          ],
        },
        {
          type: "group",
          label: "住居環境の状況",
          fields: [
            {
              type: "select",
              key: "roomSafetyLevel",
              label: "住居の安全性・適切な広さ",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0．住居は改修され機能的であり、家族人数に見合った広さである" },
                {
                  value: "1",
                  label:
                    "1．住居が機能的・安全でない個所の改修を希望している、家族人数には見合った広さである",
                },
                {
                  value: "2",
                  label:
                    "2．住居が機能的でなく障害物状態だが改修-整理を希望しない、家族人数に見合った広さでない",
                },
              ],
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "reformToolsEquipment",
      label: "Ⅲ　住居環境の改修/介護用具利用の必要性",
      fields: [
        {
          type: "group",
          key: "reform",
          label: "1. 住居環境",
          fields: [
            {
              type: "select",
              key: "need",
              label: "住居環境",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "必要なし" },
                { value: "1", label: "必要あり" },
              ],
            },
            {
              type: "multi",
              key: "places",
              label: "改修内容（複数選択可）",
              options: [
                { value: "居室", label: "居室" },
                { value: "浴室", label: "浴室" },
                { value: "脱衣室", label: "脱衣室" },
                { value: "浴槽", label: "浴槽" },
                { value: "トイレ", label: "トイレ" },
                { value: "便器", label: "便器" },
                { value: "廊下", label: "廊下" },
                { value: "玄関", label: "玄関" },
                { value: "庭", label: "庭" },
                { value: "階段", label: "階段" },
                { value: "その他", label: "その他" },
              ],
              visibleIf: { field: "need", equals: "1" },
            },
            {
              type: "text",
              key: "placeOtherText",
              label: "（その他の場合の詳細）",
              placeholder: "内容をご記入ください",
              visibleIf: { field: "need", equals: "1" },
            },
          ],
        },
        {
          type: "group",
          key: "careTool",
          label: "2. 介護用具",
          fields: [
            {
              type: "select",
              key: "need",
              label: "介護用具",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "必要なし" },
                { value: "1", label: "必要あり" },
              ],
            },
            {
              type: "multi",
              key: "types",
              label: "改修内容（複数選択可）",
              options: [
                { value: "移動用具", label: "移動用具" },
                { value: "生活用具", label: "生活用具" },
                { value: "介助用具", label: "介助用具" },
              ],
              visibleIf: { field: "need", equals: "1" },
            },
          ],
        },
        {
          type: "group",
          key: "equipment",
          label: "3. 設備",
          fields: [
            {
              type: "select",
              key: "need",
              label: "設備",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "必要なし" },
                { value: "1", label: "必要あり" },
              ],
            },
            {
              type: "multi",
              key: "types",
              label: "改修内容（複数選択可）",
              options: [
                { value: "障害者用生活用具", label: "障害者用調理・食事等生活用具" },
                { value: "電気", label: "電気" },
                { value: "冷暖房機", label: "冷暖房機" },
                { value: "エレベータ", label: "エレベータ" },
                { value: "その他", label: "その他" },
              ],
              visibleIf: { field: "need", equals: "1" },
            },
            {
              type: "text",
              key: "otherText",
              label: "（その他の場合の詳細）",
              placeholder: "内容をご記入ください",
              visibleIf: { field: "need", equals: "1" },
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "socialServiceDecision",
      label: "Ⅳ　介護保険サービス利用の判断",
      fields: [
        {
          type: "group",
          label: "介護保険サービス利用の判断",
          fields: [
            {
              type: "select",
              key: "usage",
              label: "該当する内容を選択してください",
              options: [
                { value: "", label: "選択してください" },
                {
                  value: "0",
                  label:
                    "0. 介護保険サービスや自費のサービスの導入などを判断し、積極的に介護に活用している",
                },
                { value: "1", label: "1. 介護・社会的サービスの導入を検討し判断している" },
                {
                  value: "2",
                  label:
                    "2. 介護・社会的サービスの制度や内容を知らない、導入の理解や判断には支援が必要",
                },
                {
                  value: "3",
                  label: "3. 介護・社会的サービスの制度や内容を知っていて使っていない、拒否している",
                },
              ],
            },
            {
              type: "textarea",
              key: "reasonText",
              label: "回答が3の方は理由を記入してください",
              rows: 3,
              placeholder: "理由を記入してください",
              visibleIf: { field: "usage", equals: "3" },
            },
          ],
        },
      ],
    },
  ],
};

export default page3;
