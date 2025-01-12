import pytest
from unittest.mock import Mock, patch
from src.reddit_crawl import get_posts
import json

@pytest.fixture
def mock_post_data():
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Test Post",
                        "author": "test_user",
                        "permalink": "/r/test/comments/123/test_post",
                        "upvote_ratio": 0.95,
                        "selftext": "Test content"
                    }
                }
            ]
        }
    }

@pytest.fixture
def mock_driver():
    driver = Mock()
    element = Mock()
    driver.find_element.return_value = element
    return driver, element

@patch('selenium.webdriver.Chrome')
def test_successful_post_retrieval(mock_chrome, mock_driver, mock_post_data):
    driver, element = mock_driver
    mock_chrome.return_value = driver
    element.text = json.dumps(mock_post_data)
    
    posts = get_posts("test")
    
    assert len(posts) == 1
    post = posts["Test Post"]
    assert post["title"] == "Test Post"
    assert post["author"] == "test_user"
    assert post["permalink"] == "/r/test/comments/123/test_post"
    assert post["upvote_ratio"] == 0.95
    assert post["text"] == "Test content"

@patch('selenium.webdriver.Chrome')
def test_retry_mechanism(mock_chrome, mock_driver):
    driver, element = mock_driver
    mock_chrome.return_value = driver
    
    # First two attempts fail, third succeeds
    element.text = "invalid json"
    posts = get_posts("test", retries=2)
    
    # Verify driver.quit was called 3 times
    assert driver.quit.call_count == 3
    # Should return empty dict on failure
    assert posts == {}

@patch('selenium.webdriver.Chrome')
def test_error_handling(mock_chrome, mock_driver):
    driver, _ = mock_driver
    mock_chrome.return_value = driver
    driver.get.side_effect = Exception("Connection error")
    
    posts = get_posts("test")
    assert posts == {}  # Should return empty dict on error

@patch('selenium.webdriver.Chrome')
def test_empty_response(mock_chrome, mock_driver):
    driver, element = mock_driver
    mock_chrome.return_value = driver
    element.text = json.dumps({"data": {"children": []}})
    
    posts = get_posts("test")
    
    assert len(posts) == 0
    assert driver.quit.called