import jieba
import nltk
from nltk.corpus import stopwords
import re
import string
import os # 用于加载停用词表

# 定义停用词表文件路径 (假设放在 text_preprocessor.py 同目录下)
STOPWORDS_PATH = os.path.join(os.path.dirname(__file__), 'stopwords.txt')

class TextPreprocessor:
    def __init__(self):
        # 下载nltk需要的资源
        try:
            nltk.download('punkt')  # 基础分词器
            nltk.download('punkt_tab')  # punkt标签
            nltk.download('stopwords')  # 停用词
            nltk.download('averaged_perceptron_tagger')  # 词性标注器
        except LookupError as e:
            print(f"Warning: Error downloading NLTK data: {e}")
            
        # 初始化英文停用词 - 先获取NLTK基础停用词，然后添加570个词
        base_en_stopwords = set(stopwords.words('english'))
        
        # 添加570个英文停用词，但排除单个字母
        additional_en_stopwords = set([
            "a's", "able", "about", "above", "according", "accordingly", "across", "actually", "after", 
            "afterwards", "again", "against", "ain't", "all", "allow", "allows", "almost", "alone", "along", 
            "already", "also", "although", "always", "am", "among", "amongst", "an", "and", "another", "any", 
            "anybody", "anyhow", "anyone", "anything", "anyway", "anyways", "anywhere", "apart", "appear", 
            "appreciate", "appropriate", "are", "aren't", "around", "as", "aside", "ask", "asking", "associated", 
            "at", "available", "away", "awfully", "be", "became", "because", "become", "becomes", "becoming", 
            "been", "before", "beforehand", "behind", "being", "believe", "below", "beside", "besides", "best", 
            "better", "between", "beyond", "both", "brief", "but", "by", "c'mon", "c's", "came", "can", 
            "can't", "cannot", "cant", "cause", "causes", "certain", "certainly", "changes", "clearly", "co", 
            "com", "come", "comes", "concerning", "consequently", "consider", "considering", "contain", "containing", 
            "contains", "corresponding", "could", "couldn't", "course", "currently", "definitely", "described", 
            "despite", "did", "didn't", "different", "do", "does", "doesn't", "doing", "don't", "done", "down", 
            "downwards", "during", "each", "edu", "eg", "eight", "either", "else", "elsewhere", "enough", 
            "entirely", "especially", "et", "etc", "even", "ever", "every", "everybody", "everyone", "everything", 
            "everywhere", "ex", "exactly", "example", "except", "far", "few", "fifth", "first", "five", 
            "followed", "following", "follows", "for", "former", "formerly", "forth", "four", "from", "further", 
            "furthermore", "get", "gets", "getting", "given", "gives", "go", "goes", "going", "gone", "got", 
            "gotten", "greetings", "had", "hadn't", "happens", "hardly", "has", "hasn't", "have", "haven't", 
            "having", "he", "he's", "hello", "help", "hence", "her", "here", "here's", "hereafter", "hereby", 
            "herein", "hereupon", "hers", "herself", "hi", "him", "himself", "his", "hither", "hopefully", "how", 
            "howbeit", "however", "i'd", "i'll", "i'm", "i've", "ie", "if", "ignored", "immediate", "in", 
            "inasmuch", "inc", "indeed", "indicate", "indicated", "indicates", "inner", "insofar", "instead", 
            "into", "inward", "is", "isn't", "it", "it'd", "it'll", "it's", "its", "itself", "just", 
            "keep", "keeps", "kept", "know", "known", "knows", "last", "lately", "later", "latter", "latterly", 
            "least", "less", "lest", "let", "let's", "like", "liked", "likely", "little", "look", "looking", 
            "looks", "ltd", "mainly", "many", "may", "maybe", "me", "mean", "meanwhile", "merely", "might", 
            "more", "moreover", "most", "mostly", "much", "must", "my", "myself", "name", "namely", "nd", 
            "near", "nearly", "necessary", "need", "needs", "neither", "never", "nevertheless", "new", "next", 
            "nine", "no", "nobody", "non", "none", "noone", "nor", "normally", "not", "nothing", "novel", "now", 
            "nowhere", "obviously", "of", "off", "often", "oh", "ok", "okay", "old", "on", "once", "one", 
            "ones", "only", "onto", "or", "other", "others", "otherwise", "ought", "our", "ours", "ourselves", 
            "out", "outside", "over", "overall", "own", "particular", "particularly", "per", "perhaps", 
            "placed", "please", "plus", "possible", "presumably", "probably", "provides", "que", "quite", 
            "qv", "rather", "rd", "re", "really", "reasonably", "regarding", "regardless", "regards", 
            "relatively", "respectively", "right", "said", "same", "saw", "say", "saying", "says", "second", 
            "secondly", "see", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self", "selves", "sensible", 
            "sent", "serious", "seriously", "seven", "several", "shall", "she", "should", "shouldn't", "since", 
            "six", "so", "some", "somebody", "somehow", "someone", "something", "sometime", "sometimes", "somewhat", 
            "somewhere", "soon", "sorry", "specified", "specify", "specifying", "still", "sub", "such", "sup", 
            "sure", "t's", "take", "taken", "tell", "tends", "th", "than", "thank", "thanks", "thanx", 
            "that", "that's", "thats", "the", "their", "theirs", "them", "themselves", "then", "thence", "there", 
            "there's", "thereafter", "thereby", "therefore", "therein", "theres", "thereupon", "these", "they", 
            "they'd", "they'll", "they're", "they've", "think", "third", "this", "thorough", "thoroughly", "those", 
            "though", "three", "through", "throughout", "thru", "thus", "to", "together", "too", "took", "toward", 
            "towards", "tried", "tries", "truly", "try", "trying", "twice", "two", "un", "under", "unfortunately", 
            "unless", "unlikely", "until", "unto", "up", "upon", "us", "use", "used", "useful", "uses", "using", 
            "usually", "uucp", "value", "various", "very", "via", "viz", "vs", "want", "wants", "was", 
            "wasn't", "way", "we", "we'd", "we'll", "we're", "we've", "welcome", "well", "went", "were", "weren't", 
            "what", "what's", "whatever", "when", "whence", "whenever", "where", "where's", "whereafter", "whereas", 
            "whereby", "wherein", "whereupon", "wherever", "whether", "which", "while", "whither", "who", "who's", 
            "whoever", "whole", "whom", "whose", "why", "will", "willing", "wish", "with", "within", "without", 
            "won't", "wonder", "would", "wouldn't", "yes", "yet", "you", "you'd", "you'll", "you're", 
            "you've", "your", "yours", "yourself", "yourselves", "zero"
        ])
        
        # 合并NLTK基础停用词和额外的英文停用词
        self.en_stopwords = base_en_stopwords.union(additional_en_stopwords)
        
        # 初始化中文停用词 - 先定义基础中文停用词，然后加载文件中的中文停用词
        base_cn_stopwords = set([
            '的', '了', '是', '在', '和', '有', '为', '对', '与', '不', 
            '也', '就', '都', '很', '一个', '这个', '这些', '而', '上', 
            '下', '中', '出', '等', '要', '以', '能', '会', '你', '我',
            '他', '她', '它', '这', '那', '个', '们', '把', '但', '来',
            '去', '说', '看', '将', '到', '着', '从', '并', '及', '或'
        ])
        
        # 从文件加载中文停用词并合并
        file_cn_stopwords = self._load_chinese_stopwords(STOPWORDS_PATH)
        self.cn_stopwords = base_cn_stopwords.union(file_cn_stopwords)
        
        # 初始化jieba
        jieba.initialize()

        print(f"--- [TextPreprocessor.__init__] Initializing TextPreprocessor ---")
        print(f"--- [TextPreprocessor.__init__] English stopwords: {len(self.en_stopwords)} words (NLTK: {len(base_en_stopwords)}, Additional: {len(additional_en_stopwords)}) ---")
        print(f"--- [TextPreprocessor.__init__] Chinese stopwords: {len(self.cn_stopwords)} words (Base: {len(base_cn_stopwords)}, File: {len(file_cn_stopwords)}) ---")
        try:
            list(jieba.cut("测试jieba加载"))
            print("--- [TextPreprocessor.__init__] jieba loaded successfully. ---")
        except Exception as e:
            print(f"!!! [TextPreprocessor.__init__] Error loading jieba: {e}")

    def _load_chinese_stopwords(self, filepath):
        """从文件加载中文停用词列表"""
        stopwords = set()
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word:  # 只添加非空词
                            stopwords.add(word)
                print(f"--- [TextPreprocessor._load_chinese_stopwords] Loaded {len(stopwords)} Chinese stopwords from {filepath} ---")
            else:
                print(f"--- [TextPreprocessor._load_chinese_stopwords] Warning: Stopwords file not found at {filepath} ---")
        except Exception as e:
            print(f"!!! [TextPreprocessor._load_chinese_stopwords] Error loading stopwords from {filepath}: {e}")
        return stopwords

    def _load_stopwords(self, filepath):
        """从文件加载停用词列表 - 已弃用，保留兼容性"""
        return self._load_chinese_stopwords(filepath)

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
            # 分别处理中文和英文词汇
            filtered_words = []
            for word in words:
                if not word.strip() or word.isspace() or len(word) <= 1:
                    continue
                
                # 检查是否为中文词汇
                is_chinese_word = bool(re.search(r'[\u4e00-\u9fff]', word))
                
                if is_chinese_word:
                    # 中文词汇使用中文停用词
                    if word not in self.cn_stopwords:
                        filtered_words.append(word)
                else:
                    # 英文词汇使用英文停用词
                    if word not in self.en_stopwords:
                        filtered_words.append(word)
            
            words = filtered_words
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
