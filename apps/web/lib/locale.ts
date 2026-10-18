// R-13: the interface language, chosen once per browser and honoured by both halves of the app.
//
// Two decisions are load-bearing here, and both exist because the easy version breaks quietly.
//
// **A cookie, not localStorage.** Half of this app renders on the server (the landing page, the run list, the
// report page), and a value that only the browser can read arrives there one frame late: the server renders
// English, hydration then wants Chinese, and React reports the mismatch while the text flickers. The owner id
// in `owner.ts` already solved the same problem for a different value, so this reuses its shape -- first-party
// cookie, read by the server off the request and by client components off `document`.
//
// **One dictionary, keyed strings, no inline ternaries.** A page that writes `locale === "zh" ? A : B` is
// unguardable: nothing stops it from carrying the English branch and forgetting the other, and the failure is
// silent and per-page. Every translatable string therefore lives in `UI_STRINGS` below, and
// `tests/contract/test_web_locale_parity.py` asserts the two locales hold the same keys with no empty values,
// so an omission is a red test rather than an English sentence in a Chinese page.
//
// Analysis output is deliberately outside this module. A run's report renders in the language the run produced
// (the plan's rule, and the right one: machine-translating a statistician's finding is how numbers get lost),
// so nothing here touches report text, tool names, or column names.

export const LOCALE_COOKIE = "dsa_locale";

export const LOCALES = ["en", "zh"] as const;

export type Locale = (typeof LOCALES)[number];

export const LOCALE_LABELS: Record<Locale, string> = { en: "English", zh: "中文" };

export function normalizeLocale(value: unknown): Locale {
  return value === "zh" ? "zh" : "en";
}

