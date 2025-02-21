import jieba
import nltk
from nltk.corpus import stopwords
import re
import string

class TextPreprocessor:
    def __init__(self):
        # 下载nltk需要的资源
        try:
            nltk.download('punkt')  # 基础分词器
            nltk.download('punkt_tab')  # punkt标签
            nltk.download('stopwords')  # 停用词
            nltk.download('averaged_perceptron_tagger')  # 词性标注器
        except LookupError as e:
            logger.warning(f"Error downloading NLTK data: {e}")
            
        # 初始化停用词
        self.en_stopwords = set(stopwords.words('english'))
        self.cn_stopwords = set([
            '的', '了', '是', '在', '和', '有', '为', '对', '与', '不', 
            '也', '就', '都', '很', '一个', '这个', '这些', '而', '上', 
            '下', '中', '出', '等', '要', '以', '能', '会', '你', '我',
            '他', '她', '它', '这', '那', '个', '们', '把', '但', '来',
            '去', '说', '看', '将', '到', '着', '从', '并', '及', '或'
        ])
        
        # 初始化jieba
        jieba.initialize()

    def preprocess_text(self, text: str) -> str:
        """
        对中英文混合文本进行预处理
        
        Args:
            text: 输入的文本字符串
            
        Returns:
            处理后的文本字符串
        """
        if not text or not isinstance(text, str):
            return ""
            
        # 1. 基础清洗
        # 转小写、移除标点符号
        text = text.lower()
        text = re.sub(f'[{string.punctuation}]', ' ', text)
        
        # 2. 分词处理
        # 检测文本是否包含中文
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        
        if has_chinese:
            # 对于包含中文的文本，使用jieba分词
            words = jieba.cut(text)
            # 去除停用词(中英文)
            words = [word for word in words 
                    if word.strip() 
                    and word not in self.cn_stopwords 
                    and word not in self.en_stopwords
                    and not word.isspace()
                    and len(word) > 1]  # 去除单字词，提高质量
        else:
            # 纯英文文本使用nltk分词
            words = nltk.word_tokenize(text)
            # 去除停用词(英文)
            words = [word for word in words 
                    if word.strip() 
                    and word not in self.en_stopwords
                    and not word.isspace()
                    and len(word) > 1]
        
        # 3. 后处理
        # 去除数字(可选，取决于具体需求)
        # words = [word for word in words if not word.isdigit()]
        
        # 4. 拼接结果
        return " ".join(words)

    def process_batch(self, texts: list) -> list:
        """批量处理文本"""
        return [self.preprocess_text(text) for text in texts]
