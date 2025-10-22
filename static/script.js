async function loadCoins() {
  const res = await fetch("/coins");
  const data = await res.json();
  data.sort((a, b) => a.id - b.id);

  const uniqueBody = document.querySelector("#uniqueTable tbody");
  const duplicateBody = document.querySelector("#duplicateTable tbody");
  const uniqueEmpty = document.getElementById("uniqueEmpty");
  const duplicateEmpty = document.getElementById("duplicateEmpty");

  uniqueBody.innerHTML = "";
  duplicateBody.innerHTML = "";

  const uniqueCoins = data;
  const duplicateCoins = data.filter(c => c.exists_count > 1);

  if (uniqueCoins.length === 0) {
    uniqueEmpty.textContent = "No unique coins yet.";
  } else {
    uniqueEmpty.textContent = "";
  }

  if (duplicateCoins.length === 0) {
    duplicateEmpty.textContent = "No duplicates yet.";
  } else {
    duplicateEmpty.textContent = "";
  }

  const createRow = (coin, { displayCount, isDuplicateRow }) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${coin.id}</td>
      <td>${coin.country}</td>
      <td>${coin.denomination}</td>
      <td>${coin.year}</td>
      <td>${displayCount}</td>
      <td><button type="button">${coin.exists_count > 1 ? (isDuplicateRow ? "Remove duplicate" : "Remove one") : "Remove"}</button></td>
    `;
    const btn = tr.querySelector("button");
    btn.addEventListener("click", () => deleteCoin(coin.id, coin.exists_count, isDuplicateRow));
    return tr;
  };

  uniqueCoins.forEach(coin =>
    uniqueBody.appendChild(
      createRow(coin, {
        displayCount: Math.min(coin.exists_count, 1),
        isDuplicateRow: false
      })
    )
  );
  duplicateCoins.forEach(coin =>
    duplicateBody.appendChild(
      createRow(coin, {
        displayCount: coin.exists_count - 1,
        isDuplicateRow: true
      })
    )
  );
}

async function deleteCoin(id, count, isDuplicateRow) {
  const message = count > 1
    ? isDuplicateRow
      ? "Remove one duplicate copy of this coin?"
      : "Remove one copy of this coin?"
    : "Remove this coin from the collection?";

  if (!confirm(message)) return;

  const res = await fetch("/coins/" + id, { method: "DELETE" });
  const result = await res.json();
  const msg = document.getElementById("msg");

  if (result.error) {
    msg.textContent = `⚠️ ${result.error}`;
  } else if (result.status === "deleted") {
    msg.textContent = "🗑️ Coin removed.";
  } else if (result.status === "decremented") {
    msg.textContent = "➖ One copy removed.";
  }

  loadCoins();
}

document.querySelector("#coinForm").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    country: document.querySelector("#country").value,
    denomination: document.querySelector("#denomination").value,
    year: document.querySelector("#year").value
  };
  const res = await fetch("/coins", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const r = await res.json();
  const msg = document.getElementById("msg");
  if (r.error) {
    msg.textContent = `⚠️ ${r.error}`;
  } else if (r.status === "added") {
    msg.textContent = "✅ Coin added to the collection.";
  } else if (r.status === "incremented") {
    msg.textContent = "➕ Coin count increased.";
  }
  e.target.reset();
  loadCoins();
});

loadCoins();

