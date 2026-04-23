/**
 * トップページ（最初のユーザー入力画面）専用UIモジュール。
 * main.js からコールバックを受け取り、
 * - 回数開始
 * - ニーズ領域への遷移
 * を通知する。
 */

export function renderTopPage({ app, onStartRound, onOpenNeeds }) {
  app.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.className = "container";
  wrapper.style.maxWidth = "700px";
  wrapper.style.margin = "30px auto";
  wrapper.style.background = "#fff";
  wrapper.style.padding = "40px 30px";
  wrapper.style.borderRadius = "20px";
  wrapper.style.boxShadow = "0 6px 18px rgba(0,0,0,0.12)";
  wrapper.style.textAlign = "center";

  const title = document.createElement("h1");
  title.textContent = "APOS-HC 入力フォーム";
  title.style.color = "#1f80c4";
  title.style.fontSize = "1.8rem";
  title.style.marginBottom = "20px";

  const note = document.createElement("div");
  note.innerHTML = `
    <strong>ご使用上の注意</strong><br>
    ・このアンケートは表紙を含めて全20ページあります。すべて回答してください。<br>
    ・全3回（2か月ごと）にわたって行います。<br>
    ・ページを移動するか一時保存のボタンを押すと、その時点の入力が保存されます。
  `;
  note.style.background = "#f0f9f3";
  note.style.borderLeft = "6px solid #87d299";
  note.style.padding = "15px 18px";
  note.style.borderRadius = "10px";
  note.style.fontSize = "0.95rem";
  note.style.textAlign = "left";
  note.style.marginBottom = "30px";

  const inputBlock = document.createElement("div");
  inputBlock.style.marginBottom = "25px";
  inputBlock.style.textAlign = "left";

  const facilityInput = document.createElement("input");
  facilityInput.type = "text";
  facilityInput.placeholder = "事業所番号を入力";
  facilityInput.style.width = "100%";
  facilityInput.style.padding = "10px";
  facilityInput.style.boxSizing = "border-box";

  const personInput = document.createElement("input");
  personInput.type = "text";
  personInput.placeholder = "個人番号を入力";
  personInput.style.width = "100%";
  personInput.style.padding = "10px";
  personInput.style.boxSizing = "border-box";
  personInput.style.marginTop = "10px";

  const buttons = document.createElement("div");
  buttons.style.display = "flex";
  buttons.style.flexDirection = "column";
  buttons.style.alignItems = "center";
  buttons.style.gap = "12px";

  function createRoundButton(round) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = `${round}回目をはじめる`;
    btn.style.fontSize = "1.1rem";
    btn.style.padding = "14px 26px";
    btn.style.border = "none";
    btn.style.borderRadius = "12px";
    btn.style.backgroundColor = "#87d299";
    btn.style.color = "#fff";
    btn.style.cursor = "pointer";
    btn.style.width = "260px";
    btn.style.boxShadow = "0 4px 10px rgba(0,0,0,0.15)";
    return btn;
  }

  function validateUserInputs() {
    const facilityId = facilityInput.value.trim();
    const personId = personInput.value.trim();
    if (!facilityId || !personId) {
      alert("事業所番号と個人番号を入力してください。");
      return null;
    }
    return { facilityId, personId };
  }

  const round1Button = createRoundButton(1);
  const round2Button = createRoundButton(2);
  const round3Button = createRoundButton(3);
  const needsButton = document.createElement("button");
  needsButton.type = "button";
  needsButton.textContent = "ニーズ領域を参照";
  needsButton.style.fontSize = "1rem";
  needsButton.style.padding = "12px 24px";
  needsButton.style.border = "none";
  needsButton.style.borderRadius = "10px";
  needsButton.style.backgroundColor = "#1f80c4";
  needsButton.style.color = "#fff";
  needsButton.style.cursor = "pointer";
  needsButton.style.width = "260px";
  needsButton.style.boxShadow = "0 4px 10px rgba(0,0,0,0.15)";

  round1Button.addEventListener("click", () => {
    const inputs = validateUserInputs();
    if (!inputs) return;
    onStartRound({
      facilityId: inputs.facilityId,
      personId: inputs.personId,
      assessmentRound: 1,
    });
  });
  round2Button.addEventListener("click", () => {
    const inputs = validateUserInputs();
    if (!inputs) return;
    onStartRound({
      facilityId: inputs.facilityId,
      personId: inputs.personId,
      assessmentRound: 2,
    });
  });
  round3Button.addEventListener("click", () => {
    const inputs = validateUserInputs();
    if (!inputs) return;
    onStartRound({
      facilityId: inputs.facilityId,
      personId: inputs.personId,
      assessmentRound: 3,
    });
  });
  needsButton.addEventListener("click", () => {
    const inputs = validateUserInputs();
    if (!inputs) return;
    onOpenNeeds({
      facilityId: inputs.facilityId,
      personId: inputs.personId,
    });
  });

  wrapper.appendChild(title);
  wrapper.appendChild(note);
  inputBlock.appendChild(facilityInput);
  inputBlock.appendChild(personInput);
  wrapper.appendChild(inputBlock);
  buttons.appendChild(round1Button);
  buttons.appendChild(round2Button);
  buttons.appendChild(round3Button);
  buttons.appendChild(needsButton);
  wrapper.appendChild(buttons);
  app.appendChild(wrapper);
}
