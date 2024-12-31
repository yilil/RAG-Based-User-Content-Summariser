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

# Install langchain_community and faiss-cpu python packages
```pip install -qU langchain_community faiss-cpu langchain-gemini```
