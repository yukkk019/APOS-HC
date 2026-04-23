/**
 * このファイルは「質問を画面に並べる係」です。
 *
 * JSONで書かれた質問定義を読み、
 * - 入力欄を作る
 * - 値を読み書きする
 * - 条件に応じて表示/非表示を切り替える
 * ことを行います。
 */
import { components } from "./components.js";
import { deepClone, getByPath, setByPath } from "./logic.js";

export const formState = {
  _meta: {},
};

export class FormRenderer {
  // 【クラスの役割】
  // JSONで書かれた「質問の設計図」から、実際の入力画面を作る。
  //
  // targetEl : 画面を描く場所（DOM要素）
  // onChange : 入力が変わるたびに呼ぶ関数
  constructor(targetEl, { onChange } = {}) {
    this.targetEl = targetEl;
    this.onChange = onChange || (() => {});
    this.bindings = [];
    this.value = {};
    this.fieldMap = {};
    this.visibilityItems = [];
    this.keyPathIndex = new Map();
  }

  // 【何をする？】
  // 1ページ分のフォームを最初から作り直して表示する。
  //
  // definition  : ページ定義（どの項目を出すか）
  // initialValue: 初期値（復元データなど）
  render(definition, initialValue = {}) {
    // ページを開くたびに、前の状態を消して作り直す
    this.definition = definition;
    this.value = deepClone(initialValue);
    this.bindings = [];
    this.fieldMap = {};
    this.visibilityItems = [];
    this.keyPathIndex = new Map();
    this.targetEl.innerHTML = "";

    const root = document.createElement("div");
    root.className = "dynamic-form-root";

    if (definition.formTitle) {
      const title = document.createElement("h1");
      title.textContent = definition.formTitle;
      root.appendChild(title);
    }

    if (definition.badge) {
      const badge = document.createElement("span");
      badge.textContent = definition.badge;
      badge.style.position = "absolute";
      badge.style.top = "40px";
      badge.style.right = "80px";
      badge.style.fontSize = "1.05em";
      badge.style.color = "#003366";
      badge.style.fontWeight = "600";
      badge.style.background = "#f5fafd";
      badge.style.borderRadius = "7px";
      badge.style.padding = "4px 18px 4px 10px";
      badge.style.boxShadow = "0 2px 6px rgba(0,0,0,0.04)";
      badge.style.letterSpacing = "0.08em";
      badge.style.zIndex = "2";
      root.appendChild(badge);
    }

    const form = document.createElement("form");
    form.id = "surveyForm";
    root.appendChild(form);

    this.renderFields(definition.fields || [], form, []);
    this.evaluateVisibility();
    this.targetEl.appendChild(root);
  }

  renderFields(fields, parentEl, basePath) {
    // fields配列を先頭から順番に描画する。
    fields.forEach((fieldDef) => {
      this.renderField(fieldDef, parentEl, basePath);
    });
  }

  renderField(fieldDef, parentEl, basePath) {
    // 1つの入力項目を描画して、値の保存先と連動させる。
    if (fieldDef.type === "group") {
      this.renderGroup(fieldDef, parentEl, basePath);
      return;
    }

    const factory = components[fieldDef.type];
    if (!factory) {
      throw new Error(`Unsupported field type: ${fieldDef.type}`);
    }

    const fieldPath = fieldDef.key ? [...basePath, fieldDef.key] : [...basePath];
    const defaultValue = fieldDef.defaultValue ?? (fieldDef.type === "multi" ? [] : "");
    const currentValue =
      fieldPath.length > 0 ? getByPath(this.value, fieldPath) ?? defaultValue : defaultValue;

    const row = document.createElement("div");
    row.className = "field-row";

    if (!fieldDef.hideLabel && fieldDef.label) {
      const labelEl = document.createElement("label");
      labelEl.className = "field-label";
      labelEl.textContent = fieldDef.label;
      row.appendChild(labelEl);
    }

    // 入力が変わったとき:
    // 1) データ更新
    // 2) 表示条件(visibleIf)を再判定
    // 3) main.jsへ変更通知
    const component = factory(fieldDef, currentValue, (nextValue) => {
      if (fieldPath.length > 0) {
        setByPath(this.value, fieldPath, nextValue);
      }
      this.evaluateVisibility();
      this.onChange(this.getValue());
    });

    row.appendChild(component.el);
    parentEl.appendChild(row);

    const fieldId = this.resolveFieldId(fieldDef, fieldPath);
    this.fieldMap[fieldId] = {
      component,
      wrapper: row,
      def: fieldDef,
      path: fieldPath,
    };
    this.visibilityItems.push({
      def: fieldDef,
      wrapper: row,
      path: fieldPath,
      component,
    });
    this.registerFieldPath(fieldDef, fieldPath);

    if (fieldPath.length > 0) {
      setByPath(this.value, fieldPath, component.getValue());
      this.bindings.push({ path: fieldPath, component, defaultValue });
    }
  }

  renderGroup(groupDef, parentEl, basePath) {
    // group（まとまり）を1つのセクションとして描画する。
    // groupの中の項目はこの関数内で再帰的に描画される。
    const groupPath = groupDef.key ? [...basePath, groupDef.key] : [...basePath];
    if (groupDef.key && getByPath(this.value, groupPath) == null) {
      setByPath(this.value, groupPath, {});
    }

    const section = document.createElement("section");
    section.className = "form-section";
    if (groupDef.className) section.classList.add(groupDef.className);

    if (groupDef.label) {
      const heading = document.createElement("h2");
      heading.textContent = groupDef.label;
      section.appendChild(heading);
    }

    this.renderFields(groupDef.fields || [], section, groupPath);
    parentEl.appendChild(section);

    const groupId = this.resolveFieldId(groupDef, groupPath);
    this.fieldMap[groupId] = {
      component: null,
      wrapper: section,
      def: groupDef,
      path: groupPath,
    };
    this.visibilityItems.push({
      def: groupDef,
      wrapper: section,
      path: groupPath,
      component: null,
    });
    this.registerFieldPath(groupDef, groupPath);
  }

