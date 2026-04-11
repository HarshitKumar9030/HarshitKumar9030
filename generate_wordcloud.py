import os
import requests
from wordcloud import WordCloud
import matplotlib.pyplot as plt

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
        "state": "all",
        "per_page": 100
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    words = get_local_words()
    
    if response.status_code == 200:
        issues = response.json()
        for issue in issues:
            # Title format: "wordcloud: [your word here]" or similar
            title = issue.get("title", "")
            # we also read body just in case
            body = issue.get("body") or ""
            
            # Simple extraction strategy: assume the body has the word if using the old template format, 
            # but user title input is easiest: 'wordcloud: hello' -> 'hello'
            # Let's clean the string.
            words.extend(title.replace("wordcloud:", "").replace("[your word here]", "").split())
            if "### Word" in body:
                try:
                    extracted = body.split("### Word")[1].split()[0]
                    words.append(extracted)
                except IndexError:
                    pass

    return list(filter(None, words))

def get_local_words():
    if os.path.exists('wordcloud.txt'):
        with open('wordcloud.txt', 'r') as f:
            return f.read().split()
    return ["Awesome", "Code", "GitHub", "Developer", "OpenSource"]

def main():
    words = get_words_from_issues()
    if not words:
        words = ["Awesome", "Code", "GitHub", "Developer", "OpenSource"]

    
    # Save processed words locally to ensure we don't lose anything
    with open('wordcloud.txt', 'w') as f:
        f.write("\n".join(words))

    text = " ".join(words)
    
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='#0D1117', # GitHub dark theme background
        colormap='cool',
        max_words=200,
        contour_width=3,
        contour_color='steelblue'
    ).generate(text)
    
    os.makedirs('images', exist_ok=True)
    wordcloud.to_file('images/wordcloud.png')
    print("Wordcloud generated successfully at images/wordcloud.png")

if __name__ == "__main__":
    main()
