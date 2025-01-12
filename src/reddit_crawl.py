from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import csv

def setup_webdriver(headless=True) -> webdriver.Chrome:
    """Set up the WebDriver with optional headless mode and user-agent spoofing."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

def get_posts(feed, retries=3, timeout=10) -> dict:
    tries = 0
    success = False
    posts = {}  # Initialize posts dictionary outside try block

    while tries <= retries and not success:
        driver = setup_webdriver()
        try:
            url = f"https://www.reddit.com/r/{feed}.json"
            driver.get(url)
            json_data = driver.find_element(By.TAG_NAME, 'pre').text
            response = json.loads(json_data)

            if response:
                success = True
                list_of_posts = response['data']['children']
                for post in list_of_posts:
                    data = post['data']
                    title = data['title']
                    author = data['author']
                    permalink = data['permalink']
                    upvote_ratio = data['upvote_ratio']
                    text = data['selftext']
                    posts[title] = {
                        'title': title,
                        'author': author,
                        'permalink': permalink,
                        'upvote_ratio': upvote_ratio,
                        "text": text
                    }
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            driver.quit()
        tries += 1

    return posts

def parse_text(text: str) -> str:
    """Parse text to remove unwanted characters and whitespace."""    
    text = text.replace('\n', ' ')
    text = text.replace('\\', ' ')
    return text

def write_to_csv(posts: dict, filename: str):
    """Write post data to a CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Author', 'Permalink', 'Upvote Ratio', 'Text'])
        for post in posts.values():
            writer.writerow([
                post['title'],
                post['author'], 
                post['permalink'],
                post['upvote_ratio'],
                post['text']
            ])

def main():
    feed = 'tifu'
    posts = get_posts(feed)
    posts = {k: {**v, 'text': parse_text(v['text'])} for k, v in posts.items()}
    write_to_csv(posts, f'{feed}_posts.csv')

if __name__ == '__main__':
    main()