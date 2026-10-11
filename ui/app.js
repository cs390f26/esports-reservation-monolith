const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);

function esc(value) {
  return String(value).replace(
    /[&<>"']/g,
    (ch) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[ch],
  );
}

function dateText(value) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function pretty(isoDate) {
  return new Date(`${isoDate}T12:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function hh(hour) {
  return `${String(hour).padStart(2, "0")}:00`;
}

function defaultDate() {
  const now = new Date();
  if (now.getHours() >= 20) {
    const next = new Date(now);
    next.setDate(next.getDate() + 1);
    return dateText(next);
  }
  return dateText(now);
}

function computerFor(inventory, spaceId) {
  return inventory.computers.find((computer) => computer.space_id === spaceId) || null;
}

function showLoadError(err) {
  const slot = $("#load-error");
  if (!slot) return;
  slot.hidden = false;
  slot.textContent = err.message || "The lounge data could not be loaded.";
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error("The lounge database could not be reached.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error((data && data.message) || "The lounge database could not be reached.");
  }
  return data;
}

function stationCard(space, computer, free) {
  const state = !space.is_active ? "Inactive" : free ? "Available" : "Reserved";
  const detail = computer ? esc(computer.hostname) : "No computer assigned";
  return `<a class="station" href="03-space-details.html?desk=${space.space_id}"><div class="row"><strong>${esc(space.space_name)}</strong><span aria-hidden="true">↗</span></div><div class="monitor" aria-hidden="true"></div><p>${detail}</p><span class="badge ${state === "Available" ? "" : "busy"}">${state}</span></a>`;
}

async function initOverview() {
  if (params.get("booked") === "1") $("#saved-note").hidden = false;
  const [inventory, blocks] = await Promise.all([api("/inventory"), api("/availability")]);
  const block = blocks[0];
  $("#block-kind").textContent = block.in_progress ? "Current time block" : "Next time block";
  $("#date-label").textContent = pretty(block.date);
  $("#block-label").textContent = `${hh(block.start_hour)}–${hh(block.end_hour)}`;
  $("#lounge-note").textContent = block.in_progress ? "" : " The lounge is closed.";
  const count = inventory.spaces.length;
  $("#station-count").textContent = `${count} station${count === 1 ? "" : "s"}`;
  $("#stations").innerHTML = inventory.spaces
    .map((space) =>
      stationCard(
        space,
        computerFor(inventory, space.space_id),
        block.space_ids.includes(space.space_id),
      ),
    )
    .join("");
}

async function initReservation() {
  const inventory = await api("/inventory");
  const form = $("#booking");
  const spaces = inventory.spaces.filter((space) => space.is_active);
  if (!spaces.length) {
    showLoadError(new Error("No active stations are available to reserve."));
    return;
  }
  form.desk.innerHTML = spaces
    .map((space) => {
      const computer = computerFor(inventory, space.space_id);
      const extra = computer ? ` · ${esc(computer.hostname)}` : "";
      return `<option value="${space.space_id}">${esc(space.space_name)}${extra}</option>`;
    })
    .join("");
  const wanted = params.get("desk");
  if (wanted && [...form.desk.options].some((option) => option.value === wanted)) {
    form.desk.value = wanted;
  }

  $("#equipment-list").innerHTML = inventory.equipment
    .map(
      (item) =>
        `<label class="check"><input type="checkbox" name="equipment" value="${item.equipment_id}" /><span>${esc(item.item_name)}</span><small>${esc(item.category)}</small></label>`,
    )
    .join("");

  form.date.value = params.get("date") || defaultDate();
  form.date.min = dateText(new Date());

  let blocks = [];
  let requestId = 0;

  function refreshEquipment() {
    const block = blocks.find((item) => String(item.start_hour) === form.block.value);
    const free = new Set(block ? block.equipment_ids : []);
    for (const input of form.querySelectorAll("[name=equipment]")) {
      const available = free.has(Number(input.value));
      input.disabled = !available;
      if (!available) input.checked = false;
    }
  }

  async function renderBlocks() {
    const id = ++requestId;
    if (!form.date.value) return;
    blocks = await api(`/availability?date=${encodeURIComponent(form.date.value)}`);
    if (id !== requestId) return;
    const picked = form.block.value;
    const now = new Date();
    form.block.innerHTML = blocks
      .map((block) => {
        const past = new Date(block.start_time) <= now;
        const busy = !block.space_ids.includes(Number(form.desk.value));
        const note = past ? " · Started" : busy ? " · Reserved" : "";
        return `<option value="${block.start_hour}"${past || busy ? " disabled" : ""}>${hh(block.start_hour)}–${hh(block.end_hour)}${note}</option>`;
      })
      .join("");
    const stillOpen = [...form.block.options].find(
      (option) => option.value === picked && !option.disabled,
    );
    const firstOpen = [...form.block.options].find((option) => !option.disabled);
    if (stillOpen) form.block.value = picked;
    else if (firstOpen) form.block.value = firstOpen.value;
    refreshEquipment();
  }

  function selectedEquipment() {
    return [...form.querySelectorAll("[name=equipment]:checked")].map((input) =>
      Number(input.value),
    );
  }

  function validate() {
    const option = form.block.selectedOptions[0];
    let message = "";
    if (!form.desk.value) message = "Choose a station.";
    else if (!form.name.value.trim()) message = "Enter the name for this reservation.";
    else if (!option || option.disabled) message = "Choose one of the available time blocks.";
    $("#feedback").textContent = message;
    if (message) return null;
    return {
      user_id: form.name.value.trim(),
      space_id: Number(form.desk.value),
      equipment_ids: selectedEquipment(),
      date: form.date.value,
      start_hour: Number(form.block.value),
    };
  }

  form.desk.onchange = () => {
    renderBlocks().catch((err) => {
      $("#feedback").textContent = err.message;
    });
  };
  form.date.onchange = () => {
    renderBlocks().catch((err) => {
      $("#feedback").textContent = err.message;
    });
  };
  form.block.onchange = refreshEquipment;

  let pending = null;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    pending = validate();
    if (!pending) return;
    const space = inventory.spaces.find((item) => item.space_id === pending.space_id);
    const names = pending.equipment_ids.map((id) => {
      const item = inventory.equipment.find((gear) => gear.equipment_id === id);
      return item ? item.item_name : "Equipment";
    });
    const gear = names.length ? names.map(esc).join(", ") : "No additional equipment";
    $("#summary").innerHTML = `<h3>${esc(space.space_name)}</h3><p>${pretty(pending.date)} · ${hh(pending.start_hour)}–${hh(pending.start_hour + 2)}<br>${esc(pending.user_id)}<br>${gear}</p>`;
    $("#confirm").showModal();
  });

  let saving = false;
  $("#confirm-booking").onclick = async () => {
    pending = validate();
    if (!pending) {
      $("#confirm").close();
      return;
    }
    if (saving) return;
    saving = true;
    try {
      await api("/reservations", { method: "POST", body: JSON.stringify(pending) });
      location.href = "01-overview.html?booked=1";
    } catch (err) {
      $("#confirm").close();
      $("#feedback").textContent = err.message;
    } finally {
      saving = false;
    }
  };

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.onclick = () => button.closest("dialog").close();
  });

  await renderBlocks();
}

async function initDetails() {
  const inventory = await api("/inventory");
  const space = inventory.spaces.find((item) => item.space_id === Number(params.get("desk")));
  if (!space) {
    $("#desk-title").textContent = "Station not found";
    $("#reserve-desk").hidden = true;
    showLoadError(new Error("That space could not be found."));
    return;
  }
  const computer = computerFor(inventory, space.space_id);
  $("#desk-title").textContent = space.space_name;
  $("#space-description").textContent =
    space.description || "Explore the setup, then reserve a time block.";
  $("#hostname").textContent = computer ? computer.hostname : "No computer assigned";
  $("#computer-status").textContent = computer ? computer.status : "—";
  $("#specs").textContent = computer && computer.specs ? computer.specs : "—";
  if (space.is_active) {
    $("#reserve-desk").href = `02-reservation.html?desk=${space.space_id}`;
  } else {
    $("#reserve-desk").hidden = true;
    $("#inactive-note").hidden = false;
  }
}

async function initSettings() {
  let inventory = await api("/inventory");
  const form = $("#desk-editor");

  function renderEquipment() {
    $("#equipment-list").innerHTML = inventory.equipment
      .map(
        (item) =>
          `<div class="listrow"><strong>${esc(item.item_name)}</strong><span>${esc(item.status)}</span></div>`,
      )
      .join("");
  }

  function renderRows() {
    $("#desk-rows").innerHTML = inventory.spaces
      .map((space) => {
        const computer = computerFor(inventory, space.space_id);
        const machine = computer
          ? `${esc(computer.hostname)} · ${esc(computer.status)}`
          : "No computer";
        return `<tr><td>${esc(space.space_name)}</td><td>${machine}</td><td><span class="badge ${space.is_active ? "" : "busy"}">${space.is_active ? "Active" : "Inactive"}</span></td><td><button type="button" data-edit="${space.space_id}">Edit</button></td></tr>`;
      })
      .join("");
  }

  function edit(spaceId) {
    const space = inventory.spaces.find((item) => item.space_id === Number(spaceId));
    if (!space) return;
    const computer = computerFor(inventory, space.space_id);
    form.desk.value = space.space_id;
    form.name.value = space.space_name;
    form.description.value = space.description || "";
    form.active.value = String(space.is_active);
    form.hostname.value = computer ? computer.hostname : "";
    form.specs.value = computer && computer.specs ? computer.specs : "";
    form.hostname.disabled = !computer;
    form.specs.disabled = !computer;
    form.hostname.required = Boolean(computer);
    $("#edit-heading").textContent = `Edit ${space.space_name}`;
  }

  renderRows();
  renderEquipment();
  const initial = params.get("desk") || (inventory.spaces[0] && inventory.spaces[0].space_id);
  if (initial) edit(initial);

  $("#desk-rows").onclick = (event) => {
    const button = event.target.closest("[data-edit]");
    if (button) edit(button.dataset.edit);
  };

  form.onsubmit = async (event) => {
    event.preventDefault();
    const spaceId = Number(form.desk.value);
    $("#feedback").textContent = "";
    try {
      const updatedSpace = await api(`/spaces/${spaceId}`, {
        method: "PATCH",
        body: JSON.stringify({
          space_name: form.name.value.trim(),
          description: form.description.value.trim() || null,
          is_active: form.active.value === "true",
        }),
      });
      inventory = {
        ...inventory,
        spaces: inventory.spaces.map((item) =>
          item.space_id === updatedSpace.space_id ? updatedSpace : item,
        ),
      };
      const computer = computerFor(inventory, spaceId);
      if (computer) {
        const updatedComputer = await api(`/computers/${computer.computer_id}`, {
          method: "PATCH",
          body: JSON.stringify({
            hostname: form.hostname.value.trim(),
            specs: form.specs.value.trim() || null,
          }),
        });
        inventory = {
          ...inventory,
          computers: inventory.computers.map((item) =>
            item.computer_id === updatedComputer.computer_id ? updatedComputer : item,
          ),
        };
      }
      renderRows();
      edit(spaceId);
      $("#feedback").textContent = "Station changes saved.";
    } catch (err) {
      renderRows();
      $("#feedback").textContent = err.message;
    }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  const pages = {
    overview: initOverview,
    reservation: initReservation,
    details: initDetails,
    settings: initSettings,
  };
  const start = pages[document.body.dataset.page];
  if (start) start().catch(showLoadError);
});
