import json
import csv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException


def setup_webdriver(headless=True) -> webdriver.Chrome:
    """Set up the WebDriver with optional headless mode and user-agent spoofing.

    Returns:
        webdriver.Chrome: The configured WebDriver instance
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)


def get_posts(feed, retries=3, timeout=10, single=False) -> dict:
    """Get posts from a Reddit feed.

    Args:
        feed (str): The name of the Reddit feed to crawl
        retries (int): The number of retries to attempt if the request fails
        timeout (int): The timeout for the request in seconds
        single (bool): If True, only return the first post

    Returns:
        dict: A dictionary of posts with their metadata
    """
    tries = 0
    success = False
    posts = {}  # Initialize posts dictionary outside try block

    while tries <= retries and not success:
        driver = setup_webdriver()
        try:
            url = f"https://www.reddit.com/r/{feed}.json"
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            json_data = driver.find_element(By.TAG_NAME, 'pre').text
            response = json.loads(json_data)

            if response:
                success = True
                list_of_posts = response['data']['children']
                if single and list_of_posts:  # If single mode, only process the first post
                    list_of_posts = [list_of_posts[0]]
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
        except (WebDriverException, json.JSONDecodeError, KeyError) as e:
            print(f"An error occurred: {e}")
        finally:
            driver.quit()
        tries += 1

    return posts


def parse_text(text: str) -> str:
    """Parse text to remove unwanted characters and whitespace.

    Args:
        text (str): The text to parse

    Returns:
        str: The parsed text
    """
    text = text.replace('\n', ' ')
    text = text.replace('\\', ' ')
    return text


def write_to_csv(posts: dict, filename: str):
    """Write post data to a CSV file.

    Args:
        posts (dict): A dictionary of posts with their metadata
        filename (str): The name of the file to write to

    Returns:
        None
    """
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(
            ['Title', 'Author', 'Permalink', 'Upvote Ratio', 'Text'])
        for post in posts.values():
            writer.writerow([
                post['title'],
                post['author'],
                post['permalink'],
                post['upvote_ratio'],
                post['text']
            ])


def main():
    """Main function to execute the Reddit crawling and CSV writing process."""
    feed = 'tifu'
    posts = get_posts(feed)
    posts = {k: {**v, 'text': parse_text(v['text'])} for k, v in posts.items()}
    write_to_csv(posts, f'{feed}_posts.csv')


if __name__ == '__main__':
    main()
