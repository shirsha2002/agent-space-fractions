# Fresh Start Guide — শূন্য থেকে পুরো কাজ + Video

এই guide ধরে একদম শুরু থেকে কাজটা আবার করবে, আর সাথে সাথে video রেকর্ড করবে।
প্রতিটা ধাপে লেখা আছে **কী করবে**, **কী দেখবে**, আর video-তে **কী বলবে** (ইংরেজিতে)।

> ⚠️ তিনটা নিয়ম সবসময় মানবে:
> 1. **API key কখনো screen-এ দেখাবে না** — না video-তে, না screenshot-এ, না chat-এ।
> 2. খরচ: আগের run-এ খরচ হয়েছে ≈ **$0.21**। একটা নতুন live run-এ আরো ≈ $0.10–0.25 লাগতে পারে।
>    মোট $1-এর নিচে থাকবে, কিন্তু **একবারের বেশি live run করবে না**।
> 3. Game-এর নাম **Space Fractions** (ভগ্নাংশ), "Functions" না।

---

## Part 0 — বুঝে নাও কী বানানো হয়েছে (২ মিনিট পড়ো)

```
Teacher-এর 2টা markdown file  (game-এর বর্ণনা + UML diagram, কোনো code নেই)
            │  input
            ▼
🤖 Task1CodeAgent.exe   ← Task 1-এর আসল জিনিস (code agent)
   • file পড়ে → DeepSeek (deepseek-v4-pro)-কে কাজ পাঠায়
   • AI-এর লেখা পুরো project folder-এ save করে
   • test চালায়, ভুল হলে AI-কে দিয়ে ঠিক করায় (সর্বোচ্চ 2 বার)
            │  output = source code folder (code + requirements.txt + README + tests)
            ▼
PyInstaller build script  → 🎮 SpaceFractions.exe (খেলার জন্য)
```

