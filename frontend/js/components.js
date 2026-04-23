/**
 * このファイルは「入力パーツ部品集」です。
 * 例: 1行テキスト、ラジオ、日付(年/月/日)、表入力 など。
 *
 * どの部品も同じ形で使えるように、
 * - 画面に出す要素(el)
 * - 今の値を読む(getValue)
 * - 値を入れる(setValue)
 * をそろえています。
 */
import { formatDateString, splitDateString } from "./logic.js";

function createInputElement(inputType, def) {
  // 共通の入力欄を作る（placeholder や readonly もここで設定）
  const input = document.createElement("input");
  input.type = inputType;
  if (def.placeholder) input.placeholder = def.placeholder;
  if (def.readonly) input.disabled = true;
  if (def.min !== undefined) input.min = String(def.min);
  if (def.max !== undefined) input.max = String(def.max);
  if (def.step !== undefined) input.step = String(def.step);
  return input;
}

function bindSimpleValue(el, onChange, getter) {
  // 入力中でも確定時でも、最新の値を親へ知らせる
  ["input", "change"].forEach((eventName) => {
    el.addEventListener(eventName, () => onChange(getter()));
  });
}

function createText(def, initialValue = "", onChange = () => {}) {
  // 1行テキスト入力部品。
  const el = createInputElement(def.inputType || "text", def);
  const api = {
    el,
    getValue: () => el.value,
    setValue: (value) => {
      el.value = value ?? "";
    },
  };
  api.setValue(initialValue);
  bindSimpleValue(el, onChange, api.getValue);
  return api;
}

function createTextarea(def, initialValue = "", onChange = () => {}) {
  // 複数行テキスト入力部品。
  const el = document.createElement("textarea");
  if (def.rows) el.rows = def.rows;
  if (def.placeholder) el.placeholder = def.placeholder;
  if (def.readonly) el.disabled = true;

  const api = {
    el,
    getValue: () => el.value,
    setValue: (value) => {
      el.value = value ?? "";
    },
  };
  api.setValue(initialValue);
  bindSimpleValue(el, onChange, api.getValue);
  return api;
}

function createSelect(def, initialValue = "", onChange = () => {}) {
  // プルダウン選択部品（1つだけ選択）。
  const el = document.createElement("select");
  if (def.readonly) el.disabled = true;

  const options = def.options || [];
  options.forEach((option) => {
    const optionEl = document.createElement("option");
    optionEl.value = option.value;
    optionEl.textContent = option.label;
    el.appendChild(optionEl);
  });

  const api = {
    el,
    getValue: () => el.value,
    setValue: (value) => {
      el.value = value ?? "";
    },
  };
  api.setValue(initialValue);
  bindSimpleValue(el, onChange, api.getValue);
  return api;
}

function createRadio(def, initialValue = "", onChange = () => {}) {
  // ラジオボタン部品（1つだけ選択）。
  const wrapper = document.createElement("div");
  wrapper.className = "option-list";
  const name = `radio_${def.key}_${Math.random().toString(36).slice(2, 8)}`;
  const radios = [];

  (def.options || []).forEach((option) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = name;
    input.value = option.value;
    if (def.readonly) input.disabled = true;
    const text = document.createTextNode(` ${option.label}`);
    label.appendChild(input);
    label.appendChild(text);
    wrapper.appendChild(label);
    radios.push(input);
  });

  const api = {
    el: wrapper,
    getValue: () => {
      const checked = radios.find((radio) => radio.checked);
      return checked ? checked.value : "";
    },
    setValue: (value) => {
      radios.forEach((radio) => {
        radio.checked = radio.value === (value ?? "");
      });
    },
  };
  api.setValue(initialValue);
  radios.forEach((radio) => {
    radio.addEventListener("change", () => onChange(api.getValue()));
  });
  return api;
}

function createMulti(def, initialValue = [], onChange = () => {}) {
  // チェックボックス部品（複数選択可）。
  const wrapper = document.createElement("div");
  wrapper.className = "option-list";
  const checkboxes = [];

  (def.options || []).forEach((option) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = option.value;
    if (def.readonly) input.disabled = true;
    const text = document.createTextNode(` ${option.label}`);
    label.appendChild(input);
    label.appendChild(text);
    wrapper.appendChild(label);
    checkboxes.push(input);
  });

  const api = {
    el: wrapper,
    getValue: () =>
      checkboxes.filter((checkbox) => checkbox.checked).map((checkbox) => checkbox.value),
    setValue: (value) => {
      const next = Array.isArray(value) ? value.map(String) : [];
      checkboxes.forEach((checkbox) => {
        checkbox.checked = next.includes(checkbox.value);
      });
    },
  };
  api.setValue(initialValue);
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => onChange(api.getValue()));
  });
  return api;
}

