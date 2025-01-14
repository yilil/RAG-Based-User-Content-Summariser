UI Design Figma Link（Dev mode）：https://www.figma.com/design/1BZN661uSi2y4FKDcd4RgZ/NextGen-AI-(Prototype)?node-id=0-1&m=dev

# Create a virtual environment
```python3 -m venv venv```

# Activate the virtual environment
```source venv/bin/activate  # macOS/Linux```

```venv\Scripts\activate     # Windows```

# Install project dependencies
```pip install -r requirements.txt```

# To setup Gemini API Key
```python set_api_key.py # enter your key``` 

then restart terminal and reactivate the virtual environment
```venv\Scripts\Activate.ps1  # Windows```

# langchain-google-genai Installation
```pip install -U langchain-google-genai```

# Install `scikit-learn` for Similarity Search
```pip install scikit-learn```

# Install Langchain community
```pip install langchain-community```

# 需要设置 Application Default Credentials (ADC)，并添加到环境变量中

# 现在还没法做测试：
因为需要数据库中实际存储了reddit和stackoverflow扒下来的数据才能初始化构建embedding和indexing，从而再在搜索框中测试 -> 是否得到的回答中是否是用了原先提供的Reddit和Stackflow的文档内容，并判断回答的内容是否和query合理匹配

# 后续数据库的数据可以被存储后，可以先按以下操作来：
1. 初始化好环境
2. `python manage.py makemigrations` 数据库迁移
3. `python manage.py runserver`
4. 访问网站 http://127.0.0.1:8000/index_content/ 对当前数据库中内容先初始化一次embedding和indexing (之后跑的时候数据库如果没更新就不用再访问一遍了)
5. 之后就正常访问http://127.0.0.1:8000 即可输入query测试+使用RAG功能

# *注意事项：
因为项目要用到embedding和indexing，所以需要先在google cloude platform上注册账号，并且获得'GOOGLE_APPLICATION_CREDENTIALS'才可以调用，否则没权限，需要完成以下步骤 (具体设备可能会有差异)：
1. 注册google claude账号
2. 创建service account账号并add key，然后获取json文件(有关google cloud功能使用权限)保存在本地 ，并将它添加到系统环境变量中让项目可以识别到这个json文件
3. 在service account上设定自己的Role: 例如 - owner是最高权限调用各种功能和api

# 如果使用bge-en-icl embedding model
1. 首先卸载当前的langchain相关包：
`pip uninstall langchain langchain-community`
2. 然后安装新的依赖：
`pip install sentence-transformers torch transformers`
`pip install langchain langchain-community`

# 测试需要install faker
`pip install faker`

# 测试
`python manage.py test_rag`