/** Every string the interface owns, in both languages, under one key. */
export const UI_STRINGS: Record<Locale, Record<string, string>> = {
  en: {
    "meta.title": "Data Science Agent — Verifiable AI Data Science",
    "meta.description":
      "The AI data scientist that shows its work. Ask questions about your data and inspect the evidence behind the answer.",
    "a11y.skip": "Skip to content",
    "header.try": "Try DSA",
    "home.eyebrow": "Verifiable AI data science",
    "home.title": "The AI data scientist that shows its work.",
    "home.body":
      "Upload a dataset and ask a question in natural language. DSA runs statistics, SQL, machine learning, and visualization — then preserves the evidence behind every supported finding.",
    "home.cta.askSample": "Ask this of the sample data",
    "home.cta.tryYourData": "Try with your data",
    "home.cta.openExample": "Open a finished example",
    "home.cta.github": "View on GitHub ↗",
    "home.heroNote.sample":
      "The sample data and this question ship with the demo; the example report was run by this instance when it started. Nothing was written for this page.",
    "home.heroNote.flow": "Question → execution → evidence → claim → reproducible report",
    "home.stats.aria": "Project statistics",
    "home.stats.analyses": "Analyses",
    "home.stats.datasets": "Datasets",
    "home.stats.runsHere": "Runs in this environment",
    "home.stats.uploaded": "Uploaded files",
    "home.stats.connectApi": "Connect the API to see live counts",
    "home.stats.coverage": "Evidence coverage",
    "home.stats.coverageHint": "Computed per run · see Evaluation",
    "home.step1.label": "01 · Ask",
    "home.step1.title": "Start with the business question",
    "home.step1.body":
      "Use a CSV, Parquet, JSON, or Excel file and describe what you actually want to learn.",
    "home.step2.label": "02 · Analyze",
    "home.step2.title": "Let tools do the computation",
    "home.step2.body":
      "DSA plans and executes data-science tools instead of inventing numerical results in prose.",
    "home.step3.label": "03 · Verify",
    "home.step3.title": "Inspect where each claim came from",
    "home.step3.body":
      "Review the agent trace, claim-level evidence, validation checks, and reproducible artifacts.",
    "home.why.eyebrow": "Why DSA",
    "home.why.title":
      "Most AI analysis tools give you an answer. DSA gives you the answer and the evidence behind it.",
    "home.why.body":
      "That makes generated analysis easier to inspect, challenge, reproduce, and trust.",
    "home.why.link": "Start with Step 2 · Ask",
    "home.why.chain": "Claim\n └── Evidence\n      └── Tool call\n           └── Computation\n                └── Dataset hash",
    "home.recent.eyebrow": "Step 3 · Proof, not promises",
    "home.recent.title": "Recent analyses",
    "home.recent.description":
      "Latest runs in this environment. Open one to inspect its evidence chain.",
    "home.recent.start": "Start analysis",
    "home.recent.emptyTitle": "No analysis runs yet in this environment",
    "home.recent.emptyBody":
      "Upload a dataset and create the first run to see the evidence chain in action.",
    "home.recent.upload": "Upload a dataset →",
    "ask.eyebrow": "Step 2 · Ask a question",
    "ask.title": "Ask a real data-science question",
    "ask.description":
      "DSA will plan the analysis, execute tools, build evidence, and preserve the trace.",
    "ask.datasetLabel": "Dataset",
    "ask.datasetSelectAria": "Select dataset",
    "ask.selectNone": "— select —",
    "ask.noDatasets": "No datasets loaded.",
    "ask.uploadOne": "Upload one in Step 1 →",
    "ask.questionLabel": "Natural-language question",
    "ask.charUnit": "chars",
    "ask.wordUnit": "words",
    "ask.wordCountAria": "words",
    "ask.placeholder":
      "e.g. What is driving churn, and which findings are statistically supported?",
    "ask.examplesAria": "Example questions",
    "ask.suggestedFor": "Suggested for this dataset",
    "ask.defaultQuery":
      "Which factors explain the outcome, and are the effects statistically significant?",
    "ask.example1": "What is driving the target, and which effects are statistically significant?",
    "ask.example2": "Compare the main groups and explain the strongest differences.",
    "ask.example3": "Find the most important patterns, limitations, and evidence behind them.",
    "ask.chipVary": "How does {c} vary, and what explains the differences?",
    "ask.chipSpread": "What is the distribution of {c}, and are there outliers?",
    "ask.chipExplain": "Which factors explain {c}, and are the effects significant?",
    "ask.startingButton": "Starting analysis…",
    "ask.starting": "Starting…",
    "ask.runNow": "Run analysis →",
    "ask.watchNextPage": "The run starts immediately and you watch it on the next page.",
    "ask.retryCheck": "Retry the API check",
    "ask.needBoth": "Select a dataset and enter a question.",
    "ask.requestFailed": "Analysis request failed.",
    "ask.couldNotStart":
      "Analysis could not start because the DSA API at {url} is unavailable.",
    "ask.step1": "1. Execute",
    "ask.step1Body":
      "SQL, statistics, ML, and visualization tools run against your dataset — no invented numbers.",
    "ask.step2": "2. Verify",
    "ask.step2Body":
      "Every claim links back to evidence, tool calls, and the pinned dataset hash.",
    "ask.step3": "3. Reproduce",
    "ask.step3Body": "Inspect the trace, artifacts, and Markdown report in Step 3.",
    "ask.newHere": "New here?",
    "ask.newHereBodyPre": "Start at",
    "ask.newHereLink": "Step 1 · Bring your data",
    "ask.newHereBodyPost": ", then come back to ask.",
    "ask.confirmTitle": "Confirm analysis run",
    "ask.confirmBody": "Review before DSA starts planning and executing tools.",
    "ask.back": "Back",
    "ask.confirmRun": "Confirm & run →",
    "ds.eyebrow": "Step 1 · Bring your data",
    "ds.title": "Bring a dataset",
    "ds.description": "Upload a file, then ask DSA a real question about it.",
    "ds.compare": "Compare datasets",
    "ds.skipAsk": "Skip to Step 2 · Ask →",
    "ds.coldStart":
      "This demo runs on a free instance that sleeps when idle, so the first request after a pause can take about a minute.",
    "ds.uploadTitle": "Upload CSV, Parquet, JSON, or Excel (≤100MB)",
    "ds.uploadBody":
      "Drag a file onto the drop zone or browse. Accepted: .csv .parquet .json .xlsx .xls",
    "ds.ownerDisclosure":
      "Your uploads are kept apart from the next visitor's by a random id stored in a first-party cookie on this browser, which the app sends with every request. It is not an account: anyone holding that id reads the same rows, and clearing site data loses them for you too.",
    "ds.dropZoneAria": "Upload dataset: drag a file here or press Enter to browse",
    "ds.dropHere": "Drag & drop files here, or browse",
    "ds.dropNow": "Drop the files to upload",
    "ds.sendsToApi":
      "Your files are sent to the DSA API for profiling — nothing is stored in the browser.",
    "ds.browse": "Browse files",
    "ds.filesAria": "Dataset files",
    "ds.queueAria": "Upload queue",
    "ds.uploadedProfiled": "Uploaded — profiled and listed below.",
    "ds.sampleTitle": "Sample data shipped with this demo",
    "ds.sampleBody":
      "Copied from the repository at startup, so it is here after a redeploy that deletes uploads. The questions below are this project's own benchmark tasks for these exact bytes, and the report was run by this instance when it booted.",
    "ds.sampleChip": "sample",
    "ds.openReport": "Open its finished report →",
    "ds.askPrefix": "Ask: ",
    "ds.noQuestionForFile":
      "No benchmark task in the repository was written for this file's bytes, so no question is offered for it.",
    "ds.tableFills": "The table below fills in as soon as the API answers.",
    "ds.emptyTitle": "No datasets yet",
    "ds.emptyBody": "Upload one above to begin the demo flow: Bring → Ask → Inspect.",
    "ds.emptyUpload": "Upload your first dataset",
  },
  zh: {
    "meta.title": "数据科学智能体 — 可验证的 AI 数据科学",
    "meta.description": "会展示完整推导过程的 AI 数据科学家。就你的数据提问，并检查答案背后的证据。",
    "a11y.skip": "跳到主要内容",
    "header.try": "立即试用",
    "home.eyebrow": "可验证的 AI 数据科学",
    "home.title": "会展示完整推导过程的 AI 数据科学家",
    "home.body":
      "上传数据集，用自然语言提出问题。DSA 会执行统计、SQL、机器学习与可视化分析，并为每一个站得住脚的结论保留证据。",
    "home.cta.askSample": "就样例数据问这个问题",
    "home.cta.tryYourData": "用你的数据试一次",
    "home.cta.openExample": "打开一份已完成的报告",
    "home.cta.github": "在 GitHub 查看 ↗",
    "home.heroNote.sample":
      "样例数据和这个问题随 demo 一起发布；示例报告是这个实例启动时真实跑出来的，这一页没有为展示而伪造任何内容。",
    "home.heroNote.flow": "问题 → 执行 → 证据 → 结论 → 可复现报告",
    "home.stats.aria": "项目指标",
    "home.stats.analyses": "分析次数",
    "home.stats.datasets": "数据集",
    "home.stats.runsHere": "本环境中已完成的运行",
    "home.stats.uploaded": "已上传的文件",
    "home.stats.connectApi": "连上 API 后显示实时数字",
    "home.stats.coverage": "证据覆盖率",
    "home.stats.coverageHint": "按每次运行计算 · 见评估页",
    "home.step1.label": "01 · 提问",
    "home.step1.title": "从业务问题开始",
    "home.step1.body": "支持 CSV、Parquet、JSON 或 Excel 文件，直接说清你想知道什么。",
    "home.step2.label": "02 · 分析",
    "home.step2.title": "计算交给工具，不靠编",
    "home.step2.body": "DSA 会规划并真实执行数据科学工具，而不是在文字里凭空生成数值结果。",
    "home.step3.label": "03 · 验证",
    "home.step3.title": "查看每个结论从何而来",
    "home.step3.body": "可以回看智能体轨迹、逐条结论的证据、校验检查，以及可复现的产物文件。",
    "home.why.eyebrow": "为什么是 DSA",
    "home.why.title": "多数 AI 分析工具只给你答案；DSA 给答案，也给出答案背后的证据。",
    "home.why.body": "这让自动生成的分析更容易被检查、被质疑、被复现，也因此更值得信任。",
    "home.why.link": "从第 2 步 · 提问开始",
    "home.why.chain": "结论\n └── 证据\n      └── 工具调用\n           └── 计算过程\n                └── 数据集哈希",
    "home.recent.eyebrow": "第 3 步 · 看证据，不听承诺",
    "home.recent.title": "最近的分析",
    "home.recent.description": "本环境中最新的运行记录。打开任意一条即可查看它的证据链。",
    "home.recent.start": "开始一次分析",
    "home.recent.emptyTitle": "这个环境还没有任何分析运行",
    "home.recent.emptyBody": "上传数据集并跑出第一次运行，就能看到完整的证据链。",
    "home.recent.upload": "上传数据集 →",
    "ask.eyebrow": "第 2 步 · 提出一个问题",
    "ask.title": "提出一个真正的数据科学问题",
    "ask.description": "DSA 会规划分析、执行工具、构建证据，并保留完整轨迹。",
    "ask.datasetLabel": "数据集",
    "ask.datasetSelectAria": "选择数据集",
    "ask.selectNone": "— 请选择 —",
    "ask.noDatasets": "尚未加载任何数据集。",
    "ask.uploadOne": "先到第 1 步上传一个 →",
    "ask.questionLabel": "自然语言问题",
    "ask.charUnit": "字符",
    "ask.wordUnit": "词",
    "ask.wordCountAria": "词",
    "ask.placeholder": "例如：哪些因素驱动了流失，哪些结论有统计支持？",
    "ask.examplesAria": "示例问题",
    "ask.suggestedFor": "针对该数据集的建议",
    "ask.defaultQuery": "哪些因素解释了结果变量，这些效应是否具有统计显著性？",
    "ask.example1": "目标变量由什么驱动，哪些效应具有统计显著性？",
    "ask.example2": "比较主要分组，并解释其中最显著的差异。",
    "ask.example3": "找出最重要的模式、局限，以及支撑它们的证据。",
    "ask.chipVary": "{c} 如何变化，差异由什么解释？",
    "ask.chipSpread": "{c} 的分布是怎样的，是否存在异常值？",
    "ask.chipExplain": "哪些因素解释了 {c}，这些效应是否显著？",
    "ask.startingButton": "正在启动分析…",
    "ask.starting": "正在启动…",
    "ask.runNow": "运行分析 →",
    "ask.watchNextPage": "运行会立即开始，你可以在下一页查看它。",
    "ask.retryCheck": "重试 API 检查",
    "ask.needBoth": "请选择数据集并输入问题。",
    "ask.requestFailed": "分析请求失败。",
    "ask.couldNotStart": "无法开始分析，因为位于 {url} 的 DSA API 不可用。",
    "ask.step1": "1. 执行",
    "ask.step1Body": "SQL、统计、机器学习与可视化工具直接在你的数据集上运行——不编造数字。",
    "ask.step2": "2. 验证",
    "ask.step2Body": "每一条结论都回链到证据、工具调用与被锁定的数据集哈希。",
    "ask.step3": "3. 复现",
    "ask.step3Body": "在第 3 步查看轨迹、产物与 Markdown 报告。",
    "ask.newHere": "第一次使用？",
    "ask.newHereBodyPre": "先从",
    "ask.newHereLink": "第 1 步 · 带上你的数据",
    "ask.newHereBodyPost": "开始，然后再回来提问。",
    "ask.confirmTitle": "确认开始分析",
    "ask.confirmBody": "在 DSA 开始规划并执行工具之前，请先核对。",
    "ask.back": "返回",
    "ask.confirmRun": "确认并运行 →",
    "ds.eyebrow": "第 1 步 · 带上你的数据",
    "ds.title": "上传一个数据集",
    "ds.description": "上传文件，然后就它向 DSA 提一个真实的问题。",
    "ds.compare": "比较数据集",
    "ds.skipAsk": "跳到第 2 步 · 提问 →",
    "ds.coldStart": "本演示运行在空闲时会休眠的免费实例上，因此暂停后的第一个请求可能需要一分钟左右。",
    "ds.uploadTitle": "上传 CSV、Parquet、JSON 或 Excel（≤100MB）",
    "ds.uploadBody": "把文件拖到拖放区，或点击浏览。支持：.csv .parquet .json .xlsx .xls",
    "ds.ownerDisclosure":
      "你的上传内容通过一个存储在本浏览器首方 cookie 中的随机 id 与下一位访客隔离，应用会在每个请求中带上它。它不是账号：任何持有该 id 的人都读到同样的数据行；清除站点数据也会让这些数据对你消失。",
    "ds.dropZoneAria": "上传数据集：将文件拖到这里，或按 Enter 浏览",
    "ds.dropHere": "把文件拖放到此处，或浏览选择",
    "ds.dropNow": "松开即上传这些文件",
    "ds.sendsToApi": "你的文件会被发送到 DSA API 进行数据剖析——浏览器中不保存任何内容。",
    "ds.browse": "浏览文件",
    "ds.filesAria": "数据集文件",
    "ds.queueAria": "上传队列",
    "ds.uploadedProfiled": "已上传——完成剖析并在下方列出。",
    "ds.sampleTitle": "本演示自带的示例数据",
    "ds.sampleBody":
      "启动时从仓库复制，因此在会清除上传内容的重新部署之后依然在此。下面的问题是本项目针对这些完全相同的字节提交的基准任务，报告则由本实例在启动时运行生成。",
    "ds.sampleChip": "示例",
    "ds.openReport": "打开它已完成的报告 →",
    "ds.askPrefix": "提问：",
    "ds.noQuestionForFile": "仓库中没有为这个文件的字节编写过基准任务，因此不为它提供问题。",
    "ds.tableFills": "API 一经响应，下方表格就会立即填充。",
    "ds.emptyTitle": "还没有任何数据集",
    "ds.emptyBody": "先在上方上传一个，即可开始演示流程：带上数据 → 提问 → 查看证据。",
    "ds.emptyUpload": "上传你的第一个数据集",
  },
};

export function t(locale: Locale, key: string): string {
  const table = UI_STRINGS[locale] ?? UI_STRINGS.en;
  const value = table[key];
  if (value !== undefined) return value;
  // A missing key must be loud in the page and in the console, not a silent fallback to English: the whole
  // point of one dictionary is that an omission is noticed.
  return `⟨${key}⟩`;
}

/** The id the browser is already using, or the default when the cookie is absent or malformed. */
export function browserLocale(): Locale {
  if (typeof document === "undefined") return "en";
  const prefix = `${LOCALE_COOKIE}=`;
  for (const part of document.cookie.split(";")) {
    const entry = part.trim();
    if (entry.startsWith(prefix)) return normalizeLocale(entry.slice(prefix.length));
  }
  return "en";
}

/** Remember the choice and re-render in it. A reload is honest here; a half-translated page is not. */
export function storeLocale(locale: Locale): void {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax`;
}