function createDateTriplet(def, initialValue = "", onChange = () => {}) {
  // 年/月/日を別入力にしつつ、値は "YYYY-MM-DD" で扱う部品。
  const wrapper = document.createElement("div");
  wrapper.className = "date-triplet";

  const yearInput = createInputElement("number", { ...def, min: 1900, max: 2100, step: 1 });
  const monthInput = createInputElement("number", { ...def, min: 1, max: 12, step: 1 });
  const dayInput = createInputElement("number", { ...def, min: 1, max: 31, step: 1 });

  yearInput.placeholder = "年";
  monthInput.placeholder = "月";
  dayInput.placeholder = "日";

  wrapper.appendChild(yearInput);
  wrapper.appendChild(document.createTextNode("年"));
  wrapper.appendChild(monthInput);
  wrapper.appendChild(document.createTextNode("月"));
  wrapper.appendChild(dayInput);
  wrapper.appendChild(document.createTextNode("日"));

  const api = {
    el: wrapper,
    getValue: () => {
      const year = yearInput.value.trim();
      const month = monthInput.value.trim();
      const day = dayInput.value.trim();
      return formatDateString(year, month, day);
    },
    setValue: (value) => {
      const [year, month, day] = splitDateString(value);
      yearInput.value = year;
      monthInput.value = month;
      dayInput.value = day;
    },
  };

  api.setValue(initialValue);
  [yearInput, monthInput, dayInput].forEach((input) => {
    bindSimpleValue(input, onChange, api.getValue);
  });
  return api;
}

function createTable(def, initialValue = [], onChange = () => {}) {
  // 表形式入力部品。各セルに他コンポーネントを埋め込む。
  const wrapper = document.createElement("div");
  const table = document.createElement("table");
  table.className = "table-component";
  wrapper.appendChild(table);

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  table.appendChild(thead);
  thead.appendChild(headerRow);

  const tbody = document.createElement("tbody");
  table.appendChild(tbody);

  const columns = def.columns || [];
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column.label;
    headerRow.appendChild(th);
  });

  let rowComponents = [];

  function createCellComponent(column, value, rowIndex) {
    // 1セル分の入力部品を作る。
    const type = column.type || "text";
    // 「入力不可のテキスト列」は、入力欄ではなく見出し風の表示へする。
    // 例: page0 の「理由」列（初回 / 定期継続評価 ...）
    if (type === "text" && column.readonly && column.staticLabel !== false) {
      const el = document.createElement("div");
      el.className = "table-static-text";
      let currentValue = "";
      const api = {
        el,
        getValue: () => currentValue,
        setValue: (nextValue) => {
          currentValue = String(nextValue ?? "");
          el.textContent = currentValue;
        },
      };
      api.setValue(value);
      return api;
    }
    const fieldDef = {
      ...column,
      key: `${column.key}_${rowIndex}`,
      hideLabel: true,
    };
    const factory = components[type];
    if (!factory) {
      throw new Error(`Unsupported table column type: ${type}`);
    }
    return factory(fieldDef, value, () => onChange(api.getValue()));
  }

  function renderRows(rows) {
    // テーブル行を作り直して画面へ反映する。
    tbody.innerHTML = "";
    rowComponents = rows.map((row, rowIndex) => {
      const tr = document.createElement("tr");
      const cells = {};
      columns.forEach((column) => {
        const td = document.createElement("td");
        const comp = createCellComponent(column, row[column.key], rowIndex);
        td.appendChild(comp.el);
        tr.appendChild(td);
        cells[column.key] = comp;
      });
      tbody.appendChild(tr);
      return cells;
    });
  }

  const api = {
    el: wrapper,
    getValue: () =>
      rowComponents.map((rowMap) => {
        const row = {};
        columns.forEach((column) => {
          row[column.key] = rowMap[column.key].getValue();
        });
        return row;
      }),
    setValue: (value) => {
      const fallbackRows = Array.isArray(def.defaultRows) ? def.defaultRows : [];
      const rows = Array.isArray(value) && value.length > 0 ? value : fallbackRows;
      renderRows(rows);
    },
  };

  api.setValue(initialValue);
  return api;
}

