# 测试代码
import torch
print("torch version:", torch.__version__)
print("torch cuda version:", torch.version.cuda)
print("is_available:", torch.cuda.is_available())
print("build:", torch.__config__.show())

# # 删除chroma_db中的数据
# import chromadb
# from pathlib import Path
# BASE_DIR = Path(__file__).resolve().parent
# # 业务数据统一放到 data 目录，便于 Windows 下管理与备份
# DATA_DIR = BASE_DIR / "data"
# CHROMA_PATH = DATA_DIR / "vector_store"  # 文件夹2：向量库持久化

# # 1. 初始化客户端
# # 注意：path="./your_db_path" 必须是你之前保存数据的文件夹路径
# # 如果你之前没有指定 path，是在内存中运行的，重启程序后数据会自动消失，不需要删除。
# client =  chromadb.PersistentClient(path=str(CHROMA_PATH))

# # 2. 检查 Collection 是否存在 (可选，但在删除前确认是个好习惯)
# collections = client.list_collections()
# print("当前存在的 Collections:", [c.name for c in collections])

# # 3. 删除名为 'autosafety_rag' 的 Collection
# try:
#     client.delete_collection(name="autosafety_rag")
#     print("✅ Collection 'autosafety_rag' 已成功删除。")
# except Exception as e:
#     # 如果 collection 不存在，会抛出 ValueError
#     print(f"❌ 删除失败: {e}")

# # 4. 再次确认
# collections_after = client.list_collections()
# print("删除后的 Collections:", [c.name for c in collections_after])