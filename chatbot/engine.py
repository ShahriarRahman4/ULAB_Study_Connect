from __future__ import annotations

import http.client
import json
import os
import re
import socket
import ssl
import urllib.parse
from typing import List, Tuple

from django.conf import settings
from django.utils.html import escape


SYSTEM_PROMPT = """You are Nova, the premium AI study tutor for ULAB StudyConnect
(University of Liberal Arts Bangladesh). Be warm, concise, and exam-practical.

You can help with:
- Exam routines, study planner, notes, PDFs, forum
- Active recall, spaced repetition, time boxing
- Course concepts (especially CSE: algorithms, databases, discrete math)
- Campus study tips for ULAB students

Never invent official exam dates. Point students to Exam Routines in StudyConnect.
Use short paragraphs and bullets. If a question is unclear, ask one clarifying question.
You may use light Markdown (## headings, - bullets, **bold**). Keep replies scannable.
"""


def reply(message: str, history: List[dict]) -> dict:
    text = (message or "").strip()
    if not text:
        return {
            "reply": "Ask me anything about studying, ULAB courses, or how to use StudyConnect.",
            "source": "nova",
        }

    remote, err = _try_remote(text, history)
    if remote:
        return {"reply": remote, "source": "model"}
    if err:
        return {
            "reply": (
                "Nova could not reach ChatGPT just now. "
                "Check the OpenAI API key in `.env` and restart the server.\n\n"
                f"Details: {err}"
            ),
            "source": "error",
        }

    return {"reply": _local_tutor(text), "source": "nova"}


def markdown_to_html(text: str) -> str:
    """Render light Markdown as safe HTML so chat does not show ### / ** raw."""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""

    def inline(s: str) -> str:
        s = escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"__(.+?)__", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    lines = raw.split("\n")
    out: list[str] = []
    in_ul = False
    in_ol = False
    para: list[str] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def flush_para() -> None:
        if para:
            out.append("<p>" + "<br>".join(inline(p) for p in para) + "</p>")
            para.clear()

    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        ul = re.match(r"^\s*[-*]\s+(.+)$", line)
        ol = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if heading:
            flush_para()
            close_lists()
            level = min(len(heading.group(1)), 3)
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif ul:
            flush_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(ul.group(1))}</li>")
        elif ol:
            flush_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(ol.group(1))}</li>")
        elif not line.strip():
            flush_para()
            close_lists()
        else:
            close_lists()
            para.append(line)
    flush_para()
    close_lists()
    return "".join(out)


def _try_remote(message: str, history: List[dict]) -> Tuple[str, str]:
    openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "").strip()
    groq_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "").strip()

    if openai_key:
        return _openai_compat(
            url="https://api.openai.com/v1/chat/completions",
            api_key=openai_key,
            model=getattr(settings, "OPENAI_MODEL", None) or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            message=message,
            history=history,
        )
    if groq_key:
        return _openai_compat(
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=groq_key,
            model=getattr(settings, "GROQ_MODEL", None) or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
            message=message,
            history=history,
        )
    return "", ""


def _openai_compat(url: str, api_key: str, model: str, message: str, history: List[dict]) -> Tuple[str, str]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    models_to_try = [model]
    for fallback in ("gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"):
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    last_err = ""
    for current_model in models_to_try:
        payload = json.dumps({
            "model": current_model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 700,
        }).encode("utf-8")
        status, body, net_err = _https_post_json(url, api_key, payload)
        if net_err:
            last_err = net_err
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            last_err = f"HTTP {status}: invalid JSON from the AI API."
            continue
        if status >= 400:
            err = (data.get("error") or {}).get("message") or body[:300]
            last_err = f"HTTP {status}: {err}"
            if status in (404, 400) and "model" in str(err).lower():
                continue
            return "", last_err
        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return "", "Unexpected response from the AI API."
        return content, ""
    return "", last_err or "Could not reach the AI API."


