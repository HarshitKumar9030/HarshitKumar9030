import os
import requests
from wordcloud import WordCloud
import random

def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    # Matches the beautiful colors in the provided image (maroons, dark reds, purples, pinks)
    colors = ['#8A0B3C', '#C81D4E', '#641E47', '#D11448', '#B71B47', '#4E193C', '#800080', '#8B008B', '#C71585', '#E60049', '#8B0000', '#6B1B3D', '#DC143C', '#CD5C5C']
    return random.choice(colors)

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
    
    response = requests.get(url, headers=headers, params=params)
    
    words = get_local_words()
    
    if response.status_code == 200:
        issues = response.json()
        for issue in issues:
            title = issue.get("title", "")
            body = issue.get("body") or ""
            issue_number = issue.get("number")
            
            new_words = []
            
            # Extract word from title if possible
            if "wordcloud" in title.lower():
                parts = title.split(":")
                if len(parts) > 1:
                    extracted = parts[1].replace("[your word here]", "").strip()
                    if extracted:
                        new_words.extend(extracted.split())
            else:
                new_words.extend(title.strip().split())

            # Extract word from issue body (template)
            if "### Word" in body:
                try:
                    # Extracts after "### Word" and before next "###" or ends
                    # Gets the first non-empty word in that section
                    lines = body.split("### Word")[1].split("###")[0].strip().splitlines()
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line and clean_line != "e.g. Awesome" and not clean_line.startswith("_"):
                            new_words.extend(clean_line.split())
                            break
                except IndexError:
                    pass

            words.extend(new_words)
            
            # Programmatically close the issue and leave comment
            if github_token and issue_number:
                # Leave a comment on the issue
                comment_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
                requests.post(comment_url, headers=headers, json={"body": 'Tada! Your word has been added to the wordcloud. Check out the updated image on my profile README!'})

                # Close the issue
                close_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
                requests.patch(close_url, headers=headers, json={"state": "closed"})

    return list(filter(None, words))

def get_local_words():
    if os.path.exists('wordcloud.txt'):
        with open('wordcloud.txt', 'r', encoding='utf-8') as f:
            return f.read().split()
    return ["Awesome", "Code", "GitHub", "Developer", "OpenSource"]

def main():
    words = get_words_from_issues()
    if not words:
        words = ["Awesome", "Code", "GitHub", "Developer", "OpenSource"]

    # Save processed words locally
    with open('wordcloud.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(words))

    text = " ".join(words)
    
    # Generate the beautiful wordcloud based on image requirements
    # High resolution, white background, custom maroon/purple colorings
    wordcloud = WordCloud(
        width=1000, 
        height=800, 
        background_color='white',
        color_func=color_func,
        max_words=300,
        font_step=2,
        max_font_size=180,
        random_state=42,
        prefer_horizontal=0.7,
        scale=2 # makes image high resolution and sharp
    ).generate(text)
    
    os.makedirs('images', exist_ok=True)
    wordcloud.to_file('images/wordcloud.png')
    print("Wordcloud generated successfully at images/wordcloud.png")

if __name__ == "__main__":
    main()
