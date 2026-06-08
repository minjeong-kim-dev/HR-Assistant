"""
코드 작성 연습용 파일
"""
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")

text = "연차휴가는 며칠 받을 수 있나요?"
vector = model.encode(text)

print(f"벡터 타입: {type(vector)}")
print(f"벡터 크기: {len(vector)}")
print(f"앞 5개 값: {vector[:5]}")