  getValue() {
    // 画面上の「現在の入力値」をまとめて返す。
    // 返すのはコピーなので、外で編集しても内部状態は壊れない。
    return deepClone(this.value);
  }

  setValue(nextValue) {
    // 外から渡された値を、画面上の全入力欄へ反映する。
    // （復元時や自動計算で値を入れ直す時に使う）
    this.value = deepClone(nextValue);
    this.bindings.forEach(({ path, component, defaultValue }) => {
      const valueAtPath = getByPath(this.value, path);
      component.setValue(valueAtPath ?? defaultValue);
    });
    this.evaluateVisibility();
    this.onChange(this.getValue());
  }

  // visibleIfルールを見て、項目を「見せる / 隠す」を更新する。
  evaluateVisibility() {
    // 画面を作り直さずに、表示/非表示だけ切り替える
    const values =
      typeof window !== "undefined" && typeof window.getFormData === "function"
        ? window.getFormData()
        : this.getValue();

    this.visibilityItems.forEach((item) => {
      const { def, wrapper, path } = item;
      if (!def?.visibleIf) {
        wrapper.style.display = "";
        return;
      }

      const visible = this.checkVisibleIf(values, def.visibleIf, path);
      wrapper.style.display = visible ? "" : "none";
    });
  }

  // 1つの visibleIfルールを判定して true/false を返す。
  checkVisibleIf(values, rule, currentPath) {
    // 表示条件を判定する（等しい/等しくない/含む/OR/AND）
    if (!rule || typeof rule !== "object") return true;

    const anyRules = rule.any || rule.or;
    if (Array.isArray(anyRules)) {
      return anyRules.some((subRule) => this.checkVisibleIf(values, subRule, currentPath));
    }

    const allRules = rule.all || rule.and;
    if (Array.isArray(allRules)) {
      return allRules.every((subRule) => this.checkVisibleIf(values, subRule, currentPath));
    }

    const hasField = Object.prototype.hasOwnProperty.call(rule, "field");
    if (!hasField) return true;

    const targetValue = this.resolveTargetValue(values, rule.field, currentPath);
    let isVisible = true;

    if (Object.prototype.hasOwnProperty.call(rule, "equals")) {
      isVisible = isVisible && targetValue === rule.equals;
    }
    if (Object.prototype.hasOwnProperty.call(rule, "notEquals")) {
      isVisible = isVisible && targetValue !== rule.notEquals;
    }
    if (Object.prototype.hasOwnProperty.call(rule, "includes")) {
      isVisible = isVisible && this.matchIncludes(targetValue, rule.includes);
    }

    return isVisible;
  }

  matchIncludes(targetValue, expectedValue) {
    // includes判定の補助関数。
    // 配列にも文字列にも対応する。
    if (Array.isArray(targetValue)) {
      if (Array.isArray(expectedValue)) {
        return expectedValue.some((item) => targetValue.includes(item));
      }
      return targetValue.includes(expectedValue);
    }

    if (typeof targetValue === "string") {
      if (Array.isArray(expectedValue)) {
        return expectedValue.some((item) => targetValue.includes(String(item)));
      }
      return targetValue.includes(String(expectedValue));
    }

    return false;
  }

  resolveTargetValue(values, fieldRef, currentPath = []) {
    // visibleIf が参照する「比較元の値」を探す。
    // 同じキー名が複数ある場合でも、なるべく近い階層を優先する。
    if (!fieldRef) return undefined;
    if (fieldRef.includes(".")) {
      return getByPath(values, fieldRef.split("."));
    }

    const parentPath = Array.isArray(currentPath) ? currentPath.slice(0, -1) : [];
    for (let i = parentPath.length; i >= 0; i -= 1) {
      const candidatePath = [...parentPath.slice(0, i), fieldRef];
      if (this.hasPathInObject(values, candidatePath)) {
        return getByPath(values, candidatePath);
      }
    }

    const candidatePaths = this.keyPathIndex.get(fieldRef) || [];
    if (candidatePaths.length > 0) {
      return getByPath(values, candidatePaths[0]);
    }

    return getByPath(values, [fieldRef]);
  }

  resolveFieldId(def, path) {
    // 項目IDを決める。
    // 優先順: def.id -> def.key -> path文字列
    if (def?.id) return def.id;
    if (def?.key) return def.key;
    return path.join(".");
  }

  registerFieldPath(def, path) {
    // key名と実際の場所(path)の対応表を作る。
    // 後でvisibleIfの値探索で使う。
    if (!def?.key || path.length === 0) return;
    const list = this.keyPathIndex.get(def.key) || [];
    list.push(path);
    this.keyPathIndex.set(def.key, list);
  }

  hasPathInObject(obj, path) {
    // pathが実在するかを true/false で返す安全チェック。
    if (!Array.isArray(path) || path.length === 0) return false;
    let cursor = obj;
    for (let i = 0; i < path.length; i += 1) {
      const key = path[i];
      if (cursor == null || !Object.prototype.hasOwnProperty.call(cursor, key)) {
        return false;
      }
      cursor = cursor[key];
    }
    return true;
  }
}
