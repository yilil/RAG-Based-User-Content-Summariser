版本 2 – 面向用户（上手手册）

0. 环境要求
Git、Node（LTS）、Python 3.11+
大文件支持：
 # macOS
brew install git-lfs && git lfs install
# Windows / Linux 按官网指引安装 git-lfs

1. 克隆项目
git clone https://github.com/your-org/NextGen-AI.git
cd NextGen-AI
git lfs pull          # 拉取 SQLite 与 FAISS 索引

2. 后端启动
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python set_api_key.py             # 粘贴你的 Gemini Key
python manage.py migrate          # 创建数据库表
python manage.py index_content --source=all   # 首次向量化（约 1 分钟）
python manage.py runserver        # http://127.0.0.1:8000

3. 前端启动
cd Frontend
npm install
npm run dev                       # http://localhost:5173

4. 如何使用
左栏选择平台（Reddit / Stack Overflow / Rednote）与 模型
可选 主题（JavaScript、Travel…）
在输入框键入问题，上方 会出现智能模板，点一下即可自动填充
回车提交，聊天区例子：
 You : Where to eat near USYD?
Bot : 以下是评分最高的五家咖啡馆…
会话自动保存到浏览器，下次打开仍在


5. 常用命令
# 仅重新索引 Reddit
python manage.py index_content --source=reddit

# 若索引损坏，全部删除后重建
rm -rf faiss_index/
python manage.py index_content --source=all



Version 2 – User handbook (clone → run → search)

0. Prerequisites
Mac / Windows / Linux with recent Git & Node (LTS) & Python 3.11+.
If you are on macOS and do not have Homebrew:
 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
Large-file support once (all OS): brew install git-lfs or follow https://git-lfs.com. Then git lfs install.


1. Clone the repo
git clone https://github.com/your-org/NextGen-AI.git
cd NextGen-AI
git lfs pull           # downloads the big SQLite + FAISS files

2. Back-end set-up
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

2.1 Supply your Gemini key
python set_api_key.py             # paste once, it lands in .env

2.2 First-time database & index
python manage.py migrate          # creates tables
python manage.py index_content --source=all   # builds embeddings (~1 min)

2.3 Run Django
python manage.py runserver        # http://127.0.0.1:8000

3. Front-end set-up
cd Frontend
npm install
npm run dev                       # http://localhost:5173
The site automatically talks to the back-end through the proxy; everything works on two tabs.

4. Using the search screen
Pick a platform (Reddit, Stack Overflow, Rednote) and model (gemini-1.5-flash, pro etc.) from the left sidebar
Optionally pick a topic (JavaScript, Travel …)
Click on the search bar and start typing the enquiry; instant question templates will appear above the bar – click to autofill
Press Enter or click the search button on the right side of the search bar. The conversation eg.
You  | What are the best cafés near USYD?
Bot  | Here are five highly-rated spots …
Each new search, it will auto scroll – the newest answer is always in view. Past chats re-open instantly because they are saved in your browser’s local storage.


5. Common commands
Re-index only Reddit after new scrapes
python manage.py index_content --source=reddit

Wipe indexes if something went wrong
rm -rf faiss_index/   # then repeat step 2.2