const API_BASE = "";
const $ = (id) => document.getElementById(id);

const state = {
  token: localStorage.getItem("token") || "",
  editId: null,
  gridApi: null,
  query: "",
  loading: false,
};

const columnDefs = [
  { field: "id", width: 90 },
  { field: "title", flex: 1 },
  { field: "owner", width: 130 },
  { field: "views", width: 100 },
  { field: "created_at", width: 200 },
  {
    headerName: "액션",
    width: 180,
    cellRenderer: (params) => {
      const wrap = document.createElement("div");
      wrap.className = "h-full flex items-center gap-1";

      const editBtn = document.createElement("button");
      editBtn.textContent = "수정";
      editBtn.className = "text-xs px-2 py-1 rounded bg-amber-500 text-white";
      editBtn.onclick = () => openEditor(params.data);

      const deleteBtn = document.createElement("button");
      deleteBtn.textContent = "삭제";
      deleteBtn.className = "text-xs px-2 py-1 rounded bg-rose-600 text-white";
      deleteBtn.onclick = () => removePost(params.data.id);

      wrap.append(editBtn, deleteBtn);
      return wrap;
    },
  },
];

function setMessage(targetId, message = "") {
  $(targetId).textContent = message;
}

function setLoading(loading) {
  state.loading = loading;
  const disabled = loading ? "true" : "false";
  ["btnLogin", "btnSearch", "btnNew", "btnLogout", "btnSave"].forEach((id) => {
    const element = $(id);
    if (element) element.disabled = disabled === "true";
  });
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    logout();
    throw new Error("로그인이 필요합니다.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "요청 실패");
  return data;
}

async function withLoading(action) {
  setLoading(true);
  try {
    return await action();
  } finally {
    setLoading(false);
  }
}

async function login() {
  setMessage("loginMsg");
  await withLoading(async () => {
    const username = $("username").value.trim();
    const password = $("password").value;

    if (!username || !password) {
      throw new Error("아이디와 비밀번호를 입력해 주세요.");
    }

    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    state.token = data.access_token;
    localStorage.setItem("token", state.token);

    await loadMe();
    showApp();
    await loadPosts();
  }).catch((error) => {
    setMessage("loginMsg", error.message);
  });
}

async function loadMe() {
  const me = await api("/api/auth/me");
  $("me").textContent = `로그인: ${me.username}`;
}

async function loadPosts() {
  setMessage("appMsg");
  return withLoading(async () => {
    const params = new URLSearchParams({ page: "1", size: "50", sort: "id:desc" });
    if (state.query) params.set("q", state.query);

    const data = await api(`/api/posts?${params.toString()}`);
    state.gridApi.setGridOption("rowData", data.items);
  }).catch((error) => {
    setMessage("appMsg", error.message);
  });
}

function openEditor(row = null) {
  state.editId = row?.id || null;
  $("editorTitle").textContent = state.editId ? `게시글 수정 #${state.editId}` : "새 게시글";
  $("postTitle").value = row?.title || "";
  $("postContent").value = row?.content || "";
  $("editor").showModal();
}

async function savePost() {
  setMessage("appMsg");
  const payload = {
    title: $("postTitle").value.trim(),
    content: $("postContent").value.trim(),
  };

  if (!payload.title || !payload.content) {
    setMessage("appMsg", "제목과 내용을 입력해 주세요.");
    return;
  }

  await withLoading(async () => {
    if (state.editId) {
      await api(`/api/posts/${state.editId}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await api("/api/posts", { method: "POST", body: JSON.stringify(payload) });
    }

    $("editor").close();
    await loadPosts();
  }).catch((error) => {
    setMessage("appMsg", error.message);
  });
}

async function removePost(id) {
  if (!confirm("삭제하시겠습니까?")) return;

  await withLoading(async () => {
    await api(`/api/posts/${id}`, { method: "DELETE" });
    await loadPosts();
  }).catch((error) => {
    setMessage("appMsg", error.message);
  });
}

function showApp() {
  $("loginView").classList.add("hidden");
  $("appView").classList.remove("hidden");
}

function logout() {
  state.token = "";
  localStorage.removeItem("token");
  $("appView").classList.add("hidden");
  $("loginView").classList.remove("hidden");
}

function initGrid() {
  const gridOptions = {
    theme: "legacy",
    columnDefs,
    rowData: [],
    defaultColDef: { sortable: true, resizable: true },
  };
  state.gridApi = agGrid.createGrid($("grid"), gridOptions);
}

$("btnLogin").onclick = login;
$("btnLogout").onclick = logout;
$("btnNew").onclick = () => openEditor();
$("btnSave").onclick = async (event) => {
  event.preventDefault();
  await savePost();
};
$("btnSearch").onclick = async () => {
  state.query = $("search").value.trim();
  await loadPosts();
};
$("password").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    await login();
  }
});

initGrid();
if (state.token) {
  loadMe()
    .then(showApp)
    .then(loadPosts)
    .catch(() => {
      setMessage("loginMsg", "다시 로그인해 주세요.");
      logout();
    });
}
