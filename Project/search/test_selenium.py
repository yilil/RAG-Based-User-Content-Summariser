from selenium import webdriver
import time

def test_selenium():
    # 如果你把 chromedriver 放到 /usr/local/bin 或已在 PATH 中
    # driver = webdriver.Chrome()  
    # 如果不在 PATH，则需要指定 executable_path：
    # driver = webdriver.Chrome(executable_path="/绝对路径/chromedriver")

    driver = webdriver.Chrome()
    driver.get("https://www.google.com")
    time.sleep(2)  # 等2秒，页面加载
    print("Page title is:", driver.title)
    driver.quit()

if __name__ == "__main__":
    test_selenium()
