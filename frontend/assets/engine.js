// Canvas 기반 멀티 DB 엔진 — DB 아이콘을 Grid 노드에 연결하면 해당 DB의 레코드를 가져와 합쳐서 보여준다.
// $(), api(), setMessage() 는 app.js 에서 정의된 전역 헬퍼를 그대로 재사용한다.

const DB_META = {
  postgresql: { label: "PostgreSQL", emoji: "🐘", endpoint: "/lab/postgres/records", compatible: true },
  mongodb: { label: "MongoDB", emoji: "🍃", endpoint: "/lab/mongo/records", compatible: true },
  supabase: { label: "Supabase", emoji: "⚡", endpoint: "/lab/supabase/records", compatible: true },
  redis: { label: "Redis", emoji: "🟥", endpoint: "/lab/redis/records", compatible: true },
  opensearch: { label: "OpenSearch", emoji: "🔍", endpoint: "/lab/opensearch/records", compatible: true },
  clickhouse: { label: "ClickHouse", emoji: "🟧", endpoint: "/lab/clickhouse/records", compatible: true },
  cassandra: { label: "Cassandra", emoji: "👁️", endpoint: "/lab/cassandra/records", compatible: true },
  dynamodb: { label: "DynamoDB", emoji: "🔶", endpoint: null, compatible: false, reason: "Employee" },
  pinecone: { label: "Pinecone", emoji: "🌲", endpoint: null, compatible: false, reason: "Vector" },
  weaviate: { label: "Weaviate", emoji: "🟣", endpoint: null, compatible: false, reason: "Vector" },
  neo4j: { label: "Neo4j", emoji: "🕸️", endpoint: null, compatible: false, reason: "Graph" },
  qdrant: { label: "Qdrant", emoji: "🔵", endpoint: null, compatible: false, reason: "Vector" },
};

const NODE_RADIUS = 32;
const LAYOUT_KEY = "engineLayout";

const engineState = {
  nodes: [],
  sourceRows: new Map(),
  gridApi: null,
};

let engineInitialized = false;
let canvas = null;
let ctx = null;
let gridNode = null;
let dragNode = null;
let didDrag = false;
let connectingFrom = null;
let tempPoint = null;

const engineColumnDefs = [
  { field: "source", width: 130 },
  { field: "id", width: 160 },
  { field: "title", flex: 1 },
  { field: "content", flex: 1 },
  { headerName: "tags", width: 160, valueGetter: (p) => (p.data.tags || []).join(", ") },
];

function distTo(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function handlePos(node) {
  return { x: node.x + NODE_RADIUS + 6, y: node.y };
}

function removeBtnPos(node) {
  return { x: node.x - NODE_RADIUS * 0.7, y: node.y - NODE_RADIUS * 0.7 };
}

function edgeControlPoints(node) {
  const p0 = handlePos(node);
  const p3 = { x: gridNode.x - gridNode.w / 2, y: gridNode.y };
  const midX = (p0.x + p3.x) / 2;
  return [p0, { x: midX, y: p0.y }, { x: midX, y: p3.y }, p3];
}

function bezierPoint(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
}

function getPos(event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return { x: (event.clientX - rect.left) * scaleX, y: (event.clientY - rect.top) * scaleY };
}

function pointInGridNode(pos) {
  return Math.abs(pos.x - gridNode.x) <= gridNode.w / 2 && Math.abs(pos.y - gridNode.y) <= gridNode.h / 2;
}

function connectedNodeNearPoint(pos) {
  for (const node of engineState.nodes) {
    if (node.status !== "connected") continue;
    const [p0, cp1, cp2, p3] = edgeControlPoints(node);
    for (let t = 0; t <= 1; t += 0.05) {
      const pt = bezierPoint(p0, cp1, cp2, p3, t);
      if (distTo(pt, pos) < 10) return node;
    }
  }
  return null;
}

function totalRowCount() {
  let total = 0;
  engineState.sourceRows.forEach((rows) => (total += rows.length));
  return total;
}

function roundRect(context, x, y, w, h, r) {
  context.beginPath();
  context.moveTo(x + r, y);
  context.arcTo(x + w, y, x + w, y + h, r);
  context.arcTo(x + w, y + h, x, y + h, r);
  context.arcTo(x, y + h, x, y, r);
  context.arcTo(x, y, x + w, y, r);
  context.closePath();
}

function nodeColor(node) {
  const meta = DB_META[node.dbKey];
  if (!meta.compatible) return { stroke: "#94a3b8", dash: [4, 3], fill: "#f8fafc" };
  if (node.status === "connected") return { stroke: "#10b981", dash: [], fill: "#ecfdf5" };
  if (node.status === "loading") return { stroke: "#f59e0b", dash: [], fill: "#fffbeb" };
  return { stroke: "#6366f1", dash: [], fill: "#eef2ff" };
}

function drawGridNode() {
  ctx.save();
  ctx.fillStyle = "#1e293b";
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2;
  roundRect(ctx, gridNode.x - gridNode.w / 2, gridNode.y - gridNode.h / 2, gridNode.w, gridNode.h, 12);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#fff";
  ctx.font = "14px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("📊 Grid", gridNode.x, gridNode.y - 6);
  ctx.font = "10px sans-serif";
  ctx.fillText(`${totalRowCount()}건 합계`, gridNode.x, gridNode.y + 12);
  ctx.restore();
}

function drawEdge(node) {
  const [p0, cp1, cp2, p3] = edgeControlPoints(node);
  ctx.beginPath();
  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 2;
  ctx.moveTo(p0.x, p0.y);
  ctx.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, p3.x, p3.y);
  ctx.stroke();
}

