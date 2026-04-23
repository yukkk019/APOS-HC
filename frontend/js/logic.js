/**
 * どこからでも使う「小さな便利関数」を集めたファイルです。
 *
 * 例:
 * - 入れ子データの値を読む/書く
 * - データを安全にコピーする
 * - 日付を YYYY-MM-DD へ整える
 * - 生年月日から年齢を出す
 */
export function getByPath(obj, path) {
  // 【何をする？】
  // 深い場所にある値を、安全に取り出す。
  //
  // 【入力】
  // obj  : 調べたいデータ全体
  // path : 配列で指定する道順（例: ["userInfo", "name", "lastName"]）
  //
  // 【戻り値】
  // - 見つかればその値
  // - 見つからなければ undefined
  if (!Array.isArray(path) || path.length === 0) return obj;
  return path.reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

export function setByPath(obj, path, value) {
  // 【何をする？】
  // 深い場所にある値を書き換える。
  // 途中に箱（オブジェクト）がなければ自動で作る。
  //
  // 【例】
  // setByPath(data, ["userInfo","age"], "80")
  // -> data.userInfo.age が "80" になる
  if (!Array.isArray(path) || path.length === 0) return;
  let cursor = obj;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    if (typeof cursor[key] !== "object" || cursor[key] == null || Array.isArray(cursor[key])) {
      cursor[key] = {};
    }
    cursor = cursor[key];
  }
  cursor[path[path.length - 1]] = value;
}

export function deepClone(value) {
  // 【何をする？】
  // データの完全コピーを作る。
  // 元のデータが後で変わっても、コピー側は影響を受けない。
  return JSON.parse(JSON.stringify(value ?? {}));
}

export function formatDateString(year, month, day) {
  // 【何をする？】
  // 年・月・日を 1つの文字列 "YYYY-MM-DD" にまとめる。
  //
  // 【戻り値】
  // - 正しい日付形式なら "2026-04-22" のような文字列
  // - 入力不足/形式不正なら ""（空文字）
  if (!year || !month || !day) return "";
  const y = String(year).trim();
  const m = String(month).trim().padStart(2, "0");
  const d = String(day).trim().padStart(2, "0");
  if (!/^\d{4}$/.test(y) || !/^\d{2}$/.test(m) || !/^\d{2}$/.test(d)) return "";
  return `${y}-${m}-${d}`;
}

export function splitDateString(value) {
  // 【何をする？】
  // "YYYY-MM-DD" を [年, 月, 日] の3つに分ける。
  //
  // 【例】
  // "2026-04-22" -> ["2026", "4", "22"]
  const text = String(value || "").trim();
  const matched = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!matched) return ["", "", ""];
  return [matched[1], String(Number(matched[2])), String(Number(matched[3]))];
}

export function calculateAgeFromDate(dateString) {
  // 【何をする？】
  // 生年月日（YYYY-MM-DD）から現在の年齢を計算する。
  //
  // 【戻り値】
  // - 計算できれば "80" のような文字列
  // - 計算できなければ ""（空文字）
  const matched = String(dateString || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!matched) return "";
  const birthYear = Number(matched[1]);
  const birthMonth = Number(matched[2]);
  const birthDay = Number(matched[3]);
  const today = new Date();
  let age = today.getFullYear() - birthYear;
  const currentMonth = today.getMonth() + 1;
  const currentDay = today.getDate();
  if (currentMonth < birthMonth || (currentMonth === birthMonth && currentDay < birthDay)) {
    age -= 1;
  }
  if (age < 0 || age > 120) return "";
  return String(age);
}