def _https_post_json(url: str, api_key: str, payload: bytes) -> Tuple[int, str, str]:
    """POST JSON without HTTP(S)_PROXY — urllib tunnels often return 403 in Cursor/VPN."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "api.openai.com"
    path = parsed.path or "/v1/chat/completions"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    port = parsed.port or 443
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ULAB-StudyConnect-Nova/1.0",
        "Connection": "close",
    }
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        ip = infos[0][4][0]
        context = ssl.create_default_context()
        raw = socket.create_connection((ip, port), timeout=45)
        tls = context.wrap_socket(raw, server_hostname=host)
        conn = http.client.HTTPSConnection(host, port=port, timeout=45, context=context)
        conn.sock = tls
        conn.request("POST", path, body=payload, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        status = resp.status
        conn.close()
        return status, body, ""
    except TimeoutError:
        return 0, "", "The AI request timed out."
    except OSError as exc:
        return 0, "", str(exc) or "Network error talking to the AI API."


def _local_tutor(text: str) -> str:
    q = text.lower().strip()

    if re.search(r"\b(hi|hello|hey|salam|assalam|yo)\b", q) and len(q) < 40:
        return (
            "Hey — I'm **Nova**, your StudyConnect tutor.\n\n"
            "I can help you:\n"
            "- Plan finals with the study planner\n"
            "- Find notes and summarize lectures\n"
            "- Explain algorithms, databases, and exam tactics\n\n"
            "What are you studying this week?"
        )

    if any(k in q for k in ("who are you", "your name", "what can you", "help me use")):
        return (
            "I'm **Nova**, the AI tutor inside ULAB StudyConnect.\n\n"
            "**Quick map of the platform**\n"
            "- **Routines** — official exam schedule, filter by course/section\n"
            "- **Planner** — generate a day-by-day plan from a saved routine\n"
            "- **Notes** — write, share publicly, attach PDFs, summarize & quiz\n"
            "- **Forum** — ask course questions the whole campus can find\n\n"
            "Tell me a course code (like CSE 310) or a topic."
        )

    if any(k in q for k in ("routine", "exam date", "exam schedule", "finals")):
        return (
            "Exam dates live in **Exam Routines**, not in chat — I won't guess official dates.\n\n"
            "Do this:\n"
            "1. Open **Routines** and find the active schedule\n"
            "2. Filter by your course code + section\n"
            "3. Save it, then open **Study Planner** and generate hours-per-day blocks\n\n"
            "Want a 7-day sprint template if you already know your first exam date?"
        )

    if any(k in q for k in ("planner", "study plan", "schedule my", "how many hours")):
        return (
            "**Build a plan that survives finals week**\n"
            "- Save your routine first\n"
            "- Set honest hours (4h/day beats a fake 10h plan)\n"
            "- Weight harder courses closer to their exam\n"
            "- Keep one recovery block every 3 days\n\n"
            "A simple split: 50% nearest exam, 30% hardest remaining course, 20% light review.\n"
            "Open **Study Planner** and generate from your saved routine."
        )

    if any(k in q for k in ("note", "pdf", "summar", "quiz", "cheatsheet")):
        return (
            "**Notes that actually get used**\n"
            "- Write in **My Notes**; mark public if classmates should find it\n"
            "- Attach a PDF for slides\n"
            "- Use **Summarize** for a 5-bullet pass, then **Quiz** for active recall\n\n"
            "Best note structure: definition → example → exam trap → 1 practice question.\n"
            "Want me to turn a topic into that template? Paste the topic."
        )

    if any(k in q for k in ("forum", "ask a question", "community")):
        return (
            "On the **Forum**, posts that get answers usually include:\n"
            "- Course code (CSE 310, CSE 311…)\n"
            "- What you already tried\n"
            "- The exact formula, error, or recurrence\n\n"
            "Search first so you don't duplicate a thread. I can help you draft a question — paste the problem."
        )

    if any(k in q for k in ("pomodoro", "focus", "procrastinat", "can't study", "cant study")):
        return (
            "**If starting is the hard part**\n"
            "- 25 min work / 5 min off (Pomodoro) — phone in another room\n"
            "- First 2 minutes: only open the notes, no 'perfect plan'\n"
            "- End each block by writing the *next* tiny action\n\n"
            "ULAB library 3rd floor fills before finals — book a quieter room or pair with one person, not a group of eight."
        )

    if any(k in q for k in ("spaced", "active recall", "how to memorize", "revision")):
        return (
            "**Memory that lasts past the exam**\n"
            "- **Active recall**: close the notes, write the idea from memory, then check\n"
            "- **Spaced repetition**: same topic after 1 day, 3 days, 7 days\n"
            "- Don't highlight whole PDFs — turn each heading into a question\n\n"
            "Tonight: 20 minutes recall, 10 minutes mistakes log. Tomorrow: only the mistakes."
        )

    if any(k in q for k in ("merge sort", "master theorem", "time complexity", "recurrence")):
        return (
            "**Merge sort & Master Theorem (exam-ready)**\n\n"
            "Merge sort splits the array in half (`T(n/2)` twice) then merges in linear time (`O(n)`):\n"
            "`T(n) = 2T(n/2) + Θ(n)`\n\n"
            "Master Theorem case 2 (a = 2, b = 2, f(n) = n, log_b a = 1):\n"
            "since f(n) = Θ(n^{log_b a}), **T(n) = Θ(n log n)**.\n\n"
            "Trap: if you forget the merge cost and write only `2T(n/2)`, you get the wrong case.\n"
            "Want a 4-line proof sketch or a comparison with heap sort?"
        )

    if any(k in q for k in ("bcnf", "3nf", "normal form", "normalization")):
        return (
            "**3NF vs BCNF — quick tell**\n"
            "- **3NF**: no non-prime attribute depends on another non-prime (no transitive junk)\n"
            "- **BCNF**: *every* determinant is a candidate key\n\n"
            "A relation can be 3NF but not BCNF when a *prime* attribute depends on something that isn't a key.\n"
            "Exam move: list candidate keys first, then check every functional dependency's left side.\n\n"
            "Paste your FDs if you want them classified."
        )

    if any(k in q for k in ("recursion", "base case", "fibonacci")):
        return (
            "**Recursion**\n"
            "A recursive function needs:\n"
            "1. **Base case** — stops the calls\n"
            "2. **Progress** — input gets smaller\n"
            "3. **Combine** — use the returned value\n\n"
            "Naive Fibonacci is slow because it recomputes overlapping subproblems — memoize or iterate.\n"
            "Want a trace of `fact(4)` or a tree for `fib(5)`?"
        )

    if any(k in q for k in ("sql join", "inner join", "left join")):
        return (
            "**SQL joins**\n"
            "- **INNER**: only matching keys\n"
            "- **LEFT**: all left rows; unmatched right columns are NULL\n"
            "- **RIGHT**: mirror of left\n"
            "- **FULL**: both sides, NULLs where no match\n\n"
            "Interview trap: `WHERE right.id IS NULL` after a LEFT JOIN finds left rows with no match."
        )

    if any(k in q for k in ("graph", "bfs", "dfs", "shortest path", "dijkstra")):
        return (
            "**Graphs (CSE 203 / 310)**\n"
            "- **BFS**: shortest path in unweighted graphs; queue\n"
            "- **DFS**: connectivity, cycles, topological order; stack/recursion\n"
            "- **Dijkstra**: non-negative weighted shortest path\n\n"
            "If edges can be negative, Dijkstra is wrong — use Bellman-Ford.\n"
            "Tell me the exact problem (trace, complexity, or code sketch)."
        )

    if any(k in q for k in ("ulab", "campus", "library", "hackathon")):
        return (
            "StudyConnect is built **for ULAB students** — routines, notes, planner, forum, and me (Nova).\n\n"
            "Campus reality: group chats bury answers; this platform keeps them searchable.\n"
            "If you're here for Hackathon 2026, the product story is: one academic hub, not ten tabs.\n\n"
            "What do you need first — a study block, a note template, or a forum draft?"
        )

    if any(k in q for k in ("stress", "anxious", "burnout", "sleep")):
        return (
            "Exam stress is normal. Protect the basics: sleep, water, one real meal.\n\n"
            "A calmer evening: 45 min of *known* weak topics, not new chapters at 1am.\n"
            "If you're overwhelmed, pick **one** course and one past question — finish that, then stop.\n\n"
            "I'm here for the academic part. If you need real counseling, use campus support services."
        )

    topic = text.strip()[:80]
    return (
        "Let's treat **{topic}** like an exam question.\n\n"
        "1. **Define it** in one sentence\n"
        "2. **One example** (numbers or a tiny case)\n"
        "3. **Common trap** students miss\n"
        "4. **One practice prompt** to test yourself\n\n"
        "Reply with the course code (e.g. CSE 310) and whether you want a definition, a worked example, or a quiz."
    ).format(topic=topic)
