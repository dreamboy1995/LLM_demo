import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings  # DeepSeek API 目前不支持 embeddings 接口
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 1.加载文档
print("正在加载文档...")
loader = TextLoader(file_path="data/readme_sample.md", encoding="utf-8")
docs = loader.load()
print(f'加载了 {len(docs)} 个文档对象')

# 2.切割文档
# RecursiveCharacterTextSplitter 按段落、句子、字符的优先级递归切割
text_spilitter = RecursiveCharacterTextSplitter(
    chunk_size=200,  # 每个文本块最大200个字符
    chunk_overlap=50,  # 相邻块重叠50个字符，保证语义连续性
    separators=["\n\n", "\n", "。", ".", " ", ""]  # 切割符优先级
)
chunks = text_spilitter.split_documents(docs)
print(f'切割成 {len(chunks)} 个文本块')
for i, chunk in enumerate(chunks):
    print(f'文本块 {i + 1}:\n{chunk.page_content[:100]}\n...')

# 3. 向量化并存储到 Chroma
print("\n正在向量化并存入 Chroma...")
embeddings = HuggingFaceEmbeddings(
    model_name="shibing624/text2vec-base-chinese",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
vectordb = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"  # 持久化到本地目录
)
print(f'已将 {vectordb._collection.count()} 个文本块存入向量库')

# 4. 测试检索
print("\n=== 测试语义检索 ===")
query = "什么是Agent的核心组件？"
results = vectordb.similarity_search(query, k=2)
for i, doc in enumerate(results):
    print(f'\n====检索结果{i + 1}：')
    print(f' {doc.page_content}')
