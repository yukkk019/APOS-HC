const nrsOptions = [
  { value: "", label: "未選択" },
  { value: "0", label: "0" },
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "4", label: "4" },
  { value: "5", label: "5" },
  { value: "6", label: "6" },
  { value: "7", label: "7" },
  { value: "8", label: "8" },
  { value: "9", label: "9" },
  { value: "10", label: "10" },
];

const yesNoNeedOptions = [
  { value: "", label: "選択してください" },
  { value: "0", label: "0. 不要" },
  { value: "1", label: "1. 使用したい" },
];

// page18: 総合判定/ケア方針関連のJSON定義。
const page18 = {
  id: 18,
  formTitle: "APOS-HC 調査票",
  badge: "No.18",
  fields: [
    {
      type: "group",
      key: "eolIntro",
      label: "Ⅻ. エンドオブライフ/終末期の過ごし方・ACP",
      fields: [
        {
          type: "select",
          key: "induction_consultation",
          label: "1. 医師が余命６ケ月以内またはエンドオブライフ期と判断されましたか",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. いいえ" },
            { value: "1", label: "1. はい" },
          ],
        },
        {
          type: "textarea",
          key: "induction_detail_discussion",
          label: "2. 主治医との話し合いや意見：（病状や予後の理解・治療方針について話を受けていますか）",
          rows: 3,
          visibleIf: { field: "induction_consultation", equals: "1" },
        },
        {
          type: "textarea",
          key: "induction_detail_support",
          label: "3. 現在気がかりなこと・希望する支援体制",
          rows: 3,
          visibleIf: { field: "induction_consultation", equals: "1" },
        },
        {
          type: "textarea",
          key: "induction_detail_values",
          label: "4. 大切にしている価値観・目標",
          rows: 3,
          visibleIf: { field: "induction_consultation", equals: "1" },
        },
      ],
    },
    {
      type: "group",
      key: "symptomAssessment",
      label: "5. 訪問日前1週間の最も強い症状",
      fields: [
        { type: "select", key: "body_activity", label: "① 身体活動", options: nrsOptions },
        { type: "select", key: "pain", label: "② 痛み", options: nrsOptions },
        { type: "select", key: "numbness", label: "③ しびれ", options: nrsOptions },
        { type: "select", key: "drowsiness", label: "④ 眠け", options: nrsOptions },
        { type: "select", key: "fatigue_score", label: "⑤ だるさ", options: nrsOptions },
        { type: "select", key: "shortness_of_breath", label: "⑥ 息切れ", options: nrsOptions },
        { type: "select", key: "loss_of_appetite", label: "⑦ 食欲不振", options: nrsOptions },
        { type: "select", key: "nausea", label: "⑧ 吐き気", options: nrsOptions },
        { type: "select", key: "sleep", label: "⑨ 睡眠", options: nrsOptions },
        { type: "select", key: "emotional_distress", label: "⑩ 気持ちのつらさ", options: nrsOptions },
      ],
    },
    {
      type: "group",
      key: "transportWish",
      label: "6. 最期を迎えるときの救急搬送希望",
      fields: [
        {
          type: "select",
          key: "emergency_transport_wish",
          label: "救急搬送希望",
          options: [
            { value: "", label: "選択してください" },
            { value: "emergency_transport_wish_a", label: "a. 自宅を最初から選択しているので、このまま自宅で過ごしたい（救急搬送なし）" },
            { value: "emergency_transport_wish_b", label: "b. 施設で充分頑張ったので、最後は自宅で過ごしたい（救急搬送なし）" },
            { value: "emergency_transport_wish_c", label: "c. ホスピス・緩和ケア病棟に搬送してほしい" },
            { value: "emergency_transport_wish_d", label: "d. 老人ホーム(有料)・看護小規模多機能型居宅介護に搬送してほしい" },
            { value: "emergency_transport_wish_e", label: "e. 病院に搬送して欲しい" },
            { value: "emergency_transport_wish_f", label: "f. まだ決まっていない" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "treatmentAgreement",
      label: "7. 望む治療・望まない治療",
      fields: [
        { type: "select", key: "treatment_respirator", label: "1. 人工呼吸器", options: yesNoNeedOptions },
        { type: "select", key: "treatment_central_venous_nutrition", label: "2. 中心静脈栄養", options: yesNoNeedOptions },
        { type: "select", key: "treatment_infusion_hydration", label: "3. 輸液:水分補給", options: yesNoNeedOptions },
        { type: "select", key: "treatment_chemotherapy", label: "4. 化学療法", options: yesNoNeedOptions },
        { type: "select", key: "treatment_tube_feeding", label: "5. 経管栄養", options: yesNoNeedOptions },
        { type: "select", key: "treatment_drug_therapy", label: "6. 薬物療法", options: yesNoNeedOptions },
        { type: "select", key: "treatment_dialysis", label: "7. 人工透析", options: yesNoNeedOptions },
        { type: "select", key: "treatment_peritoneal_dialysis", label: "8. 腹膜透析", options: yesNoNeedOptions },
        { type: "select", key: "treatment_blood_transfusion", label: "9. 輸血", options: yesNoNeedOptions },
        { type: "select", key: "treatment_cardiac_massage", label: "10. 心臓マッサージ", options: yesNoNeedOptions },
        {
          type: "textarea",
          key: "treatment_other_detail",
          label: "11. その他（ご希望の使用したいものがあればご記入ください）",
          rows: 3,
        },
      ],
    },
    {
      type: "group",
      key: "lifeProlongation",
      label: "7. 延命について",
      fields: [
        {
          type: "multi",
          key: "life_prolongation",
          label: "希望内容（複数選択可）",
          options: [
            {
              value: "no_prolongation",
              label: "１．私の病が今の医学では治らない状態で、死が迫っていると診断された場合には、単に死期を引き延ばすための延命措置は望みません",
            },
            {
              value: "palliative_care",
              label: "２．ただし、私の苦痛を和らげるために、麻薬などの適切な使用により十分な緩和医療を行ってください",
            },
            {
              value: "withdraw_life_support",
              label: "３．私が回復不能な持続的植物状態に陥った時は、生命維持措置を取りやめてください",
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "acceptance",
      label: "8. 受入れ",
      fields: [
        {
          type: "select",
          key: "acceptance_individual",
          label: "① 本人:終末期の受入れ",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0 なし" },
            { value: "1", label: "1 あり" },
          ],
        },
        {
          type: "select",
          key: "acceptance_family",
          label: "② 家族:終末期の受入れ/家族間調整",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0 なし" },
            { value: "1", label: "1 あり" },
          ],
        },
      ],
    },
  ],
};

export default page18;
