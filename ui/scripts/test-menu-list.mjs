import axios from "axios";

const baseUrl = process.env.MENU_API_BASE_URL || "http://127.0.0.1:8000";
const url = `${baseUrl.replace(/\/$/, "")}/menu/list`;

function preview(items, n = 3) {
  return (items || []).slice(0, n).map((x) => ({
    id: x.id,
    dish_name: x.dish_name,
    price: x.price,
    category: x.category,
    is_available: x.is_available,
  }));
}

try {
  const res = await axios.get(url, {
    headers: { "Cache-Control": "no-cache" },
    params: { _ts: Date.now() }, // avoid any intermediate caching
    timeout: 10000,
  });

  const data = res.data;
  const ok = !!data?.success;
  const count = data?.count ?? (Array.isArray(data?.menu_items) ? data.menu_items.length : 0);

  console.log(`[menu-list] url=${url}`);
  console.log(`[menu-list] success=${ok} count=${count}`);
  if (typeof data?.message === "string") {
    console.log(`[menu-list] message=${data.message}`);
  }
  console.log("[menu-list] preview=", preview(data?.menu_items));
  if (!ok) {
    console.log("[menu-list] full_response=", data);
  }

  if (!ok) {
    process.exitCode = 2;
  } else if (!count) {
    process.exitCode = 3;
  }
} catch (err) {
  const status = err?.response?.status;
  const body = err?.response?.data;
  console.error(`[menu-list] url=${url}`);
  console.error("[menu-list] request failed:", status || "", body || err?.message || err);
  process.exitCode = 1;
}

