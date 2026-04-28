/**
 * ここは「画面全体の司令塔」です。
 *
 * 主な役割:
 * 1) 最初にユーザー情報（事業所番号・個人番号・何回目か）を受け取る
 * 2) 各ページの質問を読み込んで表示する
 * 3) 入力内容を自動保存する
 * 4) 最後にサーバーへ送信する
 */
import { FormRenderer, formState } from "./renderer.js";
import { calculateAgeFromDate, deepClone } from "./logic.js";
import { renderTopPage } from "./top.js";

const app = document.getElementById("app");
const totalPages = 20;
const submitEndpoint = "http://localhost:8000/submit";
const saveEndpoint = "http://localhost:8000/save";
const pageTitles = [
  "表紙",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
];
const pageLoaders = {
  0: () => import("./formDefs/page0.js"),
  1: () => import("./formDefs/page1.js"),
  2: () => import("./formDefs/page2.js"),
  3: () => import("./formDefs/page3.js"),
  4: () => import("./formDefs/page4.js"),
  5: () => import("./formDefs/page5.js"),
  6: () => import("./formDefs/page6.js"),
  7: () => import("./formDefs/page7.js"),
  8: () => import("./formDefs/page8.js"),
  9: () => import("./formDefs/page9.js"),
  10: () => import("./formDefs/page10.js"),
  11: () => import("./formDefs/page11.js"),
  12: () => import("./formDefs/page12.js"),
  13: () => import("./formDefs/page13.js"),
  14: () => import("./formDefs/page14.js"),
  15: () => import("./formDefs/page15.js"),
  16: () => import("./formDefs/page16.js"),
  17: () => import("./formDefs/page17.js"),
  18: () => import("./formDefs/page18.js"),
  19: () => import("./formDefs/page19.js"),
};
let currentPage = getInitialPage();
let renderer = null;
let syncing = false;
let saveTimer = null;
const pageValues = new Map();

// アプリ起動時は、まずユーザー情報入力画面を出す
renderUserIdForm();

function renderUserIdForm() {
  // 最初の入力画面（トップUI）は top.js に分離して描画する。
  renderTopPage({
    app,
    onStartRound: ({ facilityId, personId, assessmentRound }) => {
      const userId = `${facilityId}_${personId}`;
      formState._meta = {
        facilityId,
        personId,
        userId,
        assessmentRound,
      };
      pageValues.clear();
      Object.keys(formState).forEach((key) => {
        if (key !== "_meta") {
          delete formState[key];
        }
      });
      initializeRoundDataFromPreviousIfNeeded();

      // 回数開始時は表紙ページから開始する。
      currentPage = 0;
      bootstrapLayout();
      registerLegacyGlobalApi();
      updateQueryString(currentPage);
      loadAndRender(currentPage);
    },
    onOpenNeeds: ({ facilityId, personId }) => {
      const preferredRound = Number(formState?._meta?.assessmentRound || 1);
      const round = [1, 2, 3].includes(preferredRound) ? preferredRound : 1;
      try {
        localStorage.setItem("office_id", facilityId);
        localStorage.setItem("personal_id", personId);
        localStorage.setItem("session", String(round));
      } catch (_) {
        /* ignore */
      }
      const url = new URL("/api/newneed/static/display.html", window.location.origin);
      url.searchParams.set("office_id", facilityId);
      url.searchParams.set("personal_id", personId);
      url.searchParams.set("round", String(round));
      const path = window.location.pathname || "";
      const returnTo = path.endsWith("form.html") ? "/form.html" : "/frontend/index.html";
      url.searchParams.set("return_to", returnTo);
      window.location.href = url.toString();
    },
  });
}