| File | কোথায় |
| --- | --- |
| Code Agent | `D:\varsity program\dist\current\Task1CodeAgent.exe` |
| Final game | `D:\varsity program\dist\game\SpaceFractions.exe` |
| Input 1 | `D:\varsity program\inputs\Architecture_Documentation.md` |
| Input 2 | `D:\varsity program\inputs\Architecture_View.md` |
| আগের আসল run-এর প্রমাণ | `D:\varsity program\examples\space_fractions\provenance\` |

---

## Part 1 — Recording-এর আগে প্রস্তুতি (১০ মিনিট)

1. **সব খোলা app বন্ধ করো** — বিশেষ করে Task1CodeAgent আর SpaceFractions।
2. **Desktop পরিষ্কার করো** — notification বন্ধ করো (Windows: Settings → System → Notifications → Off)।
   Browser-এ Gmail/ব্যক্তিগত tab বন্ধ রাখো।
3. **নতুন output folder বানাও:** `D:\Task1Demo` (খালি folder)। এতে video-তে পুরনো run দেখা যাবে না।
4. **API key তৈরি রাখো Notepad-এ নয়** — DeepSeek website (platform.deepseek.com → API keys) থেকে copy করবে
   recording **pause করে**, তারপর paste করে আবার recording চালু করবে।
5. **Game-এর পুরনো account মুছতে চাইলে (ঐচ্ছিক, fresh look-এর জন্য):**
   File Explorer-এর address bar-এ `%APPDATA%` লিখে Enter → `SpaceFractions` folder থাকলে মুছে দাও।
   এতে admin password আর score নতুন করে শুরু হবে।
6. **Recording tool:** `Win + G` → Xbox Game Bar → Capture → ⏺ (অথবা OBS Studio, যেটা পুরো screen ধরে)।
   Mic চালু রাখো। প্রথমে ১০ সেকেন্ডের test recording করে শুনে নাও।

---

## Part 2 — Video রেকর্ডিং (মোট ৫–৭ মিনিট)

### Scene 1 — পরিচয় (৩০ সেকেন্ড)
**দেখাবে:** GitHub repo page (https://github.com/shirsha2002/agent-space-fractions)

**বলবে:**
> "Hello, I'm Shirsha Mitra. This is my Task 1: a simplified code agent for Windows.
> It reads two architecture documents, uses the official DeepSeek API with the deepseek-v4-pro model,
> and generates a complete desktop project — here, an educational game called Space Fractions."

### Scene 2 — Input file দেখানো (৩০ সেকেন্ড)
**করবে:** VS Code-এ `inputs\Architecture_Documentation.md` খোলো, একটু scroll করো; তারপর `Architecture_View.md` খুলে UML অংশ দেখাও।

**বলবে:**
> "These are the two inputs from the task. They contain no code — only the architecture description and
> UML diagrams: use cases, classes, states and sequences. The agent must turn these into a working project."

### Scene 3 — Agent খোলা (৩০ সেকেন্ড)
**করবে:** File Explorer → `D:\varsity program\dist\current\` → **Task1CodeAgent.exe** double-click → window maximize (□)।

**বলবে:**
> "This is the agent, packaged as a standalone Windows exe with PyInstaller, so no Python installation is needed.
> The GUI has the four required parts: input files, output folder, API key, and the start button."

(mouse দিয়ে একে একে চারটা অংশ দেখাও)

### Scene 4 — Offline check (১ মিনিট) — খরচ নেই
**করবে:**
1. **Offline pipeline check** বাছা আছে দেখো।
2. Input দুটো **Browse** দিয়ে `D:\varsity program\inputs\`-এর file দুটো বাছো।
3. Output folder-এ **Browse** → `D:\Task1Demo`।
4. **Run offline check** চাপো → ডানদিকে log চলবে।

**বলবে:**
> "First, an offline check. It uses mocked responses — no API call, no cost — to test the agent's pipeline:
> input loading, normalising requirements to JSON, safe file writing, validation, and the repair loop."

### Scene 5 — Live DeepSeek generation (২–৩ মিনিট, সময় বাঁচাতে কেটে ছোট করবে)
**করবে:**
1. **Live DeepSeek generation** বাছো।
2. ⏸ **Recording pause** → API key ঘরে key paste → ▶ recording চালু। (key-টা `•••` হয়ে লুকানো থাকবে)
3. **Check model** চাপো → model access ঠিক আছে কিনা log-এ দেখাবে।
4. Output token cap = `16000`, Repairs = `2` যেমন আছে রাখো।
5. ☑ **"I authorize paid calls within the cumulative USD 1 cap."**
6. **Generate project** চাপো → অপেক্ষা (১–৩ মিনিট)। Log-এ request আর token usage দেখাবে।

**বলবে:**
> "Now the real run. The agent sends the normalised requirements to deepseek-v4-pro and asks for a complete
> project as a strict JSON file manifest. Before each call, it reserves the worst-case cost against a
> one-dollar budget, and it rejects any unsafe paths before writing files."

7. শেষ হলে status **review_required** আসবে। **Open run** চাপো → folder খুলবে → `project` folder-এ ঢুকে
   `main.py`, `requirements.txt`, `README.md`, `tests\` দেখাও।

**বলবে:**
> "Here is the generated project: source files, a dependency manifest, a README and tests.
> Generated code is untrusted, so the agent requires a human review before executing anything."

8. Code-এ চোখ বুলিয়ে ☑ **"I reviewed this run's source before executing it."** → **Validate & repair reviewed source**।
9. Test fail করলে agent নিজে repair করবে → আবার review চাইবে → আবার tick + Validate চাপো (সর্বোচ্চ ২ বার)।

**বলবে:**
> "The agent runs static checks and the tests, including independent rule tests that the model did not write.
> If something fails, it sends only the errors and affected files back to DeepSeek for a bounded repair."

10. **ফল যাই হোক, সৎভাবে বলবে:**
    - `tests_passed` হলে → **Launch output** চাপো → নতুন generate হওয়া game খুলবে, ১০ সেকেন্ড দেখাও।
    - repair-এর পরও fail হলে → বলবে:
      > "In this run the model's output still had a failing test after two repairs. The agent stops and reports
      > that honestly instead of claiming success."

    ⚠️ **কোনোভাবেই দ্বিতীয়বার live run করবে না** — বাজেট বাঁচাও।

### Scene 6 — খরচ আর আগের আসল run-এর প্রমাণ (৪৫ সেকেন্ড)
**করবে:** Log-এর শেষে cost summary দেখাও। তারপর VS Code-এ খোলো:
`examples\space_fractions\provenance\usage_ledger.json`

**বলবে:**
> "The token ledger is saved across runs. My earlier full run used three calls and cost about
> twenty-one cents; together with today's run it stays under the one-dollar limit.
> The final game I'll show next comes from that earlier run; every model output and every human fix is
> recorded in this provenance folder."

### Scene 7 — Final game খেলা (২ মিনিট)
**করবে:** `D:\varsity program\dist\game\SpaceFractions.exe` double-click।

1. **Register New Player** → username `demo`, password `demo12345` (দুবার) → Register।
2. Login → rocket intro দেখাও (বা Space চাপো skip-এর জন্য)।
3. **Help** দেখাও → Back।
4. **Play Game** → ২–৩টা প্রশ্ন ঠিক উত্তর দাও, ১টা ইচ্ছে করে ভুল দাও (লাল/সবুজ দেখাও)।
5. **Esc** চাপো → PAUSED দেখাও → আবার Esc → resume।
6. বাকি প্রশ্নগুলো দ্রুত শেষ করো (number key 1–4 + Enter) → **Mission Complete** score দেখাও।
7. **Back to Menu → Score History** দেখাও।

**বলবে:**
> "The game follows the UML: play game, view score and view help for the player; playing, paused and
> game-over states; and the question-answer sequence. Answers are checked with exact fraction arithmetic,
> and each question scores only once."

### Scene 8 — Admin (১ মিনিট)
**করবে:**
1. **Logout** → **First time? Set up admin password** → নিজের admin password দাও (৮+ অক্ষর)।
2. Username `admin` + ওই password দিয়ে login → intro skip।
3. **⚙ Admin Panel** → কোনো প্রশ্নের **Edit** → prompt-এ একটু বদলাও → **Save**।

**বলবে:**
> "The Admin actor from the use-case diagram can update questions. Passwords are hashed, and normal players
> cannot open this panel."

### Scene 9 — সমাপ্তি আর সীমাবদ্ধতা (৩০ সেকেন্ড)
**বলবে:**
> "Limitations: the source architecture describes cloud microservices, but the task requires a desktop app,
> so I adapted it to a local modular design and documented every deviation. The final game includes
> disclosed human fixes after generation. Everything — code, tests, report and evidence — is in the
> GitHub repository. Thank you."

⏹ Recording বন্ধ।

---

## Part 3 — Video edit আর upload (২০ মিনিট)

1. লম্বা অপেক্ষার অংশ কেটে ছোট করো (Windows **Clipchamp** বিনামূল্যে আছে)।
   কাটা জায়গায় ছোট লেখা দাও: *"Waiting for DeepSeek response (cut for time)"* — এটা সততার জন্য জরুরি।
2. পুরো video একবার দেখে নিশ্চিত হও **API key কোথাও দেখা যাচ্ছে না**।
3. YouTube → Create → Upload video → Title: `Task 1 – DeepSeek Code Agent & Space Fractions (Shirsha Mitra)`
   → Visibility: **Unlisted** → Publish → link copy করো।
4. Incognito window-এ link খুলে দেখো video চলছে কিনা।

---

## Part 4 — GitHub Release-এ exe দেওয়া (৫ মিনিট)

1. https://github.com/shirsha2002/agent-space-fractions → ডানদিকে **Create a new release**।
2. **Choose a tag** → `v1.0` → *Create new tag*।
3. Title: `Task 1 Submission v1.0`
4. Description:
   > Download Task1_Submission.zip, extract it, then double-click Task1CodeAgent.exe (agent) or
   > SpaceFractions.exe (generated game). No Python installation needed.
5. এই file তিনটা টেনে ছাড়ো:
   - `D:\varsity program\release\Task1_Submission.zip`
   - `D:\varsity program\dist\current\Task1CodeAgent.exe`
   - `D:\varsity program\dist\game\SpaceFractions.exe`
6. **Publish release** → release page-এর link copy করো।

---

## Part 5 — Submission email (১০ মিনিট)

নিজের Gmail থেকে, Professor Liang Peng-এর আগের Task 1 email-এ **Reply** করো:

```
Subject: Task 1 submission - Windows Code Agent and Space Fractions

