import os
import re
import random
import pathlib
import requests
from wordcloud import WordCloud


DEFAULT_WORDS = ["Awesome", "Code", "GitHub", "Developer", "OpenSource"]
FONT_PATH = "fonts/Poppins-Bold.ttf"
WORD_COLORS = [
    "#8A0B3C", "#C81D4E", "#641E47", "#D11448", "#B71B47", "#4E193C",
    "#800080", "#8B008B", "#C71585", "#E60049", "#8B0000", "#6B1B3D",
    "#DC143C", "#CD5C5C"
]

def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    # Palette matched to the reference image.
    return random.choice(WORD_COLORS)


def normalize_words(raw_text):
    candidates = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", raw_text or "")
    blocked = {
        "wordcloud", "your", "word", "here", "e", "g", "add",
        "submit", "issue", "template"
    }
    cleaned = []
    for token in candidates:
        lower = token.lower()
        if lower in blocked:
            continue
        cleaned.append(token)
    return cleaned


def unique_words(words):
    seen = set()
    deduped = []
    for word in words:
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(word)
    return deduped


def extract_words_from_issue(issue):
    title = issue.get("title") or ""
    body = issue.get("body") or ""

    words = []

    # Handle title format like: wordcloud: myword
    title_parts = title.split(":", 1)
    if len(title_parts) == 2 and "wordcloud" in title_parts[0].lower():
        words.extend(normalize_words(title_parts[1]))
    else:
        words.extend(normalize_words(title))

    # Issue form body usually contains a "### Word" section.
    section_match = re.search(r"###\s*Word\s*(.*?)(?:\n###|\Z)", body, flags=re.IGNORECASE | re.DOTALL)
    if section_match:
        words.extend(normalize_words(section_match.group(1)))
    else:
        words.extend(normalize_words(body))

    return words


def close_issue_with_comment(repo, issue_number, headers):
    comment_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    requests.post(
        comment_url,
        headers=headers,
        json={"body": "Tada! Your word has been added to the wordcloud."},
        timeout=20,
    )

    close_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    requests.patch(close_url, headers=headers, json={"state": "closed"}, timeout=20)


def get_event_issue_if_any():
    event_name = os.getenv("GITHUB_EVENT_NAME")
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_name not in {"issues", "issue_comment"} or not event_path:
        return None

    try:
        import json
        with open(event_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None

    issue = payload.get("issue")
    if not isinstance(issue, dict):
        return None

    labels = [label.get("name", "").lower() for label in issue.get("labels", []) if isinstance(label, dict)]
    body = (issue.get("body") or "").lower()
    title = (issue.get("title") or "").lower()

    is_wordcloud_issue = "wordcloud" in labels or "wordcloud" in title or "### word" in body
    return issue if is_wordcloud_issue else None


def ensure_poppins_font():
    font_file = pathlib.Path(FONT_PATH)
    font_file.parent.mkdir(parents=True, exist_ok=True)
    if font_file.exists():
        return str(font_file)

    url = "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(font_file, "wb") as handle:
        handle.write(response.content)
    return str(font_file)

def get_words_from_issues():
    github_token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPOSITORY')
    if not repo:
        print("GITHUB_REPOSITORY not set. Using local file if exists.")
        return get_local_words()

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    params = {
        "labels": "wordcloud",
        "state": "open",
        "per_page": 100
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)

    words = get_local_words()

    event_issue = get_event_issue_if_any()
    if event_issue:
        extracted = extract_words_from_issue(event_issue)
        words.extend(extracted)
        issue_number = event_issue.get("number")
        if github_token and issue_number:
            close_issue_with_comment(repo, issue_number, headers)
    
    if response.status_code == 200:
        issues = response.json()
        for issue in issues:
            issue_number = issue.get("number")
            words.extend(extract_words_from_issue(issue))

            # Avoid duplicate close/comment if we already handled current event issue above.
            if event_issue and issue_number == event_issue.get("number"):
                continue
            if github_token and issue_number:
                close_issue_with_comment(repo, issue_number, headers)

    return unique_words(list(filter(None, words)))

def get_local_words():
    if os.path.exists('wordcloud.txt'):
        with open('wordcloud.txt', 'r', encoding='utf-8') as f:
            return f.read().split()
    return DEFAULT_WORDS

def main():
    words = get_words_from_issues()
    if not words:
        words = DEFAULT_WORDS
    words = unique_words(words)

    # Save processed words locally
    with open('wordcloud.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(words))

    text = " ".join(words)
    font_path = ensure_poppins_font()
    
    # Tight layout with bold Poppins and white background.
    wordcloud = WordCloud(
        width=1600,
        height=900,
        background_color='white',
        color_func=color_func,
        max_words=600,
        font_step=2,
        max_font_size=220,
        font_path=font_path,
        margin=1,
        repeat=False,
        collocations=False,
        relative_scaling=0.15,
        random_state=42,
        prefer_horizontal=0.95,
        scale=2,
    ).generate(text)
    
    os.makedirs('images', exist_ok=True)
    wordcloud.to_file('images/wordcloud.png')
    print("Wordcloud generated successfully at images/wordcloud.png")

if __name__ == "__main__":
    main()