function bootstrapLayout() {
  // 本体レイアウト（フォーム本体・ページ移動・送信結果欄）を作る。
  app.innerHTML = `
    <div class="container" style="position:relative;">
      <div id="dynamicRoot"></div>
      <div id="formFooterBar" class="form-footer-bar">
        <div id="pageJumpButtons" class="form-page-jump"></div>
        <div id="formFooterActions" class="form-footer-actions">
          <div id="formFooterLeft" class="form-footer-group">
            <button type="button" id="backPage" class="form-footer-btn">← 戻る</button>
            <button type="button" id="goTopPage" class="form-footer-btn">トップページに戻る</button>
          </div>
          <div id="formFooterRight" class="form-footer-group">
            <button type="button" id="saveDraftButton" class="form-footer-btn">一時保存</button>
            <button type="button" id="nextPage" class="form-footer-btn">次へ →</button>
          </div>
        </div>
      </div>
      <div id="submitResultPanel" aria-live="polite" style="display:none;margin-top:1rem;padding:0.75rem 1rem;border:1px solid #ccc;border-radius:6px;background:#fafafa;">
        <div id="submitResultTitle" style="font-weight:bold;margin-bottom:0.5rem;"></div>
        <pre id="submitResultBody" style="white-space:pre-wrap;word-break:break-word;margin:0;font-size:0.875rem;font-family:ui-monospace,monospace;"></pre>
      </div>
    </div>
  `;

  renderHeader();

  document.getElementById("backPage").addEventListener("click", async () => {
    if (currentPage > 0) {
      await saveDraft();
      currentPage -= 1;
      updateQueryString(currentPage);
      loadAndRender(currentPage);
    }
  });

  document.getElementById("goTopPage").addEventListener("click", async () => {
    await saveDraft();
    currentPage = 0;
    updateQueryString(currentPage);
    renderUserIdForm();
  });

  document.getElementById("saveDraftButton").addEventListener("click", async () => {
    await saveDraft();
    showSubmitResult("一時保存しました", "入力内容を下書きとして保存しました。");
  });

  document.getElementById("nextPage").addEventListener("click", async () => {
    if (currentPage < totalPages - 1) {
      await saveDraft();
      currentPage += 1;
      updateQueryString(currentPage);
      loadAndRender(currentPage);
    } else {
      await submitForm();
    }
  });
  hideSubmitResult();
}

function renderHeader() {
  // フッター中央のページ番号ボタンを作る
  const headerRoot = document.getElementById("pageJumpButtons");
  if (!headerRoot) return;
  headerRoot.innerHTML = "";
  const firstRow = document.createElement("div");
  firstRow.className = "form-page-jump-row";
  const secondRow = document.createElement("div");
  secondRow.className = "form-page-jump-row";
  pageTitles.forEach((title, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = title;
    btn.className = "form-page-btn";
    if (index === currentPage) {
      btn.classList.add("is-active");
    }
    btn.addEventListener("click", async () => {
      if (index === currentPage) return;
      await saveDraft();
      currentPage = index;
      updateQueryString(currentPage);
      loadAndRender(currentPage);
    });
    // 10 以降は2段目へ並べる（表紙〜9 が1段目、10〜19 が2段目）
    if (index >= 10) {
      secondRow.appendChild(btn);
    } else {
      firstRow.appendChild(btn);
    }
  });
  headerRoot.appendChild(firstRow);
  headerRoot.appendChild(secondRow);
}

function hideSubmitResult() {
  // 送信結果パネルを非表示にする。
  const panel = document.getElementById("submitResultPanel");
  if (panel) panel.style.display = "none";
}