Dear Professor Liang,

Please find my Task 1 submission below:

- GitHub repository: https://github.com/shirsha2002/agent-space-fractions
- Windows executables (release): <RELEASE LINK>
- Demonstration video: <YOUTUBE LINK>
- Technical report: https://github.com/shirsha2002/agent-space-fractions/blob/main/docs/technical_report.md

The agent is a Windows desktop application (standalone .exe, no Python required) that reads
Architecture_Documentation.md and Architecture_View.md, calls the official DeepSeek API with
deepseek-v4-pro, generates the project (source, requirements.txt, README and tests), validates it and
performs bounded repairs. The generated Space Fractions game is a desktop application.
Total DeepSeek token cost is below USD 1 (about USD <TOTAL> according to the agent's ledger).

Model outputs, human fixes, limitations and the tools and assistance used are documented in the repository.

Thank you for your time and review.

Best regards,
Shirsha Mitra (寿山)
```

`<RELEASE LINK>`, `<YOUTUBE LINK>`, `<TOTAL>` বদলাতে ভুলবে না। Total দেখতে: agent-এর log-এর শেষের cost summary।
লক্ষ্য: **৬ নভেম্বরের মধ্যে** পাঠানো।

---

## Part 6 — Interview প্রস্তুতি (এই প্রশ্নগুলোর উত্তর নিজের ভাষায় বলতে পারো কিনা দেখো)

| প্রশ্ন | ছোট উত্তর |
| --- | --- |
| Agent-এর loop কী? | plan → generate → write files → validate → repair (max 2) → summary। `src/code_agent/agent.py` |
| AI-এর উত্তর কীভাবে নাও? | strict JSON manifest (file path + content); লেখার আগে schema আর path check |
| Path traversal কীভাবে আটকাও? | absolute path, `..`, drive/UNC path, symlink সব reject — `workspace_tools.py` |
| $1 বাজেট কীভাবে রাখো? | প্রতিটা call-এর আগে worst-case খরচ reserve, ledger SQLite-এ save — `budget.py` |
| Generated code কেন সরাসরি চালাও না? | AI-এর code untrusted; human review বাধ্যতামূলক, তারপর timeout-সহ test |
| Model-এর test ছাড়া আর কী test? | host-এর নিজস্ব independent rule test (fraction ঠিক, score একবার, state) |
| Exe কীভাবে বানালে? | PyInstaller — Python runtime exe-এর ভেতরে bundle করা |
| Cloud architecture কেন বানাওনি? | Teacher desktop চেয়েছেন; local modular design-এ adapt করে deviation document করেছি |
| Fraction কীভাবে check হয়? | Python `fractions.Fraction` — float-এর ভুল এড়াতে exact তুলনা |

বিস্তারিত বাংলায়: `docs/understanding_guide.md`।

---

## Checklist

- [ ] Part 1 প্রস্তুতি শেষ
- [ ] Video রেকর্ড (Scene 1–9)
- [ ] Edit + API key নেই নিশ্চিত + YouTube Unlisted upload
- [ ] GitHub Release v1.0 publish
- [ ] Email পাঠানো (৬ নভেম্বরের মধ্যে)
- [ ] Interview প্রশ্নগুলো অনুশীলন