function createPhotoSlots(def, initialValue = [], onChange = () => {}) {
  // 写真を複数枚（slotCount分）保存できる部品。
  const wrapper = document.createElement("div");
  wrapper.className = "photo-slots-component";

  const helper = document.createElement("div");
  helper.textContent =
    def.helperText ||
    "写真を保存するにはカメラで撮影または写真フォルダから選択してください。";
  helper.style.marginBottom = "8px";
  helper.style.color = "#2c3e50";
  wrapper.appendChild(helper);

  const slotCount = Number(def.slotCount || 3);
  const slots = [];

  function normalizeSlots(value) {
    // 外部値を {filename,dataUrl} の配列形式へそろえる。
    if (!Array.isArray(value)) return [];
    return value.map((entry) => ({
      filename: String(entry?.filename || ""),
      dataUrl: String(entry?.dataUrl || ""),
    }));
  }

  function emitChange() {
    // 変更通知を親へ渡す。
    onChange(api.getValue());
  }

  function createSlot(index) {
    // 1枠分のUI（プレビュー・撮影・選択・クリア）を作る。
    const card = document.createElement("div");
    card.style.margin = "10px 0";
    card.style.padding = "12px";
    card.style.border = "1px solid #b6cbd6";
    card.style.borderRadius = "10px";
    card.style.background = "#f8fbff";
    card.style.boxShadow = "0 2px 8px rgba(50,89,157,0.06)";

    const header = document.createElement("div");
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.justifyContent = "space-between";
    header.style.marginBottom = "8px";

    const title = document.createElement("div");
    title.style.fontWeight = "700";
    title.style.color = "#2c3e50";
    title.textContent = `写真 ${index + 1} / ${slotCount}`;

    const status = document.createElement("span");
    status.style.fontSize = "12px";
    status.style.padding = "2px 8px";
    status.style.borderRadius = "12px";
    status.style.border = "1px solid transparent";

    header.appendChild(title);
    header.appendChild(status);
    card.appendChild(header);

    const body = document.createElement("div");
    body.style.display = "flex";
    body.style.gap = "12px";
    body.style.alignItems = "flex-start";
    body.style.flexWrap = "wrap";

    const preview = document.createElement("div");
    preview.style.flex = "1 1 320px";
    preview.style.minWidth = "220px";
    preview.style.minHeight = "160px";
    preview.style.display = "flex";
    preview.style.alignItems = "center";
    preview.style.justifyContent = "center";
    preview.style.background = "#fff";
    preview.style.border = "2px dashed #c9d7eb";
    preview.style.borderRadius = "8px";
    preview.style.color = "#7a8aa0";

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.flexDirection = "column";
    actions.style.gap = "8px";

    const pickRow = document.createElement("div");
    const cameraBtn = document.createElement("button");
    cameraBtn.type = "button";
    cameraBtn.textContent = "カメラアプリで撮影";
    cameraBtn.style.padding = "8px 12px";
    cameraBtn.style.border = "1px solid #2d80bf";
    cameraBtn.style.background = "#3498db";
    cameraBtn.style.color = "#fff";
    cameraBtn.style.borderRadius = "6px";

    const galleryBtn = document.createElement("button");
    galleryBtn.type = "button";
    galleryBtn.textContent = "写真フォルダから選択";
    galleryBtn.style.padding = "8px 12px";
    galleryBtn.style.border = "1px solid #b0b7c3";
    galleryBtn.style.background = "#f1f5f9";
    galleryBtn.style.color = "#2c3e50";
    galleryBtn.style.borderRadius = "6px";
    galleryBtn.style.marginLeft = "8px";

    pickRow.appendChild(cameraBtn);
    pickRow.appendChild(galleryBtn);

    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.textContent = "クリア";
    clearBtn.style.padding = "8px 12px";
    clearBtn.style.border = "1px solid #b95b5b";
    clearBtn.style.background = "#ffecec";
    clearBtn.style.color = "#a03232";
    clearBtn.style.borderRadius = "6px";
    clearBtn.style.width = "fit-content";

    const fileCamera = document.createElement("input");
    fileCamera.type = "file";
    fileCamera.accept = "image/*";
    fileCamera.capture = "environment";
    fileCamera.style.display = "none";

    const fileGallery = document.createElement("input");
    fileGallery.type = "file";
    fileGallery.accept = "image/*";
    fileGallery.style.display = "none";

    actions.appendChild(pickRow);
    actions.appendChild(clearBtn);
    actions.appendChild(fileCamera);
    actions.appendChild(fileGallery);

    body.appendChild(preview);
    body.appendChild(actions);
    card.appendChild(body);
    wrapper.appendChild(card);

    const state = {
      filename: "",
      dataUrl: "",
      preview,
      status,
    };

    function renderSlot() {
      // 枠の状態（保存済み/未保存）とプレビュー表示を更新する。
      const hasImage = !!state.dataUrl;
      preview.innerHTML = "";
      if (hasImage) {
        const img = document.createElement("img");
        img.src = state.dataUrl;
        img.alt = `写真${index + 1}プレビュー`;
        img.style.maxWidth = "100%";
        img.style.maxHeight = "160px";
        img.style.objectFit = "contain";
        img.style.display = "block";
        preview.appendChild(img);

        status.textContent = state.filename ? `保存済み: ${state.filename}` : "保存済み";
        status.style.background = "#d4edda";
        status.style.color = "#155724";
        status.style.borderColor = "#c3e6cb";
      } else {
        preview.textContent = "ここにプレビューが表示されます";
        status.textContent = "未保存";
        status.style.background = "#fff3cd";
        status.style.color = "#856404";
        status.style.borderColor = "#ffe8a1";
      }
    }

    function setFile(file) {
      // 画像ファイルを読み込んで dataUrl として保持する。
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        state.filename = file.name || `room_photo_${index + 1}.jpg`;
        state.dataUrl = String(reader.result || "");
        renderSlot();
        emitChange();
      };
      reader.readAsDataURL(file);
    }

    cameraBtn.addEventListener("click", () => fileCamera.click());
    galleryBtn.addEventListener("click", () => fileGallery.click());
    clearBtn.addEventListener("click", () => {
      state.filename = "";
      state.dataUrl = "";
      fileCamera.value = "";
      fileGallery.value = "";
      renderSlot();
      emitChange();
    });

    fileCamera.addEventListener("change", (event) => {
      const file = event.target.files?.[0];
      setFile(file);
    });
    fileGallery.addEventListener("change", (event) => {
      const file = event.target.files?.[0];
      setFile(file);
    });

    renderSlot();
    return state;
  }

  for (let i = 0; i < slotCount; i += 1) {
    slots.push(createSlot(i));
  }

  const api = {
    el: wrapper,
    getValue: () =>
      slots.map((slot) => ({
        filename: slot.filename,
        dataUrl: slot.dataUrl,
      })),
    setValue: (value) => {
      const normalized = normalizeSlots(value);
      slots.forEach((slot, index) => {
        const next = normalized[index] || {};
        slot.filename = next.filename || "";
        slot.dataUrl = next.dataUrl || "";
        slot.status.style.borderColor = "transparent";
        slot.preview.innerHTML = "";
        if (slot.dataUrl) {
          const img = document.createElement("img");
          img.src = slot.dataUrl;
          img.alt = `写真${index + 1}プレビュー`;
          img.style.maxWidth = "100%";
          img.style.maxHeight = "160px";
          img.style.objectFit = "contain";
          img.style.display = "block";
          slot.preview.appendChild(img);
          slot.status.textContent = slot.filename ? `保存済み: ${slot.filename}` : "保存済み";
          slot.status.style.background = "#d4edda";
          slot.status.style.color = "#155724";
          slot.status.style.borderColor = "#c3e6cb";
        } else {
          slot.preview.textContent = "ここにプレビューが表示されます";
          slot.preview.style.color = "#7a8aa0";
          slot.status.textContent = "未保存";
          slot.status.style.background = "#fff3cd";
          slot.status.style.color = "#856404";
          slot.status.style.borderColor = "#ffe8a1";
        }
      });
    },
  };

  api.setValue(initialValue);
  return api;
}

function createImageDisplay(def) {
  // 画像を表示するだけの読み取り専用部品。
  const wrapper = document.createElement("div");
  wrapper.className = "image-display-component";

  if (def.caption) {
    const caption = document.createElement("div");
    caption.textContent = def.caption;
    caption.style.textAlign = "center";
    caption.style.fontSize = "0.93em";
    caption.style.color = "#000";
    caption.style.marginBottom = "6px";
    wrapper.appendChild(caption);
  }

  const img = document.createElement("img");
  img.src = def.src || "";
  img.alt = def.alt || "";
  img.style.maxWidth = "100%";
  img.style.height = "auto";
  img.style.border = "1px solid #b6cbd6";
  img.style.background = "#fff";
  if (def.width) img.style.width = def.width;
  wrapper.appendChild(img);

  return {
    el: wrapper,
    getValue: () => "",
    setValue: () => {},
  };
}

export const components = {
  text: createText,
  textarea: createTextarea,
  select: createSelect,
  radio: createRadio,
  multi: createMulti,
  date_triplet: createDateTriplet,
  table: createTable,
  photo_slots: createPhotoSlots,
  image_display: createImageDisplay,
};