function showSubmitResult(title, bodyText, { isError = false } = {}) {
  // 送信結果（成功/失敗）を画面下へ表示する。
  const panel = document.getElementById("submitResultPanel");
  const titleEl = document.getElementById("submitResultTitle");
  const bodyEl = document.getElementById("submitResultBody");
  if (!panel || !titleEl || !bodyEl) return;
  titleEl.textContent = title;
  bodyEl.textContent = bodyText;
  panel.style.display = "block";
  panel.style.borderColor = isError ? "#c00" : "#0a0";
  panel.style.background = isError ? "#fff5f5" : "#f5fff5";
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadAndRender(pageNumber) {
  // ページ定義を読み込み、保存済みデータがあればそれを入れて表示する
  renderHeader();

  const def = await loadPageDefinition(pageNumber);
  const mountPoint = document.getElementById("dynamicRoot");
  if (!def) {
    mountPoint.innerHTML = `<div class="form-section"><h2>ページ${pageNumber}</h2><p>このページ定義は未作成です。</p></div>`;
    return;
  }

  if (!renderer) {
    renderer = new FormRenderer(mountPoint, {
      onChange: (nextValue) => handleValueChange(nextValue),
    });
  } else {
    renderer.targetEl = mountPoint;
  }

  const saved = loadStoredPageValue(pageNumber);
  const initialValue = saved ?? pageValues.get(pageNumber) ?? {};
  renderer.render(def, initialValue);
  const renderedValue = renderer.getValue();
  pageValues.set(pageNumber, renderedValue);
  syncFormStatePage(pageNumber, renderedValue);
  setNavState();
}

function handleValueChange(nextValue) {
  // 入力が変わったら:
  // - 値を整える（自動計算など）
  // - 画面状態へ反映
  // - ローカル保存
  // - 下書き保存予約
  if (syncing) return;
  const normalized = normalizePageValue(currentPage, nextValue);
  pageValues.set(currentPage, normalized);
  syncFormStatePage(currentPage, normalized);
  const key = storageKey(currentPage);
  if (key) {
    localStorage.setItem(key, JSON.stringify(normalized));
  }
  queueDraftSave();

  if (JSON.stringify(normalized) !== JSON.stringify(nextValue)) {
    syncing = true;
    renderer.setValue(normalized);
    syncing = false;
  }
}

function queueDraftSave() {
  // 連打保存を防ぐため、少し待ってから下書き保存する
  if (saveTimer) {
    clearTimeout(saveTimer);
  }
  saveTimer = setTimeout(() => {
    saveDraft();
  }, 500);
}

function normalizePageValue(pageNumber, value) {
  // 自動計算が必要な項目（年齢/BMI/ブリンクマン指数）をここで計算
  const next = deepClone(value);
  if (pageNumber === 0) {
    const birthDate = next?.userInfo?.birthDate || "";
    const calculatedAge = calculateAgeFromDate(birthDate);
    if (next.userInfo) {
      next.userInfo.age = calculatedAge;
    }
  }
  if (pageNumber === 6) {
    const smoking = next?.lifestyleHealth?.smoking;
    if (smoking?.brinkman) {
      const amount = Number(smoking.brinkman.amount);
      const years = Number(smoking.brinkman.years);
      if (Number.isFinite(amount) && amount > 0 && Number.isFinite(years) && years > 0) {
        const index = Math.round(amount * years);
        smoking.brinkman.index = String(index);
        if (index >= 1200) {
          smoking.brinkman.judgement = "咽頭がんの危険群";
        } else if (index >= 600) {
          smoking.brinkman.judgement = "肺がんの高度危険群";
        } else if (index >= 400) {
          smoking.brinkman.judgement = "肺がんが発生しやすい";
        } else {
          smoking.brinkman.judgement = "危険群ではありません";
        }
      } else {
        smoking.brinkman.index = "";
        smoking.brinkman.judgement = "";
      }
    }
  }
  if (pageNumber === 7) {
    const bmi = next?.lifestyleHealth?.bmi;
    if (bmi) {
      const heightCm = Number(bmi.height);
      const weightKg = Number(bmi.weight);
      if (Number.isFinite(heightCm) && heightCm > 0 && Number.isFinite(weightKg) && weightKg > 0) {
        const heightM = heightCm / 100;
        const bmiValue = weightKg / (heightM * heightM);
        bmi.bmiValue = bmiValue.toFixed(1);
        if (bmiValue >= 40) {
          bmi.category = "4";
        } else if (bmiValue >= 35) {
          bmi.category = "3";
        } else if (bmiValue >= 30) {
          bmi.category = "2";
        } else if (bmiValue >= 25) {
          bmi.category = "1";
        } else if (bmiValue >= 18.5) {
          bmi.category = "0";
        } else if (bmiValue >= 17) {
          bmi.category = "5";
        } else if (bmiValue >= 16) {
          bmi.category = "6";
        } else {
          bmi.category = "7";
        }
      } else {
        bmi.bmiValue = "";
        bmi.category = "";
      }
    }
  }
  return next;
}

async function loadPageDefinition(pageNumber) {
  // 指定ページのJSON定義ファイルを読み込む。
  const loader = pageLoaders[pageNumber];
  if (!loader) return null;
  try {
    const module = await loader();
    return module.default;
  } catch (error) {
    return null;
  }
}

function getInitialPage() {
  // URLの ?page= を読んで、最初に開くページ番号を決める。
  const params = new URLSearchParams(window.location.search);
  const page = Number(params.get("page") || "0");
  if (Number.isFinite(page) && page >= 0 && page < totalPages) return page;
  return 0;
}

function updateQueryString(pageNumber) {
  // 画面遷移時にURLのページ番号を更新する。
  const next = new URL(window.location.href);
  next.searchParams.set("page", String(pageNumber));
  window.history.replaceState({}, "", next);
}

function getStorageScope() {
  // 保存先の名前を「ユーザーID + 何回目」で分けるための情報
  const userId = formState?._meta?.userId || "";
  const assessmentRound = Number(formState?._meta?.assessmentRound || 0);
  if (!userId || ![1, 2, 3].includes(assessmentRound)) {
    return null;
  }
  return {
    userId,
    assessmentRound,
  };
}

function storageKeyFor(pageNumber, userId, assessmentRound) {
  // localStorage の実キー文字列を作る。
  return `survey_${userId}_r${assessmentRound}_page_${pageNumber}`;
}

function hasAnyStoredDataForScope(userId, assessmentRound) {
  // そのユーザー・回数で1件でも保存があるか確認する。
  for (let i = 0; i < totalPages; i += 1) {
    const key = storageKeyFor(i, userId, assessmentRound);
    if (localStorage.getItem(key) != null) {
      return true;
    }
  }
  return false;
}

function initializeRoundDataFromPreviousIfNeeded() {
  // 2回目/3回目の「最初の1回だけ」前回データをコピーする
  const scope = getStorageScope();
  if (!scope) return;
  const { userId, assessmentRound } = scope;
  if (assessmentRound <= 1) return;
  if (hasAnyStoredDataForScope(userId, assessmentRound)) return;

  const previousRound = assessmentRound - 1;
  for (let i = 0; i < totalPages; i += 1) {
    const previousKey = storageKeyFor(i, userId, previousRound);
    const currentKey = storageKeyFor(i, userId, assessmentRound);
    const raw = localStorage.getItem(previousKey);
    if (raw != null) {
      localStorage.setItem(currentKey, raw);
    }
  }
}

function storageKey(pageNumber) {
  // 現在のユーザー文脈で使う localStorage キーを返す。
  const scope = getStorageScope();
  if (!scope) return null;
  return storageKeyFor(pageNumber, scope.userId, scope.assessmentRound);
}

function loadStoredPageValue(pageNumber) {
  // localStorage から指定ページの保存値を読む。
  try {
    const key = storageKey(pageNumber);
    if (!key) return null;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

function setNavState() {
  // 先頭/最終ページでは「前へ/次へ」を押せない状態にする。
  const prev = document.getElementById("backPage");
  const next = document.getElementById("nextPage");
  if (prev) prev.disabled = currentPage <= 0;
  if (next) {
    next.disabled = false;
    next.textContent = currentPage >= totalPages - 1 ? "送信" : "次へ →";
  }
}

function syncFormStatePage(pageNumber, value) {
  // 現在ページ値を共有状態 formState に反映する。
  formState[`page${pageNumber}`] = deepClone(value);
}

function collectAllAnswers() {
  // 全ページ分の回答を1つの answers オブジェクトにまとめる。
  const answers = {};
  for (let i = 0; i < totalPages; i += 1) {
    const stored = pageValues.get(i) ?? loadStoredPageValue(i);
    if (stored != null) {
      answers[`page${i}`] = deepClone(stored);
    }
  }
  return answers;
}

function snapshotCurrentPage() {
  // 画面上の最新入力を取り出し、状態とlocalStorageへ確定反映する。
  if (!renderer) return;
  const raw = renderer.getValue();
  const normalized = normalizePageValue(currentPage, raw);
  pageValues.set(currentPage, normalized);
  syncFormStatePage(currentPage, normalized);
  const key = storageKey(currentPage);
  if (key) {
    localStorage.setItem(key, JSON.stringify(normalized));
  }
  if (JSON.stringify(normalized) !== JSON.stringify(raw)) {
    syncing = true;
    renderer.setValue(normalized);
    syncing = false;
  }
}

async function saveDraft() {
  // 下書き保存: 入力途中の内容をサーバーへ送る
  const userId = formState?._meta?.userId || "";
  const assessmentRound = Number(formState?._meta?.assessmentRound || 0);
  if (!userId || ![1, 2, 3].includes(assessmentRound)) return;
  snapshotCurrentPage();
  const answers = collectAllAnswers();
  const payload = { userId, assessment_round: assessmentRound, answers };
  try {
    const res = await fetch(saveEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    console.log("自動保存OK");
  } catch (error) {
    console.error("自動保存失敗", error);
  }
}

async function submitForm() {
  // 最終送信: 全ページ分をまとめてサーバーへ送る
  const userId = formState?._meta?.userId || "";
  const assessmentRound = Number(formState?._meta?.assessmentRound || 0);
  if (!userId || ![1, 2, 3].includes(assessmentRound)) {
    alert("ユーザー情報が未入力です。最初からやり直してください。");
    return;
  }

  snapshotCurrentPage();
  const answers = collectAllAnswers();
  const payload = {
    userId,
    assessment_round: assessmentRound,
    answers,
  };

  try {
    const res = await fetch(submitEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const rawText = await res.text();
    let displayBody = rawText;
    try {
      const parsed = JSON.parse(rawText);
      displayBody = JSON.stringify(parsed, null, 2);
    } catch {
      // 非JSONの本文はそのまま表示
    }

    if (!res.ok) {
      showSubmitResult(`送信失敗（HTTP ${res.status}）`, displayBody, { isError: true });
      return;
    }

    showSubmitResult("送信成功（サーバーレスポンス）", displayBody, { isError: false });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : String(error);
    showSubmitResult("送信失敗（ネットワーク等）", message, { isError: true });
  }
}

function registerLegacyGlobalApi() {
  // 旧コード互換のため、window.getFormData/setFormData を公開する。
  window.getFormData = function getFormData() {
    if (renderer) return renderer.getValue();
    return pageValues.get(currentPage) ?? {};
  };

  window.setFormData = function setFormData(nextValue) {
    const normalized = normalizePageValue(currentPage, nextValue ?? {});
    pageValues.set(currentPage, normalized);
    syncFormStatePage(currentPage, normalized);
    const key = storageKey(currentPage);
    if (key) {
      localStorage.setItem(key, JSON.stringify(normalized));
    }
    if (renderer) {
      syncing = true;
      renderer.setValue(normalized);
      syncing = false;
    }
    return normalized;
  };
}