function drawTempEdge(node, pos) {
  const p0 = handlePos(node);
  ctx.save();
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = "#6366f1";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(p0.x, p0.y);
  ctx.lineTo(pos.x, pos.y);
  ctx.stroke();
  ctx.restore();
}

function drawNode(node) {
  const meta = DB_META[node.dbKey];
  const color = nodeColor(node);

  ctx.save();
  ctx.setLineDash(color.dash);
  ctx.fillStyle = color.fill;
  ctx.strokeStyle = color.stroke;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(node.x, node.y, NODE_RADIUS, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();

  ctx.fillStyle = "#0f172a";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "18px sans-serif";
  ctx.fillText(meta.emoji, node.x, node.y - 8);
  ctx.font = "10px sans-serif";
  ctx.fillText(meta.label, node.x, node.y + 14);
  if (node.status === "connected") {
    ctx.fillStyle = "#059669";
    ctx.font = "9px sans-serif";
    ctx.fillText(`${node.rowCount}건`, node.x, node.y + 26);
  }

  const rb = removeBtnPos(node);
  ctx.beginPath();
  ctx.fillStyle = "#ef4444";
  ctx.arc(rb.x, rb.y, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.font = "10px sans-serif";
  ctx.fillText("✕", rb.x, rb.y + 1);

  const hp = handlePos(node);
  ctx.beginPath();
  ctx.fillStyle = meta.compatible ? "#6366f1" : "#94a3b8";
  ctx.arc(hp.x, hp.y, 6, 0, Math.PI * 2);
  ctx.fill();
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawGridNode();
  engineState.nodes.forEach((node) => {
    if (node.status === "connected") drawEdge(node);
  });
  if (connectingFrom && tempPoint) drawTempEdge(connectingFrom, tempPoint);
  engineState.nodes.forEach(drawNode);
}

function refreshEngineGrid() {
  const merged = [];
  engineState.sourceRows.forEach((rows) => merged.push(...rows));
  if (engineState.gridApi) engineState.gridApi.setGridOption("rowData", merged);
}

function saveLayout() {
  const layout = engineState.nodes.map((n) => ({
    dbKey: n.dbKey,
    x: n.x,
    y: n.y,
    connected: n.status === "connected",
  }));
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
}

function sampleRecord(dbKey, index) {
  const meta = DB_META[dbKey];
  return {
    id: `${dbKey}-${Date.now()}-${index}`,
    title: `${meta.label} 샘플 ${index}`,
    content: `${meta.label} 엔진 데모용 자동 생성 레코드입니다.`,
    tags: ["sample", dbKey],
  };
}

async function connectSource(node) {
  const meta = DB_META[node.dbKey];
  node.status = "loading";
  render();
  try {
    let rows = await api(`${meta.endpoint}?limit=20`);
    if (!rows.length) {
      for (let i = 1; i <= 3; i += 1) {
        await api(meta.endpoint, { method: "POST", body: JSON.stringify(sampleRecord(node.dbKey, i)) });
      }
      rows = await api(`${meta.endpoint}?limit=20`);
    }
    engineState.sourceRows.set(node.dbKey, rows);
    node.status = "connected";
    node.rowCount = rows.length;
    setMessage("engineMsg", "");
  } catch (error) {
    node.status = "idle";
    setMessage("engineMsg", `${meta.label} 연결 실패: ${error.message}`);
  }
  refreshEngineGrid();
  saveLayout();
  render();
}

function disconnectNode(node) {
  node.status = "idle";
  engineState.sourceRows.delete(node.dbKey);
  refreshEngineGrid();
  saveLayout();
  render();
}

function removeNode(node) {
  engineState.nodes = engineState.nodes.filter((n) => n !== node);
  engineState.sourceRows.delete(node.dbKey);
  refreshEngineGrid();
  saveLayout();
  render();
}

function attemptConnect(node) {
  const meta = DB_META[node.dbKey];
  if (!meta.compatible) {
    setMessage("engineMsg", `${meta.label} 는 레코드 구조(${meta.reason})가 달라 Grid에 직접 연결할 수 없습니다.`);
    return;
  }
  if (node.status === "connected") return;
  connectSource(node);
}

function addNode(dbKey) {
  if (engineState.nodes.some((n) => n.dbKey === dbKey)) {
    setMessage("engineMsg", `${DB_META[dbKey].label} 노드는 이미 캔버스에 있습니다.`);
    return;
  }
  const idx = engineState.nodes.length;
  engineState.nodes.push({
    dbKey,
    x: 90 + (idx % 3) * 140,
    y: 70 + Math.floor(idx / 3) * 110,
    status: "idle",
    rowCount: 0,
  });
  saveLayout();
  render();
}

function loadLayout() {
  const raw = localStorage.getItem(LAYOUT_KEY);
  if (!raw) return;
  let layout = [];
  try {
    layout = JSON.parse(raw);
  } catch {
    return;
  }
  layout.forEach((item) => {
    if (!DB_META[item.dbKey]) return;
    const node = { dbKey: item.dbKey, x: item.x, y: item.y, status: "idle", rowCount: 0 };
    engineState.nodes.push(node);
    if (item.connected && DB_META[item.dbKey].compatible) connectSource(node);
  });
}

function buildPalette() {
  const container = $("enginePalette");
  Object.entries(DB_META).forEach(([key, meta]) => {
    const btn = document.createElement("button");
    btn.textContent = `${meta.emoji} ${meta.label}`;
    btn.className = meta.compatible
      ? "text-xs px-3 py-2 rounded-full border border-emerald-500 bg-emerald-50"
      : "text-xs px-3 py-2 rounded-full border border-dashed border-slate-400 bg-slate-50 text-slate-500";
    btn.onclick = () => addNode(key);
    container.appendChild(btn);
  });
}

function initEngineGrid() {
  const gridOptions = {
    theme: "legacy",
    columnDefs: engineColumnDefs,
    rowData: [],
    defaultColDef: { sortable: true, resizable: true },
  };
  engineState.gridApi = agGrid.createGrid($("engineGrid"), gridOptions);
}

function attachCanvasEvents() {
  canvas.addEventListener("mousedown", (event) => {
    const pos = getPos(event);

    const handleHit = engineState.nodes.find((n) => distTo(pos, handlePos(n)) <= 10);
    if (handleHit) {
      connectingFrom = handleHit;
      tempPoint = pos;
      return;
    }

    const removeHit = engineState.nodes.find((n) => distTo(pos, removeBtnPos(n)) <= 10);
    if (removeHit) {
      removeNode(removeHit);
      return;
    }

    const bodyHit = engineState.nodes.find((n) => distTo(pos, n) <= NODE_RADIUS);
    if (bodyHit) {
      dragNode = bodyHit;
      didDrag = false;
      return;
    }

    const edgeHit = connectedNodeNearPoint(pos);
    if (edgeHit) disconnectNode(edgeHit);
  });

  canvas.addEventListener("mousemove", (event) => {
    const pos = getPos(event);
    if (connectingFrom) {
      tempPoint = pos;
      render();
      return;
    }
    if (dragNode) {
      didDrag = true;
      dragNode.x = pos.x;
      dragNode.y = pos.y;
      render();
    }
  });

  canvas.addEventListener("mouseup", (event) => {
    const pos = getPos(event);
    if (connectingFrom) {
      if (pointInGridNode(pos)) attemptConnect(connectingFrom);
      connectingFrom = null;
      tempPoint = null;
      render();
    }
    if (dragNode && didDrag) saveLayout();
    dragNode = null;
    didDrag = false;
  });

  canvas.addEventListener("mouseleave", () => {
    connectingFrom = null;
    tempPoint = null;
    dragNode = null;
    render();
  });
}

function initEngine() {
  canvas = $("engineCanvas");
  ctx = canvas.getContext("2d");
  gridNode = { x: canvas.width - 100, y: canvas.height / 2, w: 130, h: 80 };

  buildPalette();
  initEngineGrid();
  attachCanvasEvents();
  loadLayout();
  render();
  engineInitialized = true;
}

function showPostsTab() {
  $("postsView").classList.remove("hidden");
  $("engineView").classList.add("hidden");
  $("tabPosts").className = "px-3 py-2 rounded bg-indigo-600 text-white text-sm";
  $("tabEngine").className = "px-3 py-2 rounded bg-slate-200 text-sm";
}

function showEngineTab() {
  $("postsView").classList.add("hidden");
  $("engineView").classList.remove("hidden");
  $("tabEngine").className = "px-3 py-2 rounded bg-indigo-600 text-white text-sm";
  $("tabPosts").className = "px-3 py-2 rounded bg-slate-200 text-sm";
  if (!engineInitialized) initEngine();
}

$("tabPosts").onclick = showPostsTab;
$("tabEngine").onclick = showEngineTab;
