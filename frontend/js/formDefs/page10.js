// page10: 食事・栄養関連項目のJSON定義。
const page10 = {
  id: 10,
  formTitle: "APOS-HC 調査票",
  badge: "No.10",
  fields: [
    {
      type: "group",
      key: "communicationHearingVision",
      label: "3.コミュニケーション・会話・聴覚",
      fields: [
        {
          type: "multi",
          key: "communicationMethod",
          label: "コミュニケーション手段（複数選択可）",
          options: [
            { value: "a", label: "a. 会話（音声）" },
            { value: "b", label: "b. 身振り" },
            { value: "c", label: "c. 表情/アイコンタクト" },
            { value: "d", label: "d. 文字盤" },
            { value: "e", label: "e. 筆談・絵文字・イラスト" },
            { value: "f", label: "f. 手話・点字・サイン" },
            { value: "g", label: "g. パソコン/通信装置/携帯会話補助器" },
            { value: "h", label: "h. 翻訳付きビデオ通話システム" },
            { value: "i", label: "i. その他" },
          ],
        },
        {
          type: "text",
          key: "communicationMethodOther",
          label: "コミュニケーション手段（その他）",
          placeholder: "その他の内容を記入",
        },
        {
          type: "select",
          key: "communicationLevel",
          label: "コミュニケーション能力",
          options: [
            { value: "", label: "選択してください" },
            {
              value: "0",
              label:
                "0．本人に合った方法で、日常生活のコミュニケーションが上手にとれている（会話・筆談・手話・点字・通訳・パソコン・携帯会話補助機・その他）",
            },
            { value: "1", label: "1．ゆっくりと安心した状態であれば自分の意思を伝えられる、相手の意思を理解できる" },
            { value: "2", label: "2．自分の意思を伝えづらい、相手の意思をあまり理解できない" },
            { value: "3", label: "3．言葉や非言語･感情の読み取り等全て伝えられない、相手の意思も全く理解できない" },
          ],
        },
        {
          type: "select",
          key: "conversationLevel",
          label: "会話成立状況",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0．明瞭に会話する／発音する" },
            { value: "1", label: "1．ほぼ会話はでき、相手に伝わっているが、時々言葉を忘れる" },
            { value: "2", label: "2．会話がつながらず途切れる、会話内容が伝わりにくい／言語障害がある" },
            { value: "3", label: "3．会話が全くできない／発語・発音ができない" },
          ],
        },
        {
          type: "select",
          key: "hearingLevel",
          label: "聴覚",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 問題なし" },
            { value: "1", label: "1. やや聞こえにくい" },
            { value: "2", label: "2. 補助が必要" },
            { value: "3", label: "3. 多くの補助が必要" },
            { value: "4", label: "4. ほぼ聞き取れない" },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "dailyCommunication",
      label: "4.日常の意思の伝達",
      fields: [
        {
          type: "select",
          key: "dailyCommunication",
          label: "日常のコミュニケーション",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0．相手に明確に自分の意思を伝えることができる" },
            { value: "1", label: "1．ほぼ意思を相手に伝えることができる、多少の困難がある、応対に時間がかかる" },
            { value: "2", label: "2．時々伝えられるが、基本的には食事やトイレなど具体的な欲求や事態のみ伝えられる" },
            { value: "3", label: "3．全く意思の伝達はできない、限られた者にのみ理解できるサインがある" },
          ],
        },
        {
          type: "select",
          key: "dailyJudgement",
          label: "日常の判断",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0．色々な事態や環境変化に直面しても、理にかなった判断ができ、相手に耳を傾けられる" },
            { value: "1", label: "1．新しい事態や周囲の環境変化に直面した時に混乱する、耳を傾けられない" },
            { value: "2", label: "2．落ち着かず、人に助けてもらわないと判断や相手を受け止められず、混乱する" },
            { value: "3", label: "3．支離滅裂な状態で全く判断できない・全く話を受け止められない" },
          ],
        },
        {
          type: "group",
          key: "delirium",
          label: "せん妄徴候",
          fields: [
            {
              type: "select",
              key: "exists",
              label: "せん妄徴候の有無",
              options: [
                { value: "", label: "選択してください" },
                { value: "0", label: "0. なし" },
                { value: "1", label: "1. あり" },
              ],
            },
            {
              type: "multi",
              key: "signs",
              label: "せん妄徴候（複数選択可）",
              visibleIf: { field: "exists", equals: "1" },
              options: [
                { value: "a", label: "a. 集中力低下・注意力散漫" },
                { value: "b", label: "b. 周囲環境認識の変化" },
                { value: "c", label: "c. 支離滅裂な会話" },
                { value: "d", label: "d. 落ち着きのなさ/無気力" },
                { value: "e", label: "e. 認知能力の日内変動" },
              ],
            },
          ],
        },
      ],
    },
    {
      type: "group",
      key: "vision",
      label: "5.視力・視覚",
      fields: [
        {
          type: "select",
          key: "ability",
          label: "視力・視覚能力",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0．日常の新聞・雑誌・パソコン・携帯等の文字読みができる" },
            { value: "1", label: "1．大きな文字のみ読める" },
            { value: "2", label: "2．視力に限界があり文字が読めないが、周辺の映像はわかる" },
            { value: "3", label: "3．ほとんど見えない" },
          ],
        },
        {
          type: "select",
          key: "condition",
          label: "視覚状態",
          options: [
            { value: "", label: "選択してください" },
            { value: "0", label: "0. 異常なし" },
            { value: "1", label: "1. 問題あり" },
          ],
        },
        {
          type: "multi",
          key: "conditionDetail",
          label: "視覚状態の詳細",
          visibleIf: { field: "condition", equals: "1" },
          options: [
            { value: "a", label: "a. 視野が限定される/見えづらい" },
            { value: "b", label: "b. 形識別困難/視野欠損/ゆがみ" },
            { value: "c", label: "c. まぶしさが強い" },
            { value: "d", label: "d. 色識別困難" },
            { value: "e", label: "e. 暗所で見えづらい" },
          ],
        },
      ],
    },
  ],
};

export default page10;
