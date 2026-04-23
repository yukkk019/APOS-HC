// page9: 内服・医療管理情報のJSON定義。
const page9 = {
  id: 9,
  formTitle: "APOS-HC 調査票",
  badge: "No.9",
  fields: [
    {
      type: "group",
      key: "dailyLifeFunction",
      label: "Ⅶ　日常生活を行う機能",
      fields: [
        {
          type: "table",
          key: "adl",
          label: "1. ADLの機能",
          columns: [
            { key: "category", label: "区分", type: "text", readonly: true },
            { key: "item", label: "項目", type: "text", readonly: true },
            {
              key: "score",
              label: "評価（0〜5）",
              type: "select",
              options: [
                { value: "", label: "選択" },
                { value: "0", label: "0" },
                { value: "1", label: "1" },
                { value: "2", label: "2" },
                { value: "3", label: "3" },
                { value: "4", label: "4" },
                { value: "5", label: "5" },
              ],
            },
            { key: "note", label: "メモ欄", type: "text", placeholder: "自由記入" },
          ],
          defaultRows: [
            { category: "基本動作（身辺動作）①", item: "① 食事摂取", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "② 洗顔・整髪・洗髪", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "③ 手足・体の清拭", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "④ 上着の着脱（更衣）", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "⑤ パンツ・ズボン・スカート・くつ下の着脱", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "⑥ トイレ後の始末", score: "", note: "" },
            { category: "基本動作（身辺動作）①", item: "⑦ 入浴（体を洗う・シャワーで体を洗う）", score: "", note: "" },
            { category: "起居動作②", item: "⑧ 寝返り", score: "", note: "" },
            { category: "起居動作②", item: "⑨ 起き上がり", score: "", note: "" },
            { category: "起居動作②", item: "⑩ 座位保持", score: "", note: "" },
            { category: "起居動作②", item: "⑪ ベッド・椅子からの立ち上がり", score: "", note: "" },
            { category: "起居動作②", item: "⑫ 両足での立位保持", score: "", note: "" },
            { category: "移乗・移動③", item: "⑬ ベッドから車椅子・椅子、車いすからトイレに移乗", score: "", note: "" },
            { category: "移乗・移動③", item: "⑭ 浴槽またいでの出入り", score: "", note: "" },
            { category: "移乗・移動③", item: "⑮ 家の中の歩行（自力・杖・歩行器・車いす）", score: "", note: "" },
            { category: "移乗・移動③", item: "⑯ 外での歩行（自力・杖・歩行器・車いす）", score: "", note: "" },
          ],
        },
        {
          type: "table",
          key: "iadl",
          label: "2.社会的生活を行うためのセルフケア：IADL",
          columns: [
            { key: "item", label: "評価項目", type: "text", readonly: true },
            {
              key: "score",
              label: "評価",
              type: "select",
              options: [
                { value: "", label: "選択" },
                { value: "0", label: "0" },
                { value: "1", label: "1" },
                { value: "2", label: "2" },
                { value: "3", label: "3" },
                { value: "4", label: "4" },
              ],
            },
            { key: "note", label: "メモ欄", type: "text", placeholder: "自由記入" },
          ],
          defaultRows: [
            { item: "1. 電話の利用", score: "", note: "" },
            { item: "2. 日用品の買い物", score: "", note: "" },
            { item: "3. 食事の支度", score: "", note: "" },
            { item: "4. 掃除・食器洗い・ゴミ出し等の家事", score: "", note: "" },
            { item: "5. 洗濯", score: "", note: "" },
            { item: "6. 移動・外出", score: "", note: "" },
            { item: "7. 金銭の管理", score: "", note: "" },
            { item: "8. 薬の管理", score: "", note: "" },
            { item: "9. 冷暖房の管理", score: "", note: "" },
          ],
        },
      ],
    },
  ],
};

export default page9